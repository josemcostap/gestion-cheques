import csv
import io
import os
import sqlite3
from datetime import date

from flask import Flask, Response, g, redirect, render_template, request, url_for

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "cheques.db")

app = Flask(__name__)

EXPORT_COLUMNS = [
    ("numero_ch", "N° Cheque"),
    ("cuenta", "Cuenta"),
    ("beneficiario", "Beneficiario"),
    ("concepto", "Concepto"),
    ("fecha_emision", "Emisión"),
    ("fecha_vencimiento", "Vencimiento"),
    ("dias", "Días"),
    ("monto", "Monto"),
    ("estado", "Estado"),
    ("fecha_pago", "Fecha pago"),
    ("observaciones", "Observaciones"),
]

TEXT_FIELDS = {
    "numero_ch": "Número de cheque",
    "cuenta": "Cuenta",
    "beneficiario": "Beneficiario",
    "concepto": "Concepto",
    "observaciones": "Observaciones",
}
DATE_FIELDS = {
    "fecha_emision": "Fecha de emisión",
    "fecha_vencimiento": "Fecha de vencimiento",
}
NUMBER_FIELDS = {
    "monto": "Monto",
}
BOOL_FIELDS = {
    "pagado": "Pagado",
}

FIELD_LABELS = {**TEXT_FIELDS, **DATE_FIELDS, **NUMBER_FIELDS, **BOOL_FIELDS}
FIELD_TYPES = {}
FIELD_TYPES.update({k: "text" for k in TEXT_FIELDS})
FIELD_TYPES.update({k: "date" for k in DATE_FIELDS})
FIELD_TYPES.update({k: "number" for k in NUMBER_FIELDS})
FIELD_TYPES.update({k: "bool" for k in BOOL_FIELDS})

TEXT_OPERATORS = {"contiene": "LIKE", "igual": "="}
NUMBER_OPERATORS = {"mayor_que": ">", "menor_que": "<", "igual": "="}
DATE_OPERATORS = {"despues_de": ">", "antes_de": "<", "en": "="}
BOOL_OPERATORS = {"igual": "="}


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS cheques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_emision TEXT NOT NULL,
            fecha_vencimiento TEXT NOT NULL,
            monto REAL NOT NULL,
            numero_ch TEXT NOT NULL,
            cuenta TEXT NOT NULL,
            beneficiario TEXT NOT NULL,
            concepto TEXT,
            observaciones TEXT,
            pagado INTEGER NOT NULL DEFAULT 0,
            fecha_pago TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    db.commit()
    db.close()


def build_filters(args):
    fields = args.getlist("field")
    ops = args.getlist("op")
    values = args.getlist("value")
    combine = args.get("combine", "AND")
    if combine not in ("AND", "OR"):
        combine = "AND"

    clauses = []
    params = []
    for field, op, value in zip(fields, ops, values):
        if field not in FIELD_LABELS:
            continue
        if not value:
            continue
        if field in TEXT_FIELDS and op in TEXT_OPERATORS:
            if TEXT_OPERATORS[op] == "LIKE":
                clauses.append(f"{field} LIKE ?")
                params.append(f"%{value}%")
            else:
                clauses.append(f"{field} = ?")
                params.append(value)
        elif field in NUMBER_FIELDS and op in NUMBER_OPERATORS:
            try:
                num = float(value)
            except ValueError:
                continue
            clauses.append(f"{field} {NUMBER_OPERATORS[op]} ?")
            params.append(num)
        elif field in DATE_FIELDS and op in DATE_OPERATORS:
            clauses.append(f"{field} {DATE_OPERATORS[op]} ?")
            params.append(value)
        elif field in BOOL_FIELDS and op in BOOL_OPERATORS:
            clauses.append(f"{field} = ?")
            params.append(1 if value == "si" else 0)

    where = ""
    if clauses:
        where = "WHERE " + f" {combine} ".join(clauses)
    return where, params, combine


def query_cheques(args):
    db = get_db()
    where, params, combine = build_filters(args)
    rows = db.execute(
        f"SELECT * FROM cheques {where} ORDER BY fecha_vencimiento ASC", params
    ).fetchall()

    today = date.today()
    cheques = []
    for row in rows:
        c = dict(row)
        venc = date.fromisoformat(c["fecha_vencimiento"])
        c["dias"] = (venc - today).days
        c["vencido"] = c["dias"] < 0 and not c["pagado"]
        cheques.append(c)
    return cheques, combine


def cheque_export_row(c):
    return {
        "numero_ch": c["numero_ch"],
        "cuenta": c["cuenta"],
        "beneficiario": c["beneficiario"],
        "concepto": c["concepto"] or "",
        "fecha_emision": c["fecha_emision"],
        "fecha_vencimiento": c["fecha_vencimiento"],
        "dias": c["dias"],
        "monto": c["monto"],
        "estado": "Pagado" if c["pagado"] else ("Vencido" if c["vencido"] else "Pendiente"),
        "fecha_pago": c["fecha_pago"] or "",
        "observaciones": c["observaciones"] or "",
    }


@app.route("/")
def index():
    cheques, combine = query_cheques(request.args)
    total_pendiente = sum(c["monto"] for c in cheques if not c["pagado"])
    filter_rows = list(
        zip(request.args.getlist("field"), request.args.getlist("op"), request.args.getlist("value"))
    )

    return render_template(
        "index.html",
        cheques=cheques,
        field_labels=FIELD_LABELS,
        field_types=FIELD_TYPES,
        combine=combine,
        filter_rows=filter_rows,
        total_pendiente=total_pendiente,
    )


@app.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    if request.method == "POST":
        db = get_db()
        db.execute(
            """INSERT INTO cheques
               (fecha_emision, fecha_vencimiento, monto, numero_ch, cuenta, beneficiario, concepto, observaciones, pagado)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                request.form["fecha_emision"],
                request.form["fecha_vencimiento"],
                float(request.form["monto"]),
                request.form["numero_ch"],
                request.form["cuenta"],
                request.form["beneficiario"],
                request.form.get("concepto", ""),
                request.form.get("observaciones", ""),
            ),
        )
        db.commit()
        return redirect(url_for("index"))
    return render_template("nuevo.html")


@app.route("/cheque/<int:cheque_id>/pagar", methods=["POST"])
def marcar_pagado(cheque_id):
    db = get_db()
    db.execute(
        "UPDATE cheques SET pagado = 1, fecha_pago = ? WHERE id = ?",
        (date.today().isoformat(), cheque_id),
    )
    db.commit()
    return redirect(request.referrer or url_for("index"))


@app.route("/cheque/<int:cheque_id>/eliminar", methods=["POST"])
def eliminar(cheque_id):
    db = get_db()
    db.execute("DELETE FROM cheques WHERE id = ?", (cheque_id,))
    db.commit()
    return redirect(request.referrer or url_for("index"))


@app.route("/exportar/<formato>")
def exportar(formato):
    if formato not in ("csv", "xlsx", "pdf"):
        return ("Formato no soportado", 400)

    cheques, _ = query_cheques(request.args)
    rows = [cheque_export_row(c) for c in cheques]
    filename = f"cheques_{date.today().isoformat()}.{formato}"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}

    if formato == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([label for _, label in EXPORT_COLUMNS])
        for r in rows:
            writer.writerow([r[key] for key, _ in EXPORT_COLUMNS])
        return Response(buf.getvalue().encode("utf-8-sig"), mimetype="text/csv", headers=headers)

    if formato == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font

        wb = Workbook()
        ws = wb.active
        ws.title = "Cheques"
        ws.append([label for _, label in EXPORT_COLUMNS])
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for r in rows:
            ws.append([r[key] for key, _ in EXPORT_COLUMNS])
        for col_cells in ws.columns:
            length = max((len(str(c.value)) if c.value is not None else 0) for c in col_cells)
            ws.column_dimensions[col_cells[0].column_letter].width = min(max(length + 2, 10), 40)
        buf = io.BytesIO()
        wb.save(buf)
        return Response(
            buf.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )
    styles = getSampleStyleSheet()
    data = [[label for _, label in EXPORT_COLUMNS]] + [
        [str(r[key]) for key, _ in EXPORT_COLUMNS] for r in rows
    ]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    doc.build([Paragraph("Cheques Lanzados", styles["Title"]), Spacer(1, 0.3 * cm), table])
    return Response(buf.getvalue(), mimetype="application/pdf", headers=headers)


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
