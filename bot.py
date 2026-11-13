import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from agent.orquestador import Orquestador
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
orquestador = Orquestador(bankroll=1000.0)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de pronósticos. Escribe /hoy para ver los partidos.")

async def cmd_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚽ ¿Qué fútbol quieres analizar hoy?", 
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👨 Fútbol Masculino", callback_data="gen_M"),
             InlineKeyboardButton("👩 Fútbol Femenino", callback_data="gen_F")]
        ])
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("gen_"):
        genero = data.split("_")[1]
        await query.edit_message_text(text="🔍 Buscando partidos disponibles...")
        
        partidos = await orquestador.obtener_partidos_disponibles(limite=100)
        filtrados = [p for p in partidos if p.get('genero', 'M') == genero]

        if not filtrados:
            await query.edit_message_text(f"No hay partidos de {'Masculino' if genero=='M' else 'Femenino'} disponibles ahora.")
            return

        ligas = list(set([p['liga'] for p in filtrados]))
        
        keyboard = []
        for liga in ligas:
            context.user_data[f"partidos_{liga}"] = [p for p in filtrados if p['liga'] == liga]
            keyboard.append([InlineKeyboardButton(liga, callback_data=f"liga_{liga}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="volver")])
        await query.edit_message_text("🏆 Selecciona la liga:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("liga_"):
        liga = data.split("_", 1)[1]
        partidos_liga = context.user_data.get(f"partidos_{liga}", [])

        keyboard = []
        for i, p in enumerate(partidos_liga):
            context.user_data[f"partido_{i}"] = p
            texto_boton = f"🕒 {p['hora']} | {p['texto']}"
            keyboard.append([InlineKeyboardButton(texto_boton, callback_data=f"an_{i}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Volver a ligas", callback_data="volver")])
        await query.edit_message_text(f"📅 Partidos de {liga}:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("an_"):
        idx = int(data.split("_")[1])
        partido = context.user_data.get(f"partido_{idx}")
        
        if partido:
            await query.edit_message_text(f"🤖 Analizando <b>{partido['texto']}</b>...\n⏳ Esto puede tardar unos segundos.", parse_mode="HTML")
            
            pronostico = await orquestador.generar_pronostico(partido['local'], partido['visitante'])
            
            if pronostico:
                # 1. Recopilar todas las probabilidades en una lista
                todos_los_picks = []
                
                # Añadir 1X2
                p_1x2 = pronostico.probabilidades
                for sel, prob in p_1x2.items():
                    nombre_sel = pronostico.local if sel == '1' else 'Empate' if sel == 'X' else pronostico.visitante
                    todos_los_picks.append((prob, f"Gana {nombre_sel}"))
                
                # Añadir mercados secundarios
                for nombre_mercado, opciones in pronostico.mercados.items():
                    if nombre_mercado == "1X2" or opciones == "NO RECOMENDADO":
                        continue
                    
                    if isinstance(opciones, dict):
                        for sel, prob in opciones.items():
                            todos_los_picks.append((prob, f"{nombre_mercado} - {sel}"))
                    elif isinstance(opciones, str):
                        # Extraer el porcentaje de string tipo "Over 1.5 (74.3%)"
                        try:
                            nombre = opciones.split(" (")[0]
                            prob_str = opciones.split("(")[1].replace("%)", "")
                            prob = float(prob_str) / 100.0
                            todos_los_picks.append((prob, nombre))
                        except:
                            pass
                
                # 2. Ordenar de mayor a menor y sacar el Top 3
                todos_los_picks.sort(key=lambda x: x[0], reverse=True)
                top_3 = todos_los_picks[:3]

                # 3. Construir el mensaje
                texto_final = f"⚽ <b>{pronostico.local} vs {pronostico.visitante}</b>\n\n"
                
                # Añadir TOP PICKS en negrita arriba
                texto_final += "🔥 <b>TOP PICKS:</b>\n"
                for prob, nombre in top_3:
                    texto_final += f"• <b>{nombre}: {prob*100:.1f}%</b>\n"
                texto_final += "\n"
                
                # Añadir el desglose completo
                texto_final += "📊 <b>Desglose:</b>\n"
                
                texto_final += f"🏠 Gana {pronostico.local}: {p_1x2.get('1', 0)*100:.1f}%\n"
                texto_final += f"🤝 Empate: {p_1x2.get('X', 0)*100:.1f}%\n"
                texto_final += f"✈️ Gana {pronostico.visitante}: {p_1x2.get('2', 0)*100:.1f}%\n\n"
                
                for nombre_mercado, opciones in pronostico.mercados.items():
                    if nombre_mercado == "1X2":
                        continue
                        
                    if opciones == "NO RECOMENDADO":
                        texto_final += f"⚠️ <b>{nombre_mercado}:</b> NO RECOMENDADO (Faltan datos)\n\n"
                    elif isinstance(opciones, str): 
                        texto_final += f"🔹 <b>{nombre_mercado}:</b> {opciones}\n"
                    elif isinstance(opciones, dict):
                        texto_final += f"🔹 <b>{nombre_mercado}:</b>\n"
                        for seleccion, prob in opciones.items():
                            texto_final += f"   • {seleccion}: {prob*100:.1f}%\n"
                        texto_final += "\n"
                
                texto_final += f"💡 Confianza del análisis: {pronostico.confianza.upper()}"
                
                await query.edit_message_text(texto_final, parse_mode="HTML")
            else:
                await query.edit_message_text("❌ No se pudieron obtener los datos del pronóstico para este partido. Intenta de nuevo.")
            
    elif data == "volver":
        await query.edit_message_text("⚽ ¿Qué fútbol quieres analizar hoy?", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👨 Fútbol Masculino", callback_data="gen_M"),
                 InlineKeyboardButton("👩 Fútbol Femenino", callback_data="gen_F")]
            ])
        )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("hoy", cmd_hoy))
    app.add_handler(CallbackQueryHandler(button_callback))
    logger.info("Bot iniciado y escuchando...")
    app.run_polling()
