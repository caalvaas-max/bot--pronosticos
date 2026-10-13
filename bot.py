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

SEP = "+----------------+----------+--------+"
SEP_LARGO = "+----------------+--------+--------+"


def _cuadro_pronostico(r) -> str:
    p = r.probabilidades
    m = r.mercados

    l1 = p["local"] + p["empate"]
    l2 = p["local"] + p["visitante"]
    l3 = p["empate"] + p["visitante"]

    lineas = [
        SEP,
        "| MERCADO        | SELECCION |  PROB  |",
        SEP,
        f"| Ganador        | Local     | {p['local']*100:5.1f}% |",
        f"| Ganador        | Empate    | {p['empate']*100:5.1f}% |",
        f"| Ganador        | Visita    | {p['visitante']*100:5.1f}% |",
        SEP,
        f"| Doble Oport.   | 1X        | {l1*100:5.1f}% |",
        f"| Doble Oport.   | 12        | {l2*100:5.1f}% |",
        f"| Doble Oport.   | X2        | {l3*100:5.1f}% |",
        SEP,
        f"| Goles Totales  | Over 1.5  | {m['over_15']*100:5.1f}% |",
        f"| Goles Totales  | Under 1.5 | {m['under_15']*100:5.1f}% |",
        f"| Goles Totales  | Over 2.5  | {m['over_25']*100:5.1f}% |",
        f"| Goles Totales  | Under 2.5 | {m['under_25']*100:5.1f}% |",
        f"| Goles Totales  | Over 3.5  | {m['over_35']*100:5.1f}% |",
        f"| Goles Totales  | Under 3.5 | {m['under_35']*100:5.1f}% |",
        SEP,
        f"| Ambos Anotan   | Si        | {m['btts_si']*100:5.1f}% |",
        f"| Ambos Anotan   | No        | {m['btts_no']*100:5.1f}% |",
        SEP,
        f"| Handicap       | Local -1  | {m['h_local_m1']*100:5.1f}% |",
        f"| Handicap       | Local -0.5| {m['h_local_m05']*100:5.1f}% |",
        f"| Handicap       | Visita+.5 | {m['h_visitante_p05']*100:5.1f}% |",
        SEP,
        f"| Corners        | Over 8.5  | {m['corners_over_85']*100:5.1f}% |",
        f"| Corners        | Over 9.5  | {m['corners_over_95']*100:5.1f}% |",
        f"| Corners        | Over 10.5 | {m['corners_over_105']*100:5.1f}% |",
        SEP,
        f"| Tarjetas       | Over 3.5  | {m['tarj_over_35']*100:5.1f}% |",
        f"| Tarjetas       | Over 4.5  | {m['tarj_over_45']*100:5.1f}% |",
        f"| Tarjetas       | Over 5.5  | {m['tarj_over_55']*100:5.1f}% |",
        SEP,
        f"| Marcador       | {r.marcador_top:>9} | {r.marcador_prob*100:5.1f}% |",
        SEP,
    ]
    return "\n".join(lineas)


def _cuadro_auditoria(datos: dict) -> str:
    partidos = datos["partidos"]
    tabla = datos["tabla"]

    if not partidos:
        return "Sin datos de auditoria aun."

    cols = partidos[:4]
    ancho_col = 10

    cabecera = "| MERCADO        |"
    for col in cols:
        cabecera += f" {col[:ancho_col]:^{ancho_col}} |"

    sep = "+----------------+"
    for _ in cols:
        sep += "-" * (ancho_col + 2) + "+"

    lineas = [sep, cabecera, sep]

    for mercado in sorted(tabla.keys()):
        fila = f"| {mercado[:14]:<14} |"
        for col in cols:
            valor = tabla[mercado].get(col, "-")
            if valor == "ACERTO":
                texto = "ACERTO"
            elif valor == "DESACERTO":
                texto = "DESAC"
            else:
                texto = "-"
            fila += f" {texto:^{ancho_col}} |"
        lineas.append(fila)

    lineas.append(sep)
    return "\n".join(lineas)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot de Pronosticos*\n\n"
        "Comandos:\n"
        "• `/analizar Real Madrid vs Barcelona`\n"
        "• `/rendimiento` - Auditoria en cuadro\n"
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
        cuadro = _cuadro_pronostico(r)
        mensaje = (
            f"⚽ *{r.local} vs {r.visitante}*\n\n"
            f"```\n{cuadro}\n```\n\n"
            f"🎯 *Confianza:* {r.confianza.upper()}"
        )
        await update.message.reply_text(mensaje, parse_mode="Markdown")
    except ValidacionError as e:
        await update.message.reply_text(f"❌ {e}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_rendimiento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = calculadora.calcular()
    datos = calculadora.tabla_por_partido()
    cuadro = _cuadro_auditoria(datos)

    resumen = (
        f"📊 *AUDITORIA DEL BOT*\n\n"
        f"```\n{cuadro}\n```\n\n"
        f"*Resumen Global:*\n"
        f"• Total: `{m.total}`\n"
        f"• Aciertos: `{m.aciertos}`\n"
        f"• Fallos: `{m.fallos}`\n"
        f"• Precision: `{m.precision*100:.1f}%`\n"
        f"• Brier Score: `{m.brier_score:.3f}`\n"
        f"• ROI: `{m.roi:.1f}%`"
    )
    await update.message.reply_text(resumen, parse_mode="Markdown")


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
    logger.info("Bot iniciado")
    app.run_polling()


if __name__ == "__main__":
    main()
