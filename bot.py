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
        # AQUI ESTABA EL ERROR: quitamos el await porque procesar() es sincrono
        r = orquestador.procesar(texto, guardar=True)
        
        p = r.probabilidades
        m = r.mercados
        
        # Formatear el cuadro en texto monoespaciado para Telegram
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
        f"• Precision: `{m.precision*100:.1f}%`\n"
        f"• Brier Score: `{m.brier_score:.3f}`",
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
