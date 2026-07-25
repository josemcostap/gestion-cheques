# Gestión de Cheques

App web mobile-first para cargar y controlar cheques lanzados, con filtros combinables en AND u OR.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar

```bash
python app.py
```

Abrí http://localhost:5000 en el navegador (o desde el celular usando la IP de la compu en la misma red).

## Funcionalidad

- **Nuevo cheque**: formulario con fecha de emisión, fecha de vencimiento, monto, número de cheque, cuenta, beneficiario, concepto y observaciones. Los campos Días, Pendiente y Pagado se calculan automáticamente.
- **Lista de cheques**: filtros combinables por cualquier campo, con selector global AND / OR. Botón para marcar un cheque como pagado y para eliminarlo.
- **Base de datos**: SQLite local (`instance/cheques.db`), se crea sola en el primer arranque.
