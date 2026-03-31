"""
GOLD SNIPER V2.0 - Startup Script
====================================
This script initializes all bot components and then starts
the Flask app via Gunicorn. Use this as the entry point on Render.com.

Usage:
  python start.py                    # Direct run (development)
  gunicorn start:app --preload ...   # Production (Render.com)
"""

import os
import sys
import logging
import threading
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("GoldSniper.Start")

# Import bot module
import bot
from bot import app  # Flask app for gunicorn

_initialized = False


def initialize_bot():
    """Initialize all bot components (called once)."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    logger.info("Initializing Gold Sniper V2.0...")

    from database import init_db
    from message_formatter import format_startup_message
    from price_monitor import TradeMonitor

    # Initialize database
    init_db()

    # Start background services
    bot.price_monitor.start()
    bot.news_filter.start()
    bot.keep_alive.start()

    # Initialize trade monitor
    bot.trade_monitor = TradeMonitor(bot.price_monitor, bot.pipeline, bot.telegram_send)
    bot.trade_monitor.start()

    # Start Telegram polling
    bot.start_telegram_polling()

    # Start scheduled tasks
    bot.start_scheduled_tasks()

    # Set Telegram commands
    bot.telegram_set_commands()

    # Send startup message
    bot.telegram_send(format_startup_message())

    logger.info("Gold Sniper V2.0 initialized successfully!")


# Auto-initialize when imported by gunicorn with --preload
initialize_bot()


if __name__ == "__main__":
    # Direct run (development mode)
    import config
    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)
