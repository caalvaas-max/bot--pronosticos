"""Bot de Telegram con Top Picks en negrita y cuadro completo."""
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
    await update.message.reply_text("🤖 <b>Bot de Pronosticos</b>\n\nEnvía: <code>/analizar Local vs Visitante</code>", parse_mode="HTML")

async def cmd_analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: <code>/analizar Local vs Visitante</code>", parse_mode="HTML")
        return
    texto = " ".join(context.args)
    await update.message.reply_text("🔍 Analizando...")
    
    try:
        r = await orquestador.procesar(texto, guardar=True)
        p = r.probabilidades
        m = r.mercados
        
        # 1. Recopilar todos los mercados para buscar los de mayor confianza
        picks = [
            ("Ganador Local", p.get('local', 0)),
            ("Ganador Empate", p.get('empate', 0)),
            ("Ganador Visita", p.get('visitante', 0)),
            ("Doble Oportunidad 1X", m.get('doble_1x', 0)),
            ("Doble Oportunidad 12", m.get('doble_12', 0)),
            ("Doble Oportunidad X2", m.get('doble_x2', 0)),
            ("Over 1.5 Goles", m.get('over_15', 0)),
            ("Over 2.5 Goles", m.get('over_25', 0)),
            ("Over 3.5 Goles", m.get('over_35', 0)),
            ("Hándicap Local -0.5", m.get('hcp_local_m05', 0)),
            ("Hándicap Local -1.5", m.get('hcp_local_m15', 0)),
            ("Hándicap Visita +0.5", m.get('hcp_visita_p05', 0)),
            ("Ambos Anotan (Sí)", m.get('btts_si', 0)),
            ("Ambos Anotan (No)", m.get('btts_no', 0)),
        ]
        
        # Filtrar los que tienen probabilidad > 0 y ordenar de mayor a menor
        picks_validos = [x for x in picks if x[1] > 0]
        picks_validos.sort(key=lambda x: x[1], reverse=True)
        
        # Tomar los 3 mejores
        top_3 = picks_validos[:3]
        
        # Crear el texto en negrita para los Top Picks
        top_texto = ""
        for nombre, prob in top_3:
            top_texto += f"• <b>{nombre}: {prob*100:.1f}%</b>\n"

        # 2. Armar el cuadro completo (usando <pre> para mantener el formato)
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
│ Doble Oport.   │ 1X        │ {m.get('doble_1x',0)*100:.1f}%
│ Doble Oport.   │ 12        │ {m.get('doble_12',0)*100:.1f}%
│ Doble Oport.   │ X2        │ {m.get('doble_x2',0)*100:.1f}%
├─────────────────────────────────┤
│ Goles          │ Over 1.5  │ {m.get('over_15',0)*100:.1f}%
│ Goles          │ Over 2.5  │ {m.get('over_25',0)*100:.1f}%
│ Goles          │ Over 3.5  │ {m.get('over_35',0)*100:.1f}%
├─────────────────────────────────┤
│ Handicap       │ Loc -0.5  │ {m.get('hcp_local_m05',0)*100:.1f}%
│ Handicap       │ Loc -1.5  │ {m.get('hcp_local_m15',0)*100:.1f}%
│ Handicap       │ Vis +0.5  │ {m.get('hcp_visita_p05',0)*100:.1f}%
├─────────────────────────────────┤
│ Ambos Anotan   │ Si        │ {m.get('btts_si',0)*100:.1f}%
│ Ambos Anotan   │ No        │ {m.get('btts_no',0)*100:.1f}%
├─────────────────────────────────┤
│ Marcador Top   │ {r.marcador_top}       │ {r.marcador_prob*100:.1f}%
└─────────────────────────────────┘
"""

        # 3. Mensaje final combinando ambas partes
        mensaje_final = (
            f"⭐ <b>PRONÓSTICO: {r.local} vs {r.visitante}</b>\n\n"
            f"🔥 <b>TOP PICKS (Mayor Confianza):</b>\n"
            f"{top_texto}\n"
            f"📊 <b>Desglose Completo de Mercados:</b>\n"
            f"<pre>{cuadro}</pre>\n"
            f"🎯 Confianza General: <b>{r.confianza.upper()}</b>"
        )

        await update.message.reply_text(mensaje_final, parse_mode="HTML")
        
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
# update
