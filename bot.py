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
            
            # Llamamos a la función del orquestador que calcula el pronóstico
            pronostico = await orquestador.generar_pronostico(partido['local'], partido['visitante'])
            
            if pronostico:
                p = pronostico.probabilidades
                texto_final = f"⚽ <b>{pronostico.local} vs {pronostico.visitante}</b>\n\n"
                texto_final += f"📊 <b>Probabilidades del Modelo:</b>\n"
                texto_final += f"🏠 Gana {pronostico.local}: {p.get('1', 0)*100:.1f}%\n"
                texto_final += f"🤝 Empate: {p.get('X', 0)*100:.1f}%\n"
                texto_final += f"✈️ Gana {pronostico.visitante}: {p.get('2', 0)*100:.1f}%\n\n"
                texto_final += f"💡 Confianza del análisis: {pronostico.confianza.upper()}"
                
                await query.edit_message_text(texto_final, parse_mode="HTML")
            else:
                await query.edit_message_text("❌ No se pudieron obtener los datos del pronóstico para este partido. Intenta con otro.")
            
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