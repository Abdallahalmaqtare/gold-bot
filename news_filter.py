"""
GOLD SNIPER V2.0 - Message Formatter
=======================================
Professional Telegram message templates for gold trading signals.

Message Types:
  1. Signal Alert     → New trade signal with full details
  2. TP1 Hit          → First target reached + SL adjustment
  3. TP2 Hit          → Second target reached + SL adjustment
  4. TP3 Hit          → Third target reached (full win)
  5. SL Hit           → Stop loss triggered
  6. Trade Update     → SL/TP adjustments
  7. Daily Summary    → End of day statistics
  8. Startup          → Bot initialization message
"""

from datetime import datetime, timezone, timedelta
import config

UTC3 = timezone(timedelta(hours=config.UTC_OFFSET))

HEADER = config.BOT_DISPLAY_HEADER
SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━"


def _now_utc3_str():
    return datetime.now(UTC3).strftime("%Y-%m-%d %H:%M:%S")


def _time_utc3_str():
    return datetime.now(UTC3).strftime("%H:%M:%S")


# ============================================================
# 1. Signal Alert (New Trade)
# ============================================================

def format_signal_alert(trade: dict) -> str:
    """
    Main signal message with entry, SL, and 3 TP levels.
    """
    direction = trade["signal"]
    direction_emoji = "🟢 شراء (BUY)" if direction == "BUY" else "🔴 بيع (SELL)"
    direction_arrow = "⬆️" if direction == "BUY" else "⬇️"

    # Confidence bar
    score = trade.get("confidence_score", 0)
    filled = int(score)
    empty = 10 - filled
    confidence_bar = "🟩" * filled + "⬜" * empty

    # Risk-Reward
    rr = trade.get("risk_reward_ratio", 0)

    # Lot size
    lot = trade.get("suggested_lot_size", 0.01)

    # Reasons
    reasons = trade.get("reasons", "")

    msg = (
        f"{HEADER}\n"
        f"{SEPARATOR}\n"
        f"🚨 إشارة تداول جديدة 🚨\n"
        f"{SEPARATOR}\n\n"
        f"📊 الزوج: {config.SYMBOL_DISPLAY}\n"
        f"📍 الاتجاه: {direction_emoji} {direction_arrow}\n"
        f"💰 سعر الدخول: {trade['entry_price']:.2f}\n\n"
        f"🛑 وقف الخسارة (SL): {trade['stop_loss']:.2f}\n"
        f"🎯 الهدف الأول (TP1): {trade['tp1']:.2f}\n"
        f"🎯 الهدف الثاني (TP2): {trade['tp2']:.2f}\n"
        f"🎯 الهدف الثالث (TP3): {trade['tp3']:.2f}\n\n"
        f"{SEPARATOR}\n"
        f"📈 ATR: {trade.get('atr_value', 0):.2f}\n"
        f"📊 نسبة المخاطرة/الربح: 1:{rr:.1f}\n"
        f"📦 حجم العقد المقترح: {lot} Lot\n"
        f"🔥 درجة الثقة: {score:.1f}/10\n"
        f"{confidence_bar}\n\n"
    )

    if reasons:
        msg += (
            f"📋 أسباب الدخول:\n"
            f"{reasons}\n\n"
        )

    msg += (
        f"{SEPARATOR}\n"
        f"⏰ {_now_utc3_str()} (UTC+3)\n"
        f"🆔 {trade.get('trade_id', 'N/A')}\n"
        f"{SEPARATOR}\n"
        f"⚠️ تنبيه: هذه إشارة تحليلية. تداول بمسؤولية."
    )

    return msg


# ============================================================
# 2. TP1 Hit Message
# ============================================================

def format_tp1_hit(trade: dict, event: dict) -> str:
    """Message when TP1 is reached."""
    direction_emoji = "🟢" if trade["signal"] == "BUY" else "🔴"
    pnl = event.get("pnl_points", 0)

    return (
        f"{HEADER}\n"
        f"{SEPARATOR}\n"
        f"🎉🎉🎉 مبروك! تم الوصول للهدف الأول! 🎉🎉🎉\n"
        f"{SEPARATOR}\n\n"
        f"{direction_emoji} {config.SYMBOL_DISPLAY} | {trade['signal']}\n"
        f"💰 سعر الدخول: {trade['entry_price']:.2f}\n"
        f"✅ الهدف الأول (TP1): {trade['tp1']:.2f} ✅\n"
        f"📈 الربح: +{pnl:.2f} نقطة\n\n"
        f"{SEPARATOR}\n"
        f"🔄 تحديث إدارة الصفقة:\n"
        f"🛡️ تم نقل وقف الخسارة إلى نقطة الدخول (Breakeven)\n"
        f"🛑 وقف الخسارة الجديد: {event.get('new_sl', trade['entry_price']):.2f}\n\n"
        f"🎯 الأهداف المتبقية:\n"
        f"🎯 الهدف الثاني (TP2): {trade['tp2']:.2f}\n"
        f"🎯 الهدف الثالث (TP3): {trade['tp3']:.2f}\n\n"
        f"💡 نصيحة: يمكنك إغلاق جزء من الصفقة وترك الباقي للأهداف التالية.\n"
        f"{SEPARATOR}\n"
        f"⏰ {_now_utc3_str()} (UTC+3)\n"
        f"🆔 {trade.get('trade_id', 'N/A')}"
    )


# ============================================================
# 3. TP2 Hit Message
# ============================================================

def format_tp2_hit(trade: dict, event: dict) -> str:
    """Message when TP2 is reached."""
    direction_emoji = "🟢" if trade["signal"] == "BUY" else "🔴"
    pnl = event.get("pnl_points", 0)

    return (
        f"{HEADER}\n"
        f"{SEPARATOR}\n"
        f"🏆🏆 ممتاز! تم الوصول للهدف الثاني! 🏆🏆\n"
        f"{SEPARATOR}\n\n"
        f"{direction_emoji} {config.SYMBOL_DISPLAY} | {trade['signal']}\n"
        f"💰 سعر الدخول: {trade['entry_price']:.2f}\n"
        f"✅ الهدف الأول (TP1): {trade['tp1']:.2f} ✅\n"
        f"✅ الهدف الثاني (TP2): {trade['tp2']:.2f} ✅\n"
        f"📈 الربح: +{pnl:.2f} نقطة\n\n"
        f"{SEPARATOR}\n"
        f"🔄 تحديث إدارة الصفقة:\n"
        f"🛡️ تم نقل وقف الخسارة إلى مستوى الهدف الأول\n"
        f"🛑 وقف الخسارة الجديد: {event.get('new_sl', trade['tp1']):.2f}\n\n"
        f"🎯 الهدف المتبقي:\n"
        f"🎯 الهدف الثالث (TP3): {trade['tp3']:.2f}\n\n"
        f"💡 نصيحة: أغلق 50% إضافية واترك الباقي للهدف الثالث.\n"
        f"{SEPARATOR}\n"
        f"⏰ {_now_utc3_str()} (UTC+3)\n"
        f"🆔 {trade.get('trade_id', 'N/A')}"
    )


# ============================================================
# 4. TP3 Hit Message (Full Win)
# ============================================================

def format_tp3_hit(trade: dict, event: dict) -> str:
    """Message when TP3 is reached - full win!"""
    direction_emoji = "🟢" if trade["signal"] == "BUY" else "🔴"
    pnl = event.get("pnl_points", 0)

    return (
        f"{HEADER}\n"
        f"{SEPARATOR}\n"
        f"💎💎💎 رائع! تم تحقيق جميع الأهداف! 💎💎💎\n"
        f"{SEPARATOR}\n\n"
        f"{direction_emoji} {config.SYMBOL_DISPLAY} | {trade['signal']}\n"
        f"💰 سعر الدخول: {trade['entry_price']:.2f}\n"
        f"✅ الهدف الأول (TP1): {trade['tp1']:.2f} ✅\n"
        f"✅ الهدف الثاني (TP2): {trade['tp2']:.2f} ✅\n"
        f"✅ الهدف الثالث (TP3): {trade['tp3']:.2f} ✅\n\n"
        f"🏆 إجمالي الربح: +{pnl:.2f} نقطة\n"
        f"📊 نسبة المخاطرة/الربح: 1:{trade.get('risk_reward_ratio', 0):.1f}\n\n"
        f"🎊 صفقة مكتملة بنجاح! 🎊\n"
        f"{SEPARATOR}\n"
        f"⏰ {_now_utc3_str()} (UTC+3)\n"
        f"🆔 {trade.get('trade_id', 'N/A')}"
    )


# ============================================================
# 5. SL Hit Message
# ============================================================

def format_sl_hit(trade: dict, event: dict) -> str:
    """Message when Stop Loss is hit."""
    direction_emoji = "🟢" if trade["signal"] == "BUY" else "🔴"
    pnl = event.get("pnl_points", 0)
    result = event.get("result", "LOSS")

    if result == "BREAKEVEN":
        header_text = "⚖️ تم إغلاق الصفقة عند نقطة التعادل ⚖️"
        emoji = "⚖️"
    elif result in ("TP1_HIT", "TP2_HIT"):
        header_text = f"🛡️ تم إغلاق الصفقة بربح ({result}) 🛡️"
        emoji = "🛡️"
    else:
        header_text = "❌ تم ضرب وقف الخسارة ❌"
        emoji = "❌"

    return (
        f"{HEADER}\n"
        f"{SEPARATOR}\n"
        f"{header_text}\n"
        f"{SEPARATOR}\n\n"
        f"{direction_emoji} {config.SYMBOL_DISPLAY} | {trade['signal']}\n"
        f"💰 سعر الدخول: {trade['entry_price']:.2f}\n"
        f"🛑 سعر الإغلاق: {event.get('price', 0):.2f}\n"
        f"{emoji} النتيجة: {pnl:+.2f} نقطة ({result})\n\n"
        f"{SEPARATOR}\n"
        f"⏰ {_now_utc3_str()} (UTC+3)\n"
        f"🆔 {trade.get('trade_id', 'N/A')}"
    )


# ============================================================
# 6. Trade Update Message
# ============================================================

def format_trade_update(trade: dict, update_type: str, details: str) -> str:
    """Generic trade update message."""
    return (
        f"{HEADER}\n"
        f"{SEPARATOR}\n"
        f"🔄 تحديث الصفقة | {update_type}\n"
        f"{SEPARATOR}\n\n"
        f"📊 {config.SYMBOL_DISPLAY} | {trade['signal']}\n"
        f"{details}\n\n"
        f"⏰ {_now_utc3_str()} (UTC+3)\n"
        f"🆔 {trade.get('trade_id', 'N/A')}"
    )


# ============================================================
# 7. Daily Summary
# ============================================================

def format_daily_summary(stats: dict) -> str:
    """End of day statistics summary."""
    total = stats.get("total_trades", 0)
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    be = stats.get("breakeven", 0)
    tp1 = stats.get("tp1_hits", 0)
    tp2 = stats.get("tp2_hits", 0)
    tp3 = stats.get("tp3_hits", 0)
    pnl = stats.get("total_pnl_points", 0)
    wr = stats.get("win_rate", 0)

    pnl_emoji = "📈" if pnl >= 0 else "📉"

    return (
        f"{HEADER}\n"
        f"{SEPARATOR}\n"
        f"📊 ملخص اليوم 📊\n"
        f"{SEPARATOR}\n\n"
        f"🔢 إجمالي الصفقات: {total}\n"
        f"✅ رابحة: {wins}\n"
        f"❌ خاسرة: {losses}\n"
        f"⚖️ تعادل: {be}\n\n"
        f"🎯 الأهداف المحققة:\n"
        f"  TP1: {tp1} مرة\n"
        f"  TP2: {tp2} مرة\n"
        f"  TP3: {tp3} مرة\n\n"
        f"{pnl_emoji} إجمالي النقاط: {pnl:+.2f}\n"
        f"📈 نسبة الفوز: {wr:.1f}%\n"
        f"{SEPARATOR}\n"
        f"⏰ {_now_utc3_str()} (UTC+3)"
    )


# ============================================================
# 8. Overall Stats
# ============================================================

def format_overall_stats(stats: dict) -> str:
    """Overall cumulative statistics."""
    return (
        f"{HEADER}\n"
        f"{SEPARATOR}\n"
        f"🧮 الإحصائيات التراكمية\n"
        f"{SEPARATOR}\n\n"
        f"🔢 إجمالي الصفقات: {stats.get('total', 0)}\n"
        f"✅ رابحة: {stats.get('wins', 0)}\n"
        f"❌ خاسرة: {stats.get('losses', 0)}\n"
        f"⚖️ تعادل: {stats.get('breakeven', 0)}\n\n"
        f"🎯 الأهداف:\n"
        f"  TP1: {stats.get('tp1_hits', 0)} | "
        f"TP2: {stats.get('tp2_hits', 0)} | "
        f"TP3: {stats.get('tp3_hits', 0)}\n\n"
        f"📈 نسبة الفوز: {stats.get('win_rate', 0):.1f}%\n"
        f"📊 متوسط RR: 1:{stats.get('avg_rr', 0):.1f}\n"
        f"💰 إجمالي النقاط: {stats.get('total_pnl', 0):+.2f}\n"
        f"{SEPARATOR}"
    )


# ============================================================
# 9. Startup Message
# ============================================================

def format_startup_message() -> str:
    """Bot startup message."""
    now = datetime.now(UTC3).strftime("%Y-%m-%d %H:%M:%S")

    filters = []
    if config.SIGNAL_DETECTION_ENABLED:
        filters.append("✅ Pine Script Signal Detection (FREE)")
    if config.SMC_FILTER_ENABLED:
        filters.append("✅ SMC (Order Blocks + FVG + BOS)")
    if config.SUPERTREND_FILTER_ENABLED:
        filters.append("✅ Supertrend Trend Filter")
    if config.EMA_TREND_FILTER_ENABLED:
        filters.append(f"✅ EMA Trend (EMA {config.EMA_FAST}/{config.EMA_SLOW}/{config.EMA_TREND})")
    if config.RSI_FILTER_ENABLED:
        filters.append(f"✅ RSI Filter ({config.RSI_PERIOD}) + Divergence")
    if config.MACD_FILTER_ENABLED:
        filters.append(f"✅ MACD Confirmation ({config.MACD_FAST}/{config.MACD_SLOW}/{config.MACD_SIGNAL})")
    if config.WICK_FILTER_ENABLED:
        filters.append("✅ Wick Filter (Anti-Weak-Impulse)")
    if config.KILL_ZONES_ENABLED:
        filters.append("✅ Kill Zone Trading (London/NY)")
    if config.NEWS_FILTER_ENABLED:
        filters.append("✅ News Filter (High-Impact)")

    filters_str = "\n".join(filters)

    return (
        f"🥇 {config.BOT_NAME} {config.BOT_VERSION} 🥇\n"
        f"{SEPARATOR}\n"
        f"نظام تداول الذهب الذكي\n"
        f"{SEPARATOR}\n\n"
        f"⏰ {now} (UTC+3)\n\n"
        f"📊 الأداة: {config.SYMBOL_DISPLAY}\n"
        f"⏱ الإطار الزمني: {config.LTF_TIMEFRAME} (دخول) | {config.HTF_TIMEFRAME} (اتجاه)\n\n"
        f"🔧 الفلاتر النشطة:\n"
        f"{filters_str}\n\n"
        f"📐 إعدادات ATR:\n"
        f"  SL: {config.ATR_SL_MULTIPLIER}x ATR\n"
        f"  TP1: {config.ATR_TP1_MULTIPLIER}x ATR\n"
        f"  TP2: {config.ATR_TP2_MULTIPLIER}x ATR\n"
        f"  TP3: {config.ATR_TP3_MULTIPLIER}x ATR\n\n"
        f"🛡️ إدارة الصفقة:\n"
        f"  • نقل SL إلى Breakeven عند TP1\n"
        f"  • نقل SL إلى TP1 عند TP2\n"
        f"  • الحد الأدنى للثقة: {config.MIN_CONFIDENCE_SCORE}/10\n\n"
        f"🕐 ساعات العمل: {config.TRADING_START_HOUR_UTC + config.UTC_OFFSET}:00 - "
        f"{config.TRADING_END_HOUR_UTC + config.UTC_OFFSET}:00 (UTC+3)\n"
        f"📅 أيام العمل: الاثنين - الجمعة\n\n"
        f"{SEPARATOR}\n"
        f"📌 الأوامر:\n"
        f"/start - تشغيل البوت\n"
        f"/stats - إحصائيات اليوم\n"
        f"/overall - الإحصائيات التراكمية\n"
        f"/recent - آخر 10 صفقات\n"
        f"/active - الصفقة النشطة\n"
        f"/close - إغلاق الصفقة يدوياً\n"
        f"{SEPARATOR}"
    )
