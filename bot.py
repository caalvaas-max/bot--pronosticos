"""Bot de Telegram para pronosticos deportivos."""
from __future__ import annotations
import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from agent.orquestador import Orquestador

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
orquestador = Orquestador(bankroll=1000.0)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 *Bot de Pronosticos*\n\nEnvía: `/analizar As Roma vs Real Madrid`", parse_mode="Markdown")

async def cmd_analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: `/analizar Local vs Visitante`")
        return
    texto = " ".join(context.args)
    await update.message.reply_text("🔍 Analizando...")
    
    try:
        # AHORA SÍ: procesar es async, por lo que usamos await correctamente
        r = await orquestador.procesar(texto, guardar=True)
        p = r.probabilidades
        m = r.mercados
        
        cuadro = f"""
┌─────────────────────────────────┐
│ ⚽ {r.local} vs {r.visitante}
│ Fuente: {r.fuente}
├─────────────────────────────────┤
│ MERCADO        │ SELECCION │ PROB
├─────────────────────────────────┤
│ Ganador        │ Local     │ {p['local']*100:.1f}%
│ Ganador        │ Empate    │ {p['empate']*100:.1f}%
│ Ganador        │ Visita    │ {p['visitante']*100:.1f}%
├─────────────────────────────────┤
│ Goles          │ Over 1.5  │ {m['over_15']*100:.1f}%
│ Goles          │ Over 2.5  │ {m['over_25']*100:.1f}%
│ Goles          │ Over 3.5  │ {m['over_35']*100:.1f}%
├─────────────────────────────────┤
│ Ambos Anotan   │ Si        │ {m['btts_si']*100:.1f}%
│ Ambos Anotan   │ No        │ {m['btts_no']*100:.1f}%
├─────────────────────────────────┤
│ Marcador Top   │ {r.marcador_top}       │ {r.marcador_prob*100:.1f}%
└─────────────────────────────────┘
🎯 Confianza: *{r.confianza.upper()}*
"""
        await update.message.reply_text(f"```\n{cuadro}\n```", parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Error en bot: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("analizar", cmd_analizar))
    app.run_polling()

if __name__ == "__main__":
    main()
