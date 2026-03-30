"""
Gunicorn configuration for Render.com deployment.
Ensures bot components start when gunicorn loads the app.
"""

import multiprocessing

# Server
bind = "0.0.0.0:8000"
workers = 1
threads = 4
timeout = 120
keepalive = 5

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"


def on_starting(server):
    """Called just before the master process is initialized."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    import bot
    import threading

    def _init_bot():
        import time
        time.sleep(2)  # Wait for Flask to be ready
        bot.main.__wrapped__() if hasattr(bot.main, '__wrapped__') else None

    # Initialize bot components (but not Flask server, gunicorn handles that)
    from database import init_db
    from message_formatter import format_startup_message

    init_db()

    # Start background services
    bot.price_monitor.start()
    bot.news_filter.start()
    bot.keep_alive.start()

    from price_monitor import TradeMonitor
    bot.trade_monitor = TradeMonitor(bot.price_monitor, bot.pipeline, bot.telegram_send)
    bot.trade_monitor.start()

    bot.start_telegram_polling()
    bot.start_scheduled_tasks()
    bot.telegram_set_commands()

    # Send startup message
    bot.telegram_send(format_startup_message())

    server.log.info("Bot components initialized")
