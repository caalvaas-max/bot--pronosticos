# Bot de Pronosticos Deportivos

Sistema de pronosticos de futbol con motor regenerativo.

## Caracteristicas

- Modelo Poisson Bivariante con correccion Dixon-Coles
- Pi-Ratings (Elo mejorado) + Ensemble
- Calibracion isotonica automatica
- Deteccion de Value Bets (EV+)
- Gestion de bankroll con Kelly Criterion
- Motor regenerativo: aprende de errores
- Bot de Telegram con soporte OCR
- Cache con SQLite (migrable a PostgreSQL)

## Estructura

- `domain/` - Enums y modelos del dominio
- `models/` - Modelos matematicos
- `data/` - Acceso a datos y APIs
- `auditoria/` - Motor regenerativo
- `betting/` - Gestion de apuestas
- `agent/` - Orquestador principal
- `vision/` - OCR para imagenes
- `utils/` - Utilidades
- `tests/` - Tests unitarios

## Instalacion

pip install -r requirements.txt

## Uso

python bot.py

## Variables de entorno

- TELEGRAM_TOKEN
- BZZOIRO_API_KEY
- DATABASE_URL (opcional)

## Licencia

MIT
