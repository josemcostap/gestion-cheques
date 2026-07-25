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

Abrí http://localhost:5050 en el navegador (o desde el celular usando la IP de la compu en la misma red). Podés cambiar el puerto con la variable `PORT`.

## Funcionalidad

- **Nuevo cheque**: formulario con fecha de emisión, fecha de vencimiento, monto, número de cheque, cuenta, beneficiario, concepto y observaciones. Los campos Días, Pendiente y Pagado se calculan automáticamente.
- **Lista de cheques**: filtros combinables por cualquier campo, con selector global AND / OR. Botón para marcar un cheque como pagado y para eliminarlo.
- **Exportar**: CSV, Excel y PDF de exactamente lo que está filtrado en pantalla.
- **Base de datos**: SQLite local (`instance/cheques.db`), se crea sola en el primer arranque.

## Acceder desde afuera de tu red (sin desplegar a la nube)

Para entrar desde el celular sin estar en la misma wifi que la Mac, usá un túnel de Cloudflare, que expone tu app local con una URL pública temporal, sin necesidad de crear cuenta.

### 1. Protegé la app con contraseña

Antes de exponerla a internet, seteá una contraseña (si no la seteás, cualquiera con la URL entra sin login):

```bash
export APP_PASSWORD="elegí-una-clave"
python app.py
```

### 2. Instalá cloudflared (una sola vez)

```bash
brew install cloudflared
```

### 3. Abrí el túnel (con la app ya corriendo en otra terminal)

```bash
cloudflared tunnel --url http://localhost:5050
```

Te va a imprimir una URL tipo `https://algo-random.trycloudflare.com`. Abrila desde el celular (Safari o Chrome), vas a ver la pantalla de login: ingresá la contraseña que configuraste.

**Importante:**
- El túnel solo funciona mientras la Mac esté prendida, con `python app.py` y `cloudflared` corriendo.
- La URL cambia cada vez que reiniciás `cloudflared` (es un túnel temporal/gratuito).
- No compartas esa URL con nadie: aunque es difícil de adivinar, cualquiera que la tenga puede intentar loguearse.
