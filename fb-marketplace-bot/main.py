"""
Punto de entrada principal.
Corre en paralelo:
  - Bot de Telegram (python-telegram-bot con job_queue)
  - Dashboard web Flask + SocketIO
"""

import logging
import os
import threading
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def start_web():
    from web import run_web
    run_web()


def start_bot():
    from bot import run_bot
    run_bot()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Iniciando dashboard web en http://localhost:{port}")
    logger.info("Iniciando bot de Telegram...")

    # Web en hilo secundario, bot en hilo principal
    web_thread = threading.Thread(target=start_web, daemon=True)
    web_thread.start()

    start_bot()
