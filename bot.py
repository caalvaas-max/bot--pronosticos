"""Bot de Telegram final."""
from __future__ import annotations
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from agent.orquestador import Orquestador

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
orquestador = Orquestador(bankroll=1000.0)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 <b>Bot de Pronosticos</b>\n\nEscribe <code>/hoy</code> para ver los partidos.", parse_mode="HTML")

async def cmd_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Buscando partidos disponibles en Bzzoiro...")
    partidos = await orquestador.obtener_partidos_disponibles(limite=20) 
    
    if not partidos:
        await update.message.reply_text("❌ No hay partidos disponibles en este momento.")
        return

    keyboard = []
    for i, p in enumerate(partidos):
        boton_texto = f"⏰ {p['hora']} | {p['texto']}" if p['hora'] else p['texto']
        keyboard.append([InlineKeyboardButton(boton_texto, callback_data=f"an_{i}")])

    context.user_data['partidos_hoy'] = partidos
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("⚽ <b>Selecciona un partido para analizar:</b>", reply_markup=reply_markup, parse_mode="HTML")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("an_"):
        idx = int(data.split("_")[1])
        partidos = context.user_data.get('partidos_hoy', [])
        
        if idx < len(partidos):
            texto = partidos[idx]['texto']
            await query.message.reply_text(f"🔍 Analizando <b>{texto}</b>...", parse_mode="HTML")
            
            try:
                r = await orquestador.procesar(texto, guardar=True)
                p = r.probabilidades
                m = r.mercados
                
                picks = [
                    ("Ganador Local", p.get('local', 0)), ("Ganador Empate", p.get('empate', 0)), ("Ganador Visita", p.get('visitante', 0)),
                    ("Doble Oportunidad 1X", m.get('doble_1x', 0)), ("Doble Oportunidad 12", m.get('doble_12', 0)), ("Doble Oportunidad X2", m.get('doble_x2', 0)),
                    ("Over 1.5 Goles", m.get('over_15', 0)), ("Over 2.5 Goles", m.get('over_25', 0)), ("Over 3.5 Goles", m.get('over_35', 0)),
                    ("Hándicap Local -0.5", m.get('hcp_local_m05', 0)), ("Hándicap Local -1.5", m.get('hcp_local_m15', 0)), ("Hándicap Visita +0.5", m.get('hcp_visita_p05', 0)),
                    ("Ambos Anotan (Sí)", m.get('btts_si', 0)), ("Ambos Anotan (No)", m.get('btts_no', 0)),
                ]
                picks.sort(key=lambda x: x[1], reverse=True)
                top_texto = "".join([f"• <b>{n}: {pr*100:.1f}%</b>\n" for n, pr in picks[:3]])

                hora_str = f"⏰ Hora del partido: <b>{r.hora}</b>\n" if r.hora else ""
                
                # FORMATEO BLINDADO DEL MARCADOR
                marcador_str = str(r.marcador_top) if r.marcador_top else "No disponible"
                if r.marcador_prob > 0:
                    marcador_str += f" ({r.marcador_prob*100:.1f}%)"
                
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
│ Marcador Top   │ {marcador_str[:20]} │
└─────────────────────────────────┘
"""
                mensaje = (
                    f"⭐ <b>PRONÓSTICO: {r.local} vs {r.visitante}</b>\n"
                    f"{hora_str}\n"
                    f"🔥 <b>TOP PICKS:</b>\n{top_texto}\n"
                    f"📊 <b>Desglose:</b>\n<pre>{cuadro}</pre>\n"
                    f"🎯 Confianza: <b>{r.confianza.upper()}</b>"
                )
                await query.message.reply_text(mensaje, parse_mode="HTML")
            except Exception as e:
                await query.message.reply_text(f"❌ Error: {e}")

async def cmd_analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: <code>/analizar Local vs Visitante</code>", parse_mode="HTML")
        return
    texto = " ".join(context.args)
    await update.message.reply_text(f"🔍 Analizando <b>{texto}</b>...", parse_mode="HTML")
    
    try:
        r = await orquestador.procesar(texto, guardar=True)
        p = r.probabilidades
        m = r.mercados
        
        picks = [
            ("Ganador Local", p.get('local', 0)), ("Ganador Empate", p.get('empate', 0)), ("Ganador Visita", p.get('visitante', 0)),
            ("Doble Oportunidad 1X", m.get('doble_1x', 0)), ("Doble Oportunidad 12", m.get('doble_12', 0)), ("Doble Oportunidad X2", m.get('doble_x2', 0)),
            ("Over 1.5 Goles", m.get('over_15', 0)), ("Over 2.5 Goles", m.get('over_25', 0)), ("Over 3.5 Goles", m.get('over_35', 0)),
            ("Hándicap Local -0.5", m.get('hcp_local_m05', 0)), ("Hándicap Local -1.5", m.get('hcp_local_m15', 0)), ("Hándicap Visita +0.5", m.get('hcp_visita_p05', 0)),
            ("Ambos Anotan (Sí)", m.get('btts_si', 0)), ("Ambos Anotan (No)", m.get('btts_no', 0)),
        ]
        picks.sort(key=lambda x: x[1], reverse=True)
        top_texto = "".join([f"• <b>{n}: {pr*100:.1f}%</b>\n" for n, pr in picks[:3]])

        hora_str = f"⏰ Hora del partido: <b>{r.hora}</b>\n" if r.hora else ""
        
        marcador_str = str(r.marcador_top) if r.marcador_top else "No disponible"
        if r.marcador_prob > 0:
            marcador_str += f" ({r.marcador_prob*100:.1f}%)"

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
│ Marcador Top   │ {marcador_str[:20]} │
└─────────────────────────────────┘
"""
        mensaje = (
            f"⭐ <b>PRONÓSTICO: {r.local} vs {r.visitante}</b>\n"
            f"{hora_str}\n"
            f"🔥 <b>TOP PICKS:</b>\n{top_texto}\n"
            f"📊 <b>Desglose:</b>\n<pre>{cuadro}</pre>\n"
            f"🎯 Confianza: <b>{r.confianza.upper()}</b>"
        )
        await update.message.reply_text(mensaje, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("hoy", cmd_hoy))
    app.add_handler(CommandHandler("analizar", cmd_analizar))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
