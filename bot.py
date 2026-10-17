"""Bot de Telegram para pronosticos deportivos."""
from __future__ import annotations
import logging
import os
import inspect
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from agent.orquestador import Orquestador
from agent.validacion import ValidacionError

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
        # PARCHE MAESTRO: Detecta si la función es asíncrona o síncrona
        resultado = orquestador.procesar(texto, guardar=True)
        if inspect.isawaitable(resultado):
            r = await resultado
        else:
            r = resultado
            
        p = r.probabilidades
        m = r.mercados
        
        cuadro = f"""
┌─────────────────────────────────┐
│ ⚽ {r.local} vs {r.visitante}
│ Fuente: {r.fuente}
├─────────────────────────────────┤
│ MERCADO        │ SELECCION │ PROB
├─────────────────────────────────┤
│ Ganador        │ Local     │ {p.get('local',0)*100:.1f}%
│ Ganador        │ Empate    │ {p.get('empate',0)*100:.1f}%
│ Ganador        │ Visita    │ {p.get('visitante',0)*100:.1f}%
├─────────────────────────────────┤
│ Goles          │ Over 1.5  │ {m.get('over_15',0)*100:.1f}%
│ Goles          │ Over 2.5  │ {m.get('over_25',0)*100:.1f}%
│ Goles          │ Over 3.5  │ {m.get('over_35',0)*100:.1f}%
├─────────────────────────────────┤
│ Ambos Anotan   │ Si        │ {m.get('btts_si',0)*100:.1f}%
│ Ambos Anotan   │ No        │ {m.get('btts_no',0)*100:.1f}%
├─────────────────────────────────┤
│ Marcador Top   │ {r.marcador_top}       │ {r.marcador_prob*100:.1f}%
└─────────────────────────────────┘
🎯 Confianza: *{r.confianza.upper()}*
"""
        await update.message.reply_text(f"```\n{cuadro}\n```", parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("analizar", cmd_analizar))
    app.run_polling()

if __name__ == "__main__":
    main()
