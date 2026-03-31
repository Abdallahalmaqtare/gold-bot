"""
Gunicorn configuration for Render.com deployment.
Clean version without decorative characters.
"""

import multiprocessing
import os

# Server settings
bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
workers = 1
threads = 4
timeout = 120
keepalive = 5

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

def post_fork(server, worker):
    """
    Initialize bot components after gunicorn forks the worker.
    This ensures background tasks run alongside the web server.
    """
    import bot
    from database import init_db
    from message_formatter import format_startup_message
    
    server.log.info("Initializing bot components in worker...")
    
    try:
        # 1. Initialize Database
        init_db()
        
        # 2. Start Background Services
        bot.price_monitor.start()
        bot.news_filter.start()
        bot.keep_alive.start()
        
        # 3. Initialize Trade Monitor
        from price_monitor import TradeMonitor
        bot.trade_monitor = TradeMonitor(bot.price_monitor, bot.pipeline, bot.telegram_send)
        bot.trade_monitor.start()
        
        # 4. Start Telegram & Scheduled Tasks
        bot.start_telegram_polling()
        bot.start_scheduled_tasks()
        bot.telegram_set_commands()
        
        # 5. Send Startup Notification
        bot.telegram_send(format_startup_message())
        
        server.log.info("Bot components initialized successfully")
    except Exception as e:
        server.log.error(f"Failed to initialize bot components: {str(e)}")
