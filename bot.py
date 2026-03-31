"""
GOLD SNIPER V2.0 [FREE] - Main Bot Application
==================================================
Advanced Gold (XAUUSD) Trading Signal Bot for MT5.
100% FREE - No paid indicators required!

Architecture:
  - Flask web server for TradingView webhook
  - Telegram bot for signal delivery and commands
  - Real-time price monitoring for trade management
  - Multi-stage filtering pipeline (SMC + Supertrend + EMA + RSI + MACD)
  - ATR-based dynamic SL/TP calculation
  - Automatic SL adjustment on TP hits
  - News filter for high-impact events
  - Keep-alive for Render.com hosting

Endpoints:
  POST /webhook    - Single webhook for FREE Pine Script (all data in one)
  GET  /health     - Health check
  GET  /status     - Bot status JSON
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
from webhook_handler import WebhookHandler
from pipeline import SignalPipeline
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
# Core Components
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
                logger.info(f"Not a trading day ({now_utc.strftime('%A')})")
                return

        # Check news filter
        safe, reason = news_filter.is_safe_to_trade()
        if not safe:
            logger.info(f"News filter blocked: {reason}")
            telegram_send(f"⚠️ إشارة محتملة ولكن تم تجاهلها:\n{reason}")
            return

        # Stage 2: Stability check (in background thread)
        def _stability_then_filter():
            if config.STABILITY_ENABLED:
                time.sleep(config.STABILITY_WINDOW_SECONDS)

            passed, msg = pipeline.check_stability()
            if not passed:
                logger.info(f"Stability check failed: {msg}")
                return

            # Run full pipeline (Stages 3-10)
            accepted, trade, summary = pipeline.run_pipeline()

            if not accepted:
                logger.info(f"Pipeline rejected: {summary}")
                return

            # Activate trade
            active = pipeline.activate_trade()
            if not active:
                logger.info("Failed to activate trade")
                return

            # Save to database
            db_trade = {
                "trade_id": active["trade_id"],
                "symbol": active["symbol"],
                "direction": active["signal"],
                "entry_price": active["entry_price"],
                "stop_loss": active["stop_loss"],
                "tp1": active["tp1"],
                "tp2": active["tp2"],
                "tp3": active["tp3"],
                "current_sl": active["current_sl"],
                "atr_value": active.get("atr_value", 0),
                "confidence_score": active.get("confidence_score", 0),
                "reasons": active.get("reasons", ""),
                "signal_time": active.get("detected_at", datetime.now(UTC3)).isoformat()
                    if hasattr(active.get("detected_at", ""), "isoformat")
                    else str(active.get("detected_at", "")),
                "entry_time": active.get("entry_time", datetime.now(UTC3).isoformat()),
                "pipeline_stage": active["state"],
                "gainzalgo_signal": active["signal"],
                "smc_confirmed": 1 if active.get("smc_confirmed") else 0,
                "supertrend_confirmed": 1 if active.get("supertrend_confirmed") else 0,
                "ema_confirmed": 1 if active.get("ema_confirmed") else 0,
                "rsi_value": active.get("rsi_value"),
                "macd_value": active.get("macd_value"),
                "suggested_lot_size": active.get("suggested_lot_size", 0.01),
                "risk_reward_ratio": active.get("risk_reward_ratio", 0),
            }
            save_trade(db_trade)

            # Send Telegram alert
            msg = format_signal_alert(active)
            telegram_send(msg)

            logger.info(f"Trade ACTIVATED: {active['trade_id']} "
                         f"{active['signal']} @ {active['entry_price']:.2f}")

        stability_thread = threading.Thread(target=_stability_then_filter, daemon=True)
        stability_thread.start()


# ============================================================
# Flask Routes
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Single webhook endpoint for the FREE Pine Script.
    All indicator + SMC data comes in one payload.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        logger.info(f"Webhook received: {json.dumps(data, default=str)[:500]}")

        # Update price from webhook
        price = float(data.get("price", 0))
        if price > 0:
            price_monitor.update_price_from_webhook(price)

        # Process signal through webhook handler
        signal = webhook_handler.process_webhook(data)
        if signal:
            threading.Thread(target=process_signal, args=(signal,), daemon=True).start()
            return jsonify({"status": "signal_received", "signal": signal["signal"]}), 200

        return jsonify({"status": "no_signal"}), 200

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Render.com."""
    return jsonify({
        "status": "ok",
        "bot": config.BOT_NAME,
        "version": config.BOT_VERSION,
        "time": datetime.now(UTC3).isoformat(),
    }), 200


@app.route("/status", methods=["GET"])
def status():
    """Detailed bot status."""
    active = pipeline.get_active_trade()
    pending = pipeline.get_pending_signal()
    price = price_monitor.get_current_price()
    stats = get_overall_stats()

    return jsonify({
        "bot": config.BOT_NAME,
        "version": config.BOT_VERSION,
        "time": datetime.now(UTC3).isoformat(),
        "gold_price": price,
        "active_trade": {
            "exists": active is not None and active.get("state") not in ("CLOSED", "REJECTED"),
            "trade_id": active["trade_id"] if active else None,
            "signal": active["signal"] if active else None,
            "state": active["state"] if active else None,
        } if active else None,
        "pending_signal": pending is not None,
        "stats": stats,
        "filters": {
            "smc": config.SMC_FILTER_ENABLED,
            "supertrend": config.SUPERTREND_FILTER_ENABLED,
            "ema": config.EMA_TREND_FILTER_ENABLED,
            "rsi": config.RSI_FILTER_ENABLED,
            "macd": config.MACD_FILTER_ENABLED,
            "news": config.NEWS_FILTER_ENABLED,
            "kill_zones": config.KILL_ZONES_ENABLED,
        },
    }), 200


@app.route("/", methods=["GET"])
def index():
    """Root endpoint."""
    return jsonify({
        "name": f"{config.BOT_NAME} {config.BOT_VERSION}",
        "description": "Advanced Gold (XAUUSD) Trading Signal Bot - 100% FREE",
        "endpoints": {
            "POST /webhook": "Single webhook for FREE Pine Script",
            "GET /health": "Health check",
            "GET /status": "Bot status",
        }
    }), 200


# ============================================================
# Scheduled Tasks
# ============================================================

def start_scheduled_tasks():
    """Start background scheduled tasks."""

    def _daily_summary_loop():
        while True:
            try:
                now = datetime.now(UTC3)
                if now.hour == 23 and now.minute == 0:
                    stats = get_daily_stats()
                    if stats.get("total_trades", 0) > 0:
                        telegram_send(format_daily_summary(stats))
                    cleanup_old_data(days=90)
                time.sleep(60)
            except Exception as e:
                logger.error(f"Daily summary error: {e}")
                time.sleep(60)

    threading.Thread(target=_daily_summary_loop, daemon=True).start()
    logger.info("Scheduled tasks started")


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Initialize and start the bot."""
    global trade_monitor

    logger.info(f"Starting {config.BOT_NAME} {config.BOT_VERSION}...")

    init_db()
    telegram_set_commands()

    price_monitor.start()
    news_filter.start()
    keep_alive.start()

    trade_monitor = TradeMonitor(price_monitor, pipeline, telegram_send)
    trade_monitor.start()

    start_telegram_polling()
    start_scheduled_tasks()

    telegram_send(format_startup_message())

    logger.info(f"Bot ready! Listening on {config.HOST}:{config.PORT}")

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
