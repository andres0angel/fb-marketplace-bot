"""
Servidor web Flask — Dashboard del bot de Marketplace.
Corre en paralelo con el bot de Telegram.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit

from db import get_all_ads, clear_db
from filters import apply_filters, parse_price
from scraper import run_all_searches

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET", "marketplace-bot-secret-2024")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

WEB_PASSWORD = os.environ.get("WEB_PASSWORD", "")  # opcional: proteger con password


def check_auth(password):
    if not WEB_PASSWORD:
        return True
    return password == WEB_PASSWORD


def format_ad_for_web(ad: dict) -> dict:
    price = parse_price(ad.get("price_raw", ""))
    vehicle_labels = {
        "spark_gt": "Spark GT",
        "hyundai_i10": "Hyundai i10",
        "other": "Otro",
    }
    vehicle_colors = {
        "spark_gt": "#f97316",
        "hyundai_i10": "#3b82f6",
        "other": "#8b5cf6",
    }
    vk = ad.get("vehicle_key", "other")
    return {
        "id": ad.get("id", ""),
        "title": ad.get("title", "Sin título"),
        "price": price or 0,
        "price_formatted": f"${price:,.0f}" if price else "N/A",
        "year": ad.get("year") or "N/A",
        "location": ad.get("location", ""),
        "description": (ad.get("description") or "")[:300],
        "images": ad.get("images", []),
        "url": ad.get("url", ""),
        "vehicle_label": vehicle_labels.get(vk, "Otro"),
        "vehicle_color": vehicle_colors.get(vk, "#8b5cf6"),
        "vehicle_key": vk,
        "seen_at": ad.get("seen_at", ""),
    }


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ads")
def api_ads():
    ads = get_all_ads()
    ads_sorted = sorted(ads, key=lambda x: x.get("seen_at", ""), reverse=True)
    return jsonify({
        "ads": [format_ad_for_web(a) for a in ads_sorted],
        "total": len(ads_sorted),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/stats")
def api_stats():
    ads = get_all_ads()
    by_vehicle = {}
    prices = []
    for ad in ads:
        vk = ad.get("vehicle_key", "other")
        by_vehicle[vk] = by_vehicle.get(vk, 0) + 1
        p = parse_price(ad.get("price_raw", ""))
        if p:
            prices.append(p)

    return jsonify({
        "total": len(ads),
        "by_vehicle": by_vehicle,
        "avg_price": int(sum(prices) / len(prices)) if prices else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "interval_minutes": int(os.environ.get("SEARCH_INTERVAL_MINUTES", 30)),
    })


@app.route("/api/search", methods=["POST"])
def api_search_now():
    """Dispara una búsqueda manual desde el dashboard."""
    import threading

    def do_search():
        try:
            from db import is_seen, mark_seen
            ads = run_all_searches()
            nuevos = []
            for ad in ads:
                if is_seen(ad["id"]):
                    continue
                passes, _ = apply_filters(ad)
                if not passes:
                    continue
                mark_seen(ad)
                nuevos.append(ad)

            # Notificar via WebSocket a todos los clientes conectados
            socketio.emit("new_ads", {
                "ads": [format_ad_for_web(a) for a in nuevos],
                "count": len(nuevos),
            })
            socketio.emit("search_done", {"count": len(nuevos)})
        except Exception as e:
            socketio.emit("search_error", {"error": str(e)})

    thread = threading.Thread(target=do_search, daemon=True)
    thread.start()
    return jsonify({"status": "searching"})


@app.route("/api/clear", methods=["POST"])
def api_clear():
    clear_db()
    socketio.emit("db_cleared", {})
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# WebSocket eventos
# ---------------------------------------------------------------------------

@socketio.on("connect")
def on_connect():
    logger.info(f"Cliente web conectado: {request.sid}")


@socketio.on("disconnect")
def on_disconnect():
    logger.info(f"Cliente web desconectado: {request.sid}")


# ---------------------------------------------------------------------------
# Función para emitir nuevo anuncio desde el bot de Telegram
# (llamada por el scheduler compartido)
# ---------------------------------------------------------------------------

def emit_new_ad(ad: dict):
    """Llamar desde bot.py cuando se encuentra un anuncio nuevo."""
    try:
        socketio.emit("new_ads", {
            "ads": [format_ad_for_web(ad)],
            "count": 1,
        })
    except Exception as e:
        logger.error(f"Error emitiendo WebSocket: {e}")


def run_web(host="0.0.0.0", port=None):
    port = port or int(os.environ.get("PORT", 5000))
    logger.info(f"Dashboard web en http://localhost:{port}")
    socketio.run(app, host=host, port=port, debug=False, use_reloader=False)
