"""
GOLD SNIPER V2.0 [FREE] - Main Bot Application
==================================================
Advanced Gold (XAUUSD) Trading Signal Bot for MT5.
100% FREE - No paid indicators required!
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
import requests as http_requests

import config
from message_formatter import (
    format_signal_alert,
    format_tp1_hit, format_tp2_hit, format_tp3_hit, format_sl_hit,
    format_daily_summary, format_overall_stats, format_startup_message,
    format_trade_update,
)
from database import (
    init_db, save_trade, update_trade, get_active_trades,
    get_daily_stats, get_overall_stats, get_recent_trades,
    update_daily_stats, cleanup_old_data,
)
from price_monitor import PriceMonitor, TradeMonitor
from news_filter import NewsFilter
from keep_alive import KeepAlive
from webhook_handler import WebhookHandler
from pipeline import SignalPipeline

# ============================================================
# Logging Setup
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("GoldSniper")

UTC3 = timezone(timedelta(hours=config.UTC_OFFSET))

# ============================================================
# Flask App
# ============================================================
app = Flask(__name__)

# ============================================================
# Core Components (Initialized after app to avoid circular imports)
# ============================================================
webhook_handler = WebhookHandler()
pipeline = SignalPipeline(webhook_handler)
price_monitor = PriceMonitor()
news_filter = NewsFilter()
keep_alive = KeepAlive()
trade_monitor = None

# Stability check thread
stability_thread = None
stability_lock = threading.Lock()


# ============================================================
# Telegram Functions
# ============================================================

def telegram_send(text: str, parse_mode: str = None) -> bool:
    """Send a message to Telegram."""
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        resp = http_requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(f"Telegram error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False


def telegram_set_commands():
    """Set bot commands in Telegram."""
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/setMyCommands"
        commands = [
            {"command": "start", "description": "تشغيل البوت"},
            {"command": "stats", "description": "إحصائيات اليوم"},
            {"command": "overall", "description": "الإحصائيات التراكمية"},
            {"command": "recent", "description": "آخر 10 صفقات"},
            {"command": "active", "description": "الصفقة النشطة"},
            {"command": "close", "description": "إغلاق الصفقة يدوياً"},
            {"command": "news", "description": "الأخبار القادمة"},
            {"command": "price", "description": "سعر الذهب الحالي"},
        ]
        http_requests.post(url, json={"commands": commands}, timeout=10)
    except Exception as e:
        logger.error(f"Set commands error: {e}")


def start_telegram_polling():
    """Start polling for Telegram commands."""
    thread = threading.Thread(target=_telegram_poll_loop, daemon=True)
    thread.start()
    logger.info("Telegram polling started")


def _telegram_poll_loop():
    """Poll for Telegram updates (commands)."""
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
            resp = http_requests.get(url, params={
                "offset": offset,
                "timeout": 30,
                "allowed_updates": '["message"]'
            }, timeout=35)

            if resp.status_code != 200:
                time.sleep(5)
                continue

            data = resp.json()
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if chat_id != str(config.TELEGRAM_CHAT_ID):
                    continue

                _handle_command(text)

        except Exception as e:
            logger.error(f"Telegram poll error: {e}")
            time.sleep(5)


def _handle_command(text: str):
    """Handle Telegram bot commands."""
    cmd = text.strip().lower()

    if cmd == "/start":
        telegram_send(format_startup_message())

    elif cmd == "/stats":
        stats = get_daily_stats()
        telegram_send(format_daily_summary(stats))

    elif cmd == "/overall":
        stats = get_overall_stats()
        telegram_send(format_overall_stats(stats))

    elif cmd == "/recent":
        trades = get_recent_trades(10)
        if not trades:
            telegram_send("📊 لا توجد صفقات مسجلة بعد.")
            return
        lines = [f"🥇 آخر {len(trades)} صفقات:\n"]
        for t in trades:
            emoji = "✅" if t.get("result", "").startswith("TP") else "❌" if t.get("result") == "LOSS" else "⚖️"
            pnl = t.get("pnl_points", 0)
            lines.append(
                f"{emoji} {t.get('signal', '?')} @ {t.get('entry_price', 0):.2f} | "
                f"{pnl:+.2f}p | {t.get('result', '?')}"
            )
        telegram_send("\n".join(lines))

    elif cmd == "/active":
        trade = pipeline.get_active_trade()
        if not trade:
            pending = pipeline.get_pending_signal()
            if pending:
                telegram_send(
                    f"⏳ إشارة قيد المعالجة:\n"
                    f"📊 {pending['signal']} @ {pending['price_at_detection']:.2f}\n"
                    f"🔄 المرحلة: {pending['state']}"
                )
            else:
                telegram_send("📊 لا توجد صفقة نشطة حالياً.")
            return

        current_price = price_monitor.get_current_price()
        msg = (
            f"🥇 الصفقة النشطة:\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📍 {trade['signal']} @ {trade['entry_price']:.2f}\n"
            f"💰 السعر الحالي: {current_price:.2f}\n"
            f"🛑 SL: {trade['current_sl']:.2f}\n"
            f"🎯 TP1: {trade['tp1']:.2f} {'✅' if trade.get('tp1_hit_time') else '⏳'}\n"
            f"🎯 TP2: {trade['tp2']:.2f} {'✅' if trade.get('tp2_hit_time') else '⏳'}\n"
            f"🎯 TP3: {trade['tp3']:.2f} {'✅' if trade.get('tp3_hit_time') else '⏳'}\n"
            f"📊 الحالة: {trade['state']}\n"
            f"🆔 {trade['trade_id']}"
        )
        telegram_send(msg)

    elif cmd == "/close":
        trade = pipeline.get_active_trade()
        if not trade:
            telegram_send("📊 لا توجد صفقة نشطة للإغلاق.")
            return
        current_price = price_monitor.get_current_price()
        if current_price <= 0:
            telegram_send("⚠️ لا يمكن الحصول على السعر الحالي.")
            return
        closed = pipeline.force_close(current_price, "Manual close via /close")
        if closed:
            pnl = closed.get("pnl_points", 0)
            update_trade(closed["trade_id"], {
                "close_price": current_price,
                "pnl_points": pnl,
                "result": "MANUAL_CLOSE",
                "close_time": datetime.now(UTC3).isoformat(),
            })
            update_daily_stats()
            telegram_send(
                f"✅ تم إغلاق الصفقة يدوياً\n"
                f"💰 سعر الإغلاق: {current_price:.2f}\n"
                f"📊 النتيجة: {pnl:+.2f} نقطة"
            )
            pipeline.reset()

    elif cmd == "/news":
        telegram_send(news_filter.format_news_list())

    elif cmd == "/price":
        p = price_monitor.get_current_price()
        last = price_monitor.get_last_update_time()
        if p > 0:
            ago = int(time.time() - last)
            telegram_send(f"🥇 سعر الذهب الحالي: ${p:.2f}\n⏰ آخر تحديث: منذ {ago} ثانية")
        else:
            telegram_send("⚠️ لا يمكن الحصول على سعر الذهب حالياً.")


# ============================================================
# Signal Processing
# ============================================================

def process_signal(signal_data: dict):
    """
    Process a new signal through the full pipeline.
    This runs in a separate thread to avoid blocking webhooks.
    """
    global stability_thread

    with stability_lock:
        # Stage 1: Detection
        entry = pipeline.on_signal_detected(signal_data)
        if not entry:
            logger.info("Signal rejected at detection stage")
            return

        # Check trading hours
        if config.ENABLE_TRADING_HOURS:
            now_utc = datetime.now(timezone.utc)
            if not (config.TRADING_START_HOUR_UTC <= now_utc.hour < config.TRADING_END_HOUR_UTC):
                logger.info(f"Outside trading hours (UTC {now_utc.hour})")
                return

        # Check trading days
        if config.ENABLE_TRADING_DAYS:
            now_utc = datetime.now(timezone.utc)
            if now_utc.weekday() not in config.TRADING_DAYS:
                logger.info(f"Outside trading days (Weekday {now_utc.weekday()})")
                return

        # Check news filter
        if config.NEWS_FILTER_ENABLED:
            passed, reason = news_filter.check_news_pause()
            if not passed:
                logger.info(f"Signal rejected due to news: {reason}")
                return

        # Stage 2: Stability Check
        if config.STABILITY_ENABLED:
            logger.info(f"Starting stability check ({config.STABILITY_WINDOW_SECONDS}s)...")
            time.sleep(config.STABILITY_WINDOW_SECONDS)
            passed, reason = pipeline.check_stability()
            if not passed:
                logger.info(f"Signal rejected at stability stage: {reason}")
                return

        # Stage 3-12: Run Full Pipeline
        accepted, trade, summary = pipeline.run_pipeline()
        if not accepted:
            logger.info(f"Signal rejected by pipeline: {summary}")
            return

        # Stage 13: Activation & Notification
        active_trade = pipeline.activate_trade()
        if active_trade:
            # Save to DB
            save_trade(active_trade)
            # Send Telegram Alert
            telegram_send(format_signal_alert(active_trade), parse_mode="Markdown")
            logger.info(f"Trade activated and alert sent: {active_trade['trade_id']}")


# ============================================================
# Flask Routes
# ============================================================

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "name": config.BOT_NAME,
        "version": config.BOT_VERSION,
        "endpoints": {
            "GET /health": "Health check",
            "GET /status": "Bot status JSON",
            "POST /webhook": "Single webhook for FREE Pine Script"
        }
    })


@app.route('/health')
def health():
    return jsonify({"status": "ok", "version": config.BOT_VERSION})


@app.route('/status')
def status():
    active = pipeline.get_active_trade()
    pending = pipeline.get_pending_signal()
    return jsonify({
        "bot": config.BOT_NAME,
        "version": config.BOT_VERSION,
        "active_trade": active["trade_id"] if active else None,
        "pending_signal": pending["trade_id"] if pending else None,
        "price": price_monitor.get_current_price(),
        "last_update": price_monitor.get_last_update_time()
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    """Single webhook endpoint for the FREE Pine Script."""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON data"}), 400

        logger.info(f"Webhook received: {json.dumps(data)}")

        # Process via WebhookHandler
        result = webhook_handler.process_webhook(data)
        if not result:
            return jsonify({"status": "ignored", "message": "Signal invalid or filtered"}), 200

        # Start processing in background thread
        thread = threading.Thread(target=process_signal, args=(result,), daemon=True)
        thread.start()

        return jsonify({
            "status": "signal_received",
            "symbol": result["symbol"],
            "signal": result["signal"],
            "price": result["price"]
        }), 200

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================
# Scheduled Tasks
# ============================================================

def start_scheduled_tasks():
    """Start background thread for periodic tasks."""
    thread = threading.Thread(target=_scheduled_tasks_loop, daemon=True)
    thread.start()
    logger.info("Scheduled tasks started")


def _scheduled_tasks_loop():
    """Run periodic maintenance tasks."""
    last_cleanup = 0
    last_stats_update = 0

    while True:
        try:
            now = time.time()

            # Cleanup old data (once per day)
            if now - last_cleanup > 86400:
                cleanup_old_data(days=30)
                last_cleanup = now

            # Update daily stats (every hour)
            if now - last_stats_update > 3600:
                update_daily_stats()
                last_stats_update = now

            time.sleep(60)
        except Exception as e:
            logger.error(f"Scheduled tasks error: {e}")
            time.sleep(60)


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Main entry point for direct execution."""
    init_db()
    price_monitor.start()
    news_filter.start()
    keep_alive.start()

    # Initialize trade monitor
    global trade_monitor
    trade_monitor = TradeMonitor(price_monitor, pipeline, telegram_send)
    trade_monitor.start()

    start_telegram_polling()
    start_scheduled_tasks()
    telegram_set_commands()

    # Send startup message
    telegram_send(format_startup_message())

    logger.info(f"Starting {config.BOT_NAME} {config.BOT_VERSION} on port {config.PORT}...")
    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
