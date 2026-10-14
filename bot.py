"""Bot de Telegram para pronosticos deportivos."""
from __future__ import annotations
import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from agent.orquestador import Orquestador
from agent.validacion import ValidacionError
from auditoria.metricas import CalculadoraMetricas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
orquestador = Orquestador(bankroll=1000.0)
calculadora = CalculadoraMetricas()


def formatear_cuadro(r) -> str:
    p = r.probabilidades
    m = r.mercados
    fuente = "REAL (Bzzoiro)" if r.datos_reales else "APROX"
    lineas = [
        f"⚽ {r.local} vs {r.visitante}",
        f"Fuente: {fuente}",
        "",
        "+---------------------+------------+-------+",
        "| MERCADO             | SELECCION  | PROB  |",
        "+---------------------+------------+-------+",
        f"| Ganador             | Local      | {p['local']*100:5.1f}%|",
        f"| Ganador             | Empate     | {p['empate']*100:5.1f}%|",
        f"| Ganador             | Visita     | {p['visitante']*100:5.1f}%|",
        "+---------------------+------------+-------+",
        f"| Goles               | Over 1.5   | {m['over_15']*100:5.1f}%|",
        f"| Goles               | Under 1.5  | {m['under_15']*100:5.1f}%|",
        f"| Goles               | Over 2.5   | {m['over_25']*100:5.1f}%|",
        f"| Goles               | Under 2.5  | {m['under_25']*100:5.1f}%|",
        f"| Goles               | Over 3.5   | {m['over_35']*100:5.1f}%|",
        "+---------------------+------------+-------+",
        f"| Ambos Anotan        | Si         | {m['btts_si']*100:5.1f}%|",
        f"| Ambos Anotan        | No         | {m['btts_no']*100:5.1f}%|",
        "+---------------------+------------+-------+",
        f"| Marcador            | {r.marcador_top:^10s} | {r.marcador_prob*100:5.1f}%|",
        "+---------------------+------------+-------+",
        "",
        f"🎯 Confianza: {r.confianza.upper()}",
    ]
    return "\n".join(lineas)


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
        r = await orquestador.procesar(texto, guardar=True)
        cuadro = formatear_cuadro(r)
        await update.message.reply_text(f"```\n{cuadro}\n```", parse_mode="Markdown")
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
