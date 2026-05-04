# 🚗 FB Marketplace Bot — Vehículos Antioquia

Bot de Telegram que scrapeaa Facebook Marketplace buscando vehículos en Antioquia que cumplan criterios específicos de precio, año y modelo.

---

## 📋 Criterios de búsqueda

| Vehículo | Precio máximo | Año mínimo |
|---|---|---|
| Spark GT | $25.000.000 COP | 2011 |
| Hyundai i10 | $25.000.000 COP | 2011 |
| Cualquier otro | $20.000.000 COP | 2011 |

📍 **Ubicación:** Solo Antioquia y sus municipios  
🔄 **Frecuencia:** Búsqueda automática cada 30 min (configurable)

---

## 🛠 Instalación local (tu PC)

### 1. Requisitos
- Python 3.10 o superior
- Git

### 2. Clonar y preparar
```bash
git clone <tu-repo>
cd fb-marketplace-bot
pip install -r requirements.txt
```

### 3. Crear el bot en Telegram
1. Abre Telegram y busca **@BotFather**
2. Escribe `/newbot`
3. Dale un nombre (ej: `Mi Buscador Carros`) y un username (ej: `MiCarrosBot`)
4. Copia el **token** que te da (ej: `123456789:ABCdef...`)

### 4. Obtener tu Chat ID
1. Busca **@userinfobot** en Telegram
2. Escribe `/start`
3. Te dice tu ID numérico (ej: `987654321`)

### 5. Configurar variables de entorno
```bash
cp .env.example .env
# Edita el archivo .env con tus datos
```

Contenido del `.env`:
```env
TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNO...
ALLOWED_CHAT_IDS=987654321
NOTIFY_CHAT_IDS=987654321
FB_EMAIL=tucuenta@gmail.com
FB_PASSWORD=tu_contraseña
SEARCH_INTERVAL_MINUTES=30
```

> ⚠️ **Recomendación:** Usa una cuenta de Facebook secundaria/dedicada, no tu cuenta principal.

### 6. Correr los tests
```bash
python test_filters.py
```
Deberías ver todos los tests en ✅ verde.

### 7. Iniciar el bot
```bash
python main.py
```

---

## ☁️ Deploy gratuito en Railway.app (recomendado)

Railway te da 500 horas/mes gratis, más que suficiente para este bot.

### Paso 1: Subir el código a GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/fb-marketplace-bot.git
git push -u origin main
```
> ⚠️ Asegúrate de que el `.env` esté en `.gitignore` (ya está incluido)

### Paso 2: Crear proyecto en Railway
1. Ve a [railway.app](https://railway.app) y regístrate con GitHub
2. Click en **"New Project"** → **"Deploy from GitHub repo"**
3. Selecciona tu repositorio

### Paso 3: Configurar variables de entorno en Railway
En el panel de tu proyecto:
1. Click en tu servicio → **Variables**
2. Agrega cada variable del `.env.example`:

```
TELEGRAM_TOKEN     = tu_token_aqui
ALLOWED_CHAT_IDS   = tu_chat_id
NOTIFY_CHAT_IDS    = tu_chat_id
FB_EMAIL           = tu_email
FB_PASSWORD        = tu_password
SEARCH_INTERVAL_MINUTES = 30
DB_FILE            = /data/seen_ads.json
```

### Paso 4: Configurar el comando de inicio
En Railway → Settings → **Start Command**:
```
python main.py
```

### Paso 5: Deploy
Railway hace el deploy automáticamente. ¡Listo!

---

## 🍪 Alternativa: Usar Cookie de Facebook (si bloquean email/password)

Si Facebook bloquea el login con email/password:

1. Abre Facebook en Chrome (sesión iniciada)
2. Presiona `F12` → pestaña **Application**
3. En el panel izquierdo: **Cookies** → `https://www.facebook.com`
4. Copia los valores de `c_user` y `xs`
5. En el `.env`, pon:
```env
FB_COOKIE=c_user=TU_C_USER; xs=TU_XS
```

---

## 💬 Comandos del bot

| Comando | Descripción |
|---|---|
| `/start` | Bienvenida y resumen de criterios |
| `/buscar` | Buscar ahora manualmente |
| `/recientes` | Ver los últimos 10 anuncios encontrados |
| `/estado` | Ver estado del bot y estadísticas |
| `/limpiar` | Limpiar historial (re-verifica todos los anuncios) |
| `/ayuda` | Mostrar ayuda |

---

## 🏗 Estructura del proyecto

```
fb-marketplace-bot/
├── main.py           # Punto de entrada
├── bot.py            # Bot de Telegram + comandos + job automático
├── scraper.py        # Scraping de Facebook Marketplace
├── filters.py        # Lógica de filtros (precio, año, ubicación, vehículo)
├── db.py             # Persistencia de anuncios vistos (JSON)
├── test_filters.py   # Tests unitarios
├── requirements.txt  # Dependencias Python
├── .env.example      # Plantilla de configuración
├── .gitignore        # Excluye .env y seen_ads.json de git
└── README.md         # Este archivo
```

---

## ❓ Preguntas frecuentes

**¿Por qué me bloqueó Facebook?**
Facebook detecta scraping agresivo. Soluciones:
- Aumenta `SEARCH_INTERVAL_MINUTES` a 60 o más
- Usa cookies en lugar de email/password
- Cambia a una cuenta dedicada

**¿Cómo agrego más municipios?**
Edita la lista `ANTIOQUIA_LOCATIONS` en `filters.py`

**¿Cómo agrego otro vehículo de interés?**
En `filters.py`, agrega una entrada en `VEHICLES_OF_INTEREST`:
```python
"nissan_march": {
    "aliases": ["march", "nissan march", "nissan note"],
    "max_price_cop": 22_000_000,
},
```

**¿Por qué no aparecen resultados?**
Facebook cambia su estructura frecuentemente. Verifica:
1. Que el login sea correcto (`FB_EMAIL` / `FB_PASSWORD`)
2. Que las cookies no hayan expirado
3. Revisa los logs del bot para mensajes de error

---

## 📄 .gitignore recomendado

```
.env
seen_ads.json
__pycache__/
*.pyc
.venv/
```
