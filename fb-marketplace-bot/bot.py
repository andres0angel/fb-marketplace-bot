"""
Bot de Telegram para notificaciones y búsqueda manual.
"""

import os
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode

from scraper import run_all_searches
from filters import apply_filters, parse_price
from db import is_seen, mark_seen, get_all_ads, clear_db

def _emit_to_web(ad: dict):
    """Notifica al dashboard web cuando se encuentra un anuncio nuevo."""
    try:
        from web import emit_new_ad
        emit_new_ad(ad)
    except Exception:
        pass  # El web server puede no estar corriendo

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ALLOWED_CHAT_IDS_RAW = os.environ.get("ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS = set(
    int(x.strip()) for x in ALLOWED_CHAT_IDS_RAW.split(",") if x.strip()
)


def format_price(price_raw: str) -> str:
    price = parse_price(price_raw)
    if price:
        return f"${price:,.0f} COP"
    return price_raw or "No especificado"


def build_ad_message(ad: dict) -> str:
    vehicle_labels = {
        "spark_gt": "⚡ Spark GT",
        "hyundai_i10": "🚗 Hyundai i10",
        "other": "🚙 Otro vehículo",
    }
    label = vehicle_labels.get(ad.get("vehicle_key", "other"), "🚙")
    year = ad.get("year") or "N/A"
    price = format_price(ad.get("price_raw", ""))
    title = ad.get("title", "Sin título")
    location = ad.get("location", "Ubicación desconocida")
    url = ad.get("url", "")
    description = (ad.get("description") or "")[:200]

    msg = (
        f"{label} *{title}*\n"
        f"📅 Modelo: `{year}`\n"
        f"💰 Precio: `{price}`\n"
        f"📍 Ubicación: {location}\n"
    )
    if description:
        msg += f"📝 _{description}..._\n"
    if url:
        msg += f"\n🔗 [Ver en Marketplace]({url})"
    return msg


async def is_authorized(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True  # sin restricción si no está configurado
    return update.effective_chat.id in ALLOWED_CHAT_IDS


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
    await update.message.reply_text(
        "🚗 *Bot de Marketplace - Vehículos Antioquia*\n\n"
        "Comandos disponibles:\n"
        "/buscar — Buscar anuncios ahora\n"
        "/recientes — Ver últimos anuncios encontrados\n"
        "/estado — Estado del bot\n"
        "/limpiar — Limpiar historial (re-revisar todos)\n"
        "/ayuda — Mostrar esta ayuda\n\n"
        "🔍 *Criterios activos:*\n"
        "• Spark GT → hasta $25.000.000\n"
        "• Hyundai i10 → hasta $25.000.000\n"
        "• Otros vehículos → hasta $20.000.000\n"
        "• Modelo ≥ 2011\n"
        "• Ubicación: Antioquia y municipios",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return

    msg = await update.message.reply_text("🔍 Buscando en Marketplace... espera un momento.")

    try:
        ads = run_all_searches()
        nuevos = 0

        for ad in ads:
            if is_seen(ad["id"]):
                continue
            passes, reason = apply_filters(ad)
            if not passes:
                logger.debug(f"Filtrado: {ad['title']} — {reason}")
                continue

            mark_seen(ad)
            text = build_ad_message(ad)

            # Enviar fotos si hay
            images = ad.get("images", [])
            if images:
                try:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=images[0],
                        caption=text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

            nuevos += 1

        if nuevos == 0:
            await msg.edit_text(
                "✅ Búsqueda completada. No se encontraron anuncios nuevos que cumplan los criterios."
            )
        else:
            await msg.edit_text(f"✅ Búsqueda completada. Se enviaron *{nuevos}* anuncios nuevos.", parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        await msg.edit_text(f"❌ Error durante la búsqueda: {str(e)}")


async def cmd_recientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return

    ads = get_all_ads()
    if not ads:
        await update.message.reply_text("📭 No hay anuncios registrados aún.")
        return

    recientes = ads[-10:][::-1]  # últimos 10, más nuevo primero
    await update.message.reply_text(
        f"📋 *Últimos {len(recientes)} anuncios encontrados:*",
        parse_mode=ParseMode.MARKDOWN,
    )
    for ad in recientes:
        text = build_ad_message(ad)
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
    ads = get_all_ads()
    interval = os.environ.get("SEARCH_INTERVAL_MINUTES", "30")
    await update.message.reply_text(
        f"🟢 *Bot activo*\n"
        f"📊 Anuncios registrados: {len(ads)}\n"
        f"⏱ Intervalo automático: cada {interval} min\n"
        f"🕐 Hora servidor: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
    clear_db()
    await update.message.reply_text(
        "🗑️ Historial limpiado. La próxima búsqueda revisará todos los anuncios desde cero."
    )


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


# ---------------------------------------------------------------------------
# Job periódico
# ---------------------------------------------------------------------------

async def job_busqueda_automatica(context: ContextTypes.DEFAULT_TYPE):
    """Job que corre automáticamente y notifica al chat configurado."""
    chat_ids_str = os.environ.get("NOTIFY_CHAT_IDS", os.environ.get("ALLOWED_CHAT_IDS", ""))
    chat_ids = [int(x.strip()) for x in chat_ids_str.split(",") if x.strip()]

    if not chat_ids:
        logger.warning("NOTIFY_CHAT_IDS no configurado, no se envían notificaciones automáticas")
        return

    logger.info("Ejecutando búsqueda automática...")
    try:
        ads = run_all_searches()
        nuevos_por_chat: dict[int, list] = {cid: [] for cid in chat_ids}

        for ad in ads:
            if is_seen(ad["id"]):
                continue
            passes, reason = apply_filters(ad)
            if not passes:
                continue
            mark_seen(ad)
            _emit_to_web(ad)
            for cid in chat_ids:
                nuevos_por_chat[cid].append(ad)

        for cid, nuevos in nuevos_por_chat.items():
            if not nuevos:
                continue
            await context.bot.send_message(
                chat_id=cid,
                text=f"🔔 *{len(nuevos)} anuncio(s) nuevo(s) encontrado(s)*",
                parse_mode=ParseMode.MARKDOWN,
            )
            for ad in nuevos:
                text = build_ad_message(ad)
                images = ad.get("images", [])
                if images:
                    try:
                        await context.bot.send_photo(
                            chat_id=cid,
                            photo=images[0],
                            caption=text,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                        continue
                    except Exception:
                        pass
                await context.bot.send_message(
                    chat_id=cid, text=text, parse_mode=ParseMode.MARKDOWN
                )

    except Exception as e:
        logger.error(f"Error en búsqueda automática: {e}")


def run_bot():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN no configurado en variables de entorno")

    interval_minutes = int(os.environ.get("SEARCH_INTERVAL_MINUTES", "30"))

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("recientes", cmd_recientes))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(CommandHandler("limpiar", cmd_limpiar))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))

    # Job periódico
    app.job_queue.run_repeating(
        job_busqueda_automatica,
        interval=interval_minutes * 60,
        first=60,  # Primera ejecución al minuto de arrancar
    )

    logger.info(f"Bot iniciado. Búsqueda automática cada {interval_minutes} minutos.")
    app.run_polling(drop_pending_updates=True)
