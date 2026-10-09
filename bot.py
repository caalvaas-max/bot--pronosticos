"""Bot de Telegram para pronosticos deportivos."""
from __future__ import annotations
import logging
import os
from datetime import datetime, time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from agent.orquestador import Orquestador
from agent.validacion import ValidacionError
from auditoria.metricas import CalculadoraMetricas
from auditoria.evaluar import Evaluador

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
orquestador = Orquestador(bankroll=1000.0)
calculadora = CalculadoraMetricas()
evaluador = Evaluador()

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot de Pronosticos*\n\n"
        "Comandos:\n"
        "• `/analizar Real Madrid vs Barcelona`\n"
        "• `/rendimiento` - Ver estadisticas\n"
        "• `/ayuda` - Ver esta ayuda",
        parse_mode="Markdown",
    )

async def cmd_analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Uso: `/analizar Equipo Local vs Equipo Visitante`",
            parse_mode="Markdown",
        )
        return
    texto = " ".join(context.args)
    await update.message.reply_text("🔍 Analizando...")
    try:
        r = orquestador.procesar(texto, guardar=True)
        p = r.probabilidades
        msg = (
            f"⚽ *{r.local} vs {r.visitante}*\n\n"
            f"📊 Probabilidades:\n"
            f"• Local: `{p['local']*100:.1f}%`\n"
            f"• Empate: `{p['empate']*100:.1f}%`\n"
            f"• Visitante: `{p['visitante']*100:.1f}%`\n\n"
            f"🎯 Confianza: *{r.confianza.upper()}*"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except ValidacionError as e:
        await update.message.reply_text(f"❌ {e}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_rendimiento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = calculadora.calcular()
    await update.message.reply_text(
        f"📊 *Rendimiento*\n\n"
        f"• Total: `{m.total}`\n"
        f"• Aciertos: `{m.aciertos}`\n"
        f"• Fallos: `{m.fallos}`\n"
        f"• Precision: `{m.precision*100:.1f}%`\n"
        f"• Brier Score: `{m.brier_score:.3f}`\n"
        f"• ROI: `{m.roi:.1f}%`",
        parse_mode="Markdown",
    )

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN no configurado")
        return
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("analizar", cmd_analizar))
    app.add_handler(CommandHandler("rendimiento", cmd_rendimiento))
    logger.info("🤖 Bot iniciado")
    app.run_polling()

if __name__ == "__main__":
    main()
