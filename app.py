import os
import sqlite3
from datetime import date

from flask import Flask, g, redirect, render_template, request, url_for

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "cheques.db")

app = Flask(__name__)

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


@app.route("/")
def index():
    db = get_db()
    where, params, combine = build_filters(request.args)
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


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
