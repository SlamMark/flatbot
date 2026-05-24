"""Telegram command handlers — thin layer that calls BotApiClient and formats replies."""
import logging

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from flatbot.bot.api_client import BotApiClient
from flatbot.config import settings

logger = logging.getLogger(__name__)

_HELP = (
    "🏠 <b>FlatBot</b> — alertas inmobiliarias\n\n"
    "/filtros — listar todos los filtros\n"
    "/estado — estado del último scan\n"
    "/pausar &lt;id&gt; — desactivar filtro\n"
    "/activar &lt;id&gt; — activar filtro\n"
    "/scan — lanzar scan manual\n"
    "/buscar — últimas coincidencias"
)


def _client() -> BotApiClient:
    return BotApiClient(settings.web_api_url)


def _err(msg: str) -> str:
    return f"⚠️ {msg}"


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_html(_HELP)


async def handle_filtros(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    try:
        filters = await _client().get_filters()
    except httpx.HTTPError as exc:
        logger.warning("API error in /filtros: %s", exc)
        await update.message.reply_text(_err("No se pudo contactar el servicio."))
        return

    if not filters:
        await update.message.reply_text("No hay filtros configurados.")
        return

    lines = ["📋 <b>Filtros</b>:"]
    for f in filters:
        icon = "🟢" if f["is_active"] else "🔴"
        lines.append(
            f"{icon} <b>{f['id']}</b>. {f['name']} "
            f"({f['kind']}, {f['radius_km']}km)"
        )
    lines.append("\n<i>Usa /pausar &lt;id&gt; o /activar &lt;id&gt; para cambiar.</i>")
    await update.message.reply_html("\n".join(lines))


async def handle_estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    try:
        status = await _client().get_status()
    except httpx.HTTPError as exc:
        logger.warning("API error in /estado: %s", exc)
        await update.message.reply_text(_err("No se pudo contactar el servicio."))
        return

    last = status.get("last_scan")
    if last:
        scan_line = (
            f"Último scan: {last['started_at'][:16].replace('T', ' ')}\n"
            f"  → {last['listings_fetched']} obtenidos, {last['new_listings']} nuevos, "
            f"{last['matches_found']} matches, {last['alerts_sent']} enviados"
        )
    else:
        scan_line = "Sin scans aún."

    text = (
        f"📊 <b>Estado FlatBot</b>\n"
        f"Filtros activos: {status['active_filters']}\n"
        f"{scan_line}"
    )
    await update.message.reply_html(text)


async def handle_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Uso: /pausar <id>")
        return
    filter_id = int(args[0])
    try:
        f = await _client().deactivate_filter(filter_id)
        await update.message.reply_html(f'⏸ Filtro <b>"{f["name"]}"</b> desactivado.')
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await update.message.reply_text(_err(f"Filtro {filter_id} no encontrado."))
        else:
            await update.message.reply_text(_err("Error al desactivar el filtro."))
    except httpx.HTTPError as exc:
        logger.warning("API error in /pausar: %s", exc)
        await update.message.reply_text(_err("No se pudo contactar el servicio."))


async def handle_activar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Uso: /activar <id>")
        return
    filter_id = int(args[0])
    try:
        f = await _client().activate_filter(filter_id)
        await update.message.reply_html(f'▶ Filtro <b>"{f["name"]}"</b> activado.')
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await update.message.reply_text(_err(f"Filtro {filter_id} no encontrado."))
        else:
            await update.message.reply_text(_err("Error al activar el filtro."))
    except httpx.HTTPError as exc:
        logger.warning("API error in /activar: %s", exc)
        await update.message.reply_text(_err("No se pudo contactar el servicio."))


async def handle_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text("🔄 Lanzando scan… (puede tardar unos segundos)")
    try:
        run = await _client().run_scan()
        text = (
            f'✅ Scan {run["status"]}: '
            f'{run["listings_fetched"]} obtenidos, {run["new_listings"]} nuevos, '
            f'{run["matches_found"]} matches, {run["alerts_sent"]} enviados.'
        )
        await update.message.reply_text(text)
    except httpx.HTTPError as exc:
        logger.warning("API error in /scan: %s", exc)
        await update.message.reply_text(_err("Error al lanzar el scan."))


async def handle_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    try:
        matches = await _client().get_recent_matches(limit=5)
    except httpx.HTTPError as exc:
        logger.warning("API error in /buscar: %s", exc)
        await update.message.reply_text(_err("No se pudo contactar el servicio."))
        return

    if not matches:
        await update.message.reply_text("No hay coincidencias recientes.")
        return

    lines = [f"🔍 <b>Últimas {len(matches)} coincidencias:</b>"]
    for m in matches:
        lst = m["listing"]
        price_str = f"{lst['price']:,}€{'./mes' if lst['kind'] == 'rent' else ''}"
        summary = lst.get("llm_summary") or (
            f"{lst['property_type'].capitalize()}"
            + (f" · {lst['bedrooms']}hab" if lst.get("bedrooms") else "")
            + (f" · {lst['square_meters']}m²" if lst.get("square_meters") else "")
            + f" · {price_str}"
        )
        lines.append(f"\n{summary}\n{lst['address']}\n{lst['url']}")
    await update.message.reply_html("\n".join(lines))
