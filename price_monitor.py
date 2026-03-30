"""
GOLD SNIPER V2.0 [FREE] - Signal Pipeline Engine
====================================================
Multi-Stage Filtering Pipeline (100% FREE):
  Stage 1:  Signal Detection (from FREE Pine Script)
  Stage 2:  Signal Stability (60s persistence)
  Stage 3:  SMC Filter (Order Block / FVG / BOS - built into Pine Script)
  Stage 4:  Supertrend Trend Alignment
  Stage 5:  EMA 200 Trend Confirmation
  Stage 6:  RSI Filter + Divergence Detection
  Stage 7:  MACD Momentum Confirmation
  Stage 8:  Wick Filter (Anti-Weak-Impulse)
  Stage 9:  Bollinger Bands Squeeze + Volume Filter
  Stage 10: Kill Zone Check (bonus)
  Stage 11: Confidence Score Calculation
  Stage 12: ATR-Based SL/TP Calculation
  Stage 13: Trade Execution & Monitoring

Each filter adds to the confidence score. Only signals with
score >= MIN_CONFIDENCE_SCORE are accepted.
"""

import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple, List

import config
from webhook_handler import WebhookHandler

logger = logging.getLogger(__name__)

UTC3 = timezone(timedelta(hours=config.UTC_OFFSET))


class SignalPipeline:
    """
    Advanced multi-stage pipeline for gold trading signals.
    100% FREE - No paid indicators needed.
    """

    # Trade states
    STATE_DETECTED = "DETECTED"
    STATE_STABILITY_CHECK = "STABILITY_CHECK"
    STATE_FILTERING = "FILTERING"
    STATE_READY = "READY"
    STATE_ACTIVE = "ACTIVE"
    STATE_TP1_HIT = "TP1_HIT"
    STATE_TP2_HIT = "TP2_HIT"
    STATE_TP3_HIT = "TP3_HIT"
    STATE_CLOSED = "CLOSED"
    STATE_REJECTED = "REJECTED"

    def __init__(self, webhook_handler: WebhookHandler):
        self.wh = webhook_handler
        self._active_trade: Optional[dict] = None
        self._pending_signal: Optional[dict] = None

    # ----------------------------------------------------------
    # Stage 1: Signal Detection
    # ----------------------------------------------------------

    def on_signal_detected(self, signal_data: dict) -> Optional[dict]:
        """
        Stage 1: A new signal has been detected from the FREE Pine Script.
        Initialize pipeline entry.
        """
        if self._active_trade and self._active_trade["state"] not in (
            self.STATE_CLOSED, self.STATE_REJECTED
        ):
            logger.info("Pipeline: active trade exists, rejecting new signal")
            return None

        trade_id = f"GS_{datetime.now(UTC3).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        entry = {
            "trade_id": trade_id,
            "symbol": signal_data["symbol"],
            "signal": signal_data["signal"],
            "price_at_detection": signal_data["price"],
            "atr_from_webhook": signal_data.get("atr", 0),
            "detected_at": signal_data["received_at"],
            "detected_ts": signal_data.get("received_ts", time.time()),
            "state": self.STATE_DETECTED,
            "confidence_score": 0.0,
            "confidence_details": {},
            "filters_passed": [],
            "filters_failed": [],
            # Trade levels (calculated later)
            "entry_price": None,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "tp3": None,
            "current_sl": None,
            "atr_value": None,
            # Results
            "result": "PENDING",
            "close_price": None,
            "pnl_points": 0,
            # Filter data
            "smc_confirmed": False,
            "supertrend_confirmed": False,
            "ema_confirmed": False,
            "rsi_value": None,
            "macd_value": None,
            # Bonus data from Pine Script
            "bb_squeeze": signal_data.get("bb_squeeze", False),
            "vol_high": signal_data.get("vol_high", False),
            "rsi_divergence": signal_data.get("rsi_divergence", False),
            "kill_zone_from_tv": signal_data.get("kill_zone", False),
            "market_structure": signal_data.get("market_structure", "NONE"),
            "confidence_from_tv": signal_data.get("confidence_from_tv", 0),
        }

        self._pending_signal = entry
        logger.info(f"Pipeline Stage 1: {trade_id} {signal_data['signal']} @ "
                     f"{signal_data['price']:.2f} detected (FREE Pine Script)")

        return entry

    # ----------------------------------------------------------
    # Stage 2: Stability Check
    # ----------------------------------------------------------

    def check_stability(self) -> Tuple[bool, str]:
        """
        Stage 2: Check if signal persists after stability window.
        """
        if not self._pending_signal:
            return False, "No pending signal"

        if not config.STABILITY_ENABLED:
            self._pending_signal["filters_passed"].append("stability_bypassed")
            return True, "Stability check disabled"

        elapsed = time.time() - self._pending_signal["detected_ts"]
        if elapsed < config.STABILITY_WINDOW_SECONDS:
            return False, f"Waiting: {config.STABILITY_WINDOW_SECONDS - elapsed:.0f}s remaining"

        # Check if signal still exists and direction hasn't changed
        current_signal = self.wh.get_signal_data()
        if current_signal is None:
            self._pending_signal["state"] = self.STATE_REJECTED
            self._pending_signal["filters_failed"].append("stability_signal_vanished")
            return False, "Signal vanished during stability check"

        if current_signal["signal"] != self._pending_signal["signal"]:
            self._pending_signal["state"] = self.STATE_REJECTED
            self._pending_signal["filters_failed"].append("stability_direction_changed")
            return False, "Signal direction changed"

        self._pending_signal["filters_passed"].append("stability")
        self._pending_signal["state"] = self.STATE_FILTERING
        logger.info(f"Stage 2 PASS: Signal stable for {elapsed:.0f}s")
        return True, "Stability confirmed"

    # ----------------------------------------------------------
    # Stage 3: SMC Filter (Order Blocks / FVG / BOS)
    # ----------------------------------------------------------

    def check_smc_filter(self) -> Tuple[bool, str, float]:
        """
        Stage 3: Smart Money Concepts filter.
        All SMC data comes from the FREE Pine Script.
        Returns: (passed, reason, score_contribution)
        """
        if not self._pending_signal:
            return False, "No pending signal", 0

        if not config.SMC_FILTER_ENABLED:
            self._pending_signal["filters_passed"].append("smc_bypassed")
            return True, "SMC filter disabled", 0

        indicator = self.wh.get_indicator_data()
        smc = self.wh.get_smc_state()
        signal = self._pending_signal["signal"]
        score = 0.0
        reasons = []

        # Get SMC data (from the single webhook)
        if indicator and indicator.get("ob_type", "none") != "none":
            ob_type = indicator["ob_type"]
            ob_high = indicator.get("ob_high", 0)
            ob_low = indicator.get("ob_low", 0)
            fvg_type = indicator.get("fvg_type", "none")
            bos = indicator.get("bos", "none")
            market_structure = indicator.get("market_structure", "NONE")
            price = indicator["price"]
        elif smc:
            ob_type = smc["order_block"]
            ob_high = smc["ob_high"]
            ob_low = smc["ob_low"]
            fvg_type = smc.get("fvg", "none")
            bos = smc.get("bos", "none")
            market_structure = smc.get("market_structure", "NONE")
            price = smc["price"]
        else:
            self._pending_signal["filters_passed"].append("smc_no_data")
            logger.warning("Stage 3: No SMC data available, allowing pass")
            return True, "No SMC data (allowed)", 0

        # Check Market Structure alignment
        if market_structure != "NONE":
            if (signal == "BUY" and market_structure == "BULLISH") or \
               (signal == "SELL" and market_structure == "BEARISH"):
                score += 0.5
                reasons.append(f"Market Structure: {market_structure}")

        # Check Order Block alignment
        if signal == "BUY":
            if ob_type == "bullish":
                if ob_low > 0 and ob_high > 0:
                    if ob_low - config.SMC_TOLERANCE_POINTS <= price <= ob_high + config.SMC_TOLERANCE_POINTS:
                        score += 2.5
                        reasons.append(f"Inside Bullish OB [{ob_low:.2f}-{ob_high:.2f}]")
                    else:
                        score += 1.0
                        reasons.append("Bullish OB present (price outside)")
                else:
                    score += 1.5
                    reasons.append("Bullish OB confirmed")
            elif ob_type == "bearish":
                self._pending_signal["filters_failed"].append("smc_ob_conflict")
                return False, "BUY signal conflicts with Bearish OB", 0
        else:  # SELL
            if ob_type == "bearish":
                if ob_low > 0 and ob_high > 0:
                    if ob_low - config.SMC_TOLERANCE_POINTS <= price <= ob_high + config.SMC_TOLERANCE_POINTS:
                        score += 2.5
                        reasons.append(f"Inside Bearish OB [{ob_low:.2f}-{ob_high:.2f}]")
                    else:
                        score += 1.0
                        reasons.append("Bearish OB present (price outside)")
                else:
                    score += 1.5
                    reasons.append("Bearish OB confirmed")
            elif ob_type == "bullish":
                self._pending_signal["filters_failed"].append("smc_ob_conflict")
                return False, "SELL signal conflicts with Bullish OB", 0

        # Check FVG alignment (bonus)
        if fvg_type != "none":
            if (signal == "BUY" and fvg_type == "bullish") or \
               (signal == "SELL" and fvg_type == "bearish"):
                score += 0.5
                reasons.append(f"{fvg_type.title()} FVG confluence")

        # Check BOS (Break of Structure) alignment (bonus)
        if bos != "none":
            if (signal == "BUY" and "bullish" in bos) or \
               (signal == "SELL" and "bearish" in bos):
                score += 0.5
                reasons.append(f"BOS confirmed: {bos}")
            # CHoCH (Change of Character) is even stronger
            if "choch" in bos:
                score += 0.3
                reasons.append("CHoCH detected (strong reversal)")

        self._pending_signal["smc_confirmed"] = score > 0
        self._pending_signal["filters_passed"].append("smc")
        reason_str = " | ".join(reasons) if reasons else "SMC partial match"
        logger.info(f"Stage 3 PASS: {reason_str} (score: +{score:.1f})")
        return True, reason_str, score

    # ----------------------------------------------------------
    # Stage 4: Supertrend Filter
    # ----------------------------------------------------------

    def check_supertrend(self) -> Tuple[bool, str, float]:
        """
        Stage 4: Supertrend trend alignment.
        Data comes from the FREE Pine Script.
        """
        if not self._pending_signal:
            return False, "No pending signal", 0

        if not config.SUPERTREND_FILTER_ENABLED:
            self._pending_signal["filters_passed"].append("supertrend_bypassed")
            return True, "Supertrend filter disabled", 0

        indicator = self.wh.get_indicator_data()
        st = self.wh.get_supertrend_state()
        signal = self._pending_signal["signal"]

        if indicator and indicator.get("supertrend") in ("UP", "DOWN"):
            trend = indicator["supertrend"]
            st_value = indicator.get("supertrend_value", 0)
        elif st:
            trend = st["trend"]
            st_value = st["supertrend_value"]
        else:
            self._pending_signal["filters_passed"].append("supertrend_no_data")
            logger.warning("Stage 4: No Supertrend data, allowing pass")
            return True, "No Supertrend data (allowed)", 0

        if signal == "BUY" and trend == "UP":
            self._pending_signal["supertrend_confirmed"] = True
            self._pending_signal["filters_passed"].append("supertrend")
            logger.info(f"Stage 4 PASS: Supertrend UP aligns with BUY (ST: {st_value:.2f})")
            return True, f"Supertrend UP ({st_value:.2f})", 1.5
        elif signal == "SELL" and trend == "DOWN":
            self._pending_signal["supertrend_confirmed"] = True
            self._pending_signal["filters_passed"].append("supertrend")
            logger.info(f"Stage 4 PASS: Supertrend DOWN aligns with SELL (ST: {st_value:.2f})")
            return True, f"Supertrend DOWN ({st_value:.2f})", 1.5
        else:
            self._pending_signal["filters_failed"].append("supertrend_conflict")
            logger.info(f"Stage 4 FAIL: {signal} vs Supertrend {trend}")
            return False, f"{signal} conflicts with Supertrend {trend}", 0

    # ----------------------------------------------------------
    # Stage 5: EMA Trend Filter
    # ----------------------------------------------------------

    def check_ema_trend(self) -> Tuple[bool, str, float]:
        """
        Stage 5: EMA 200 trend confirmation.
        """
        if not self._pending_signal:
            return False, "No pending signal", 0

        if not config.EMA_TREND_FILTER_ENABLED:
            self._pending_signal["filters_passed"].append("ema_bypassed")
            return True, "EMA filter disabled", 0

        indicator = self.wh.get_indicator_data()
        if not indicator or indicator.get("ema_200", 0) == 0:
            self._pending_signal["filters_passed"].append("ema_no_data")
            return True, "No EMA data (allowed)", 0

        price = indicator["price"]
        ema_200 = indicator["ema_200"]
        ema_fast = indicator.get("ema_fast", 0)
        ema_slow = indicator.get("ema_slow", 0)
        signal = self._pending_signal["signal"]
        score = 0.0
        reasons = []

        # EMA 200 trend
        if signal == "BUY" and price > ema_200:
            score += 1.0
            reasons.append(f"Price above EMA200 ({ema_200:.2f})")
        elif signal == "SELL" and price < ema_200:
            score += 1.0
            reasons.append(f"Price below EMA200 ({ema_200:.2f})")
        else:
            score += 0.0
            reasons.append(f"Counter-trend to EMA200 ({ema_200:.2f})")

        # EMA crossover bonus
        if ema_fast > 0 and ema_slow > 0:
            if signal == "BUY" and ema_fast > ema_slow:
                score += 0.5
                reasons.append("EMA fast > slow (bullish)")
            elif signal == "SELL" and ema_fast < ema_slow:
                score += 0.5
                reasons.append("EMA fast < slow (bearish)")

        self._pending_signal["ema_confirmed"] = score > 0
        self._pending_signal["filters_passed"].append("ema")
        reason_str = " | ".join(reasons)
        logger.info(f"Stage 5: {reason_str} (score: +{score:.1f})")
        return True, reason_str, score

    # ----------------------------------------------------------
    # Stage 6: RSI Filter + Divergence
    # ----------------------------------------------------------

    def check_rsi(self) -> Tuple[bool, str, float]:
        """
        Stage 6: RSI filter - avoid extreme zones and detect divergence.
        """
        if not self._pending_signal:
            return False, "No pending signal", 0

        if not config.RSI_FILTER_ENABLED:
            self._pending_signal["filters_passed"].append("rsi_bypassed")
            return True, "RSI filter disabled", 0

        indicator = self.wh.get_indicator_data()
        if not indicator or indicator.get("rsi", 0) == 0:
            self._pending_signal["filters_passed"].append("rsi_no_data")
            return True, "No RSI data (allowed)", 0

        rsi = indicator["rsi"]
        signal = self._pending_signal["signal"]
        score = 0.0
        reasons = []

        self._pending_signal["rsi_value"] = rsi

        # RSI zone check
        if signal == "BUY":
            if rsi < config.RSI_OVERSOLD:
                score += 1.0
                reasons.append(f"RSI oversold ({rsi:.1f}) - reversal zone")
            elif rsi < 45:
                score += 0.5
                reasons.append(f"RSI favorable ({rsi:.1f})")
            elif rsi > config.RSI_OVERBOUGHT:
                self._pending_signal["filters_failed"].append("rsi_overbought_buy")
                return False, f"BUY rejected: RSI overbought ({rsi:.1f})", 0
            else:
                score += 0.3
                reasons.append(f"RSI neutral ({rsi:.1f})")
        else:  # SELL
            if rsi > config.RSI_OVERBOUGHT:
                score += 1.0
                reasons.append(f"RSI overbought ({rsi:.1f}) - reversal zone")
            elif rsi > 55:
                score += 0.5
                reasons.append(f"RSI favorable ({rsi:.1f})")
            elif rsi < config.RSI_OVERSOLD:
                self._pending_signal["filters_failed"].append("rsi_oversold_sell")
                return False, f"SELL rejected: RSI oversold ({rsi:.1f})", 0
            else:
                score += 0.3
                reasons.append(f"RSI neutral ({rsi:.1f})")

        # RSI Divergence bonus (from Pine Script)
        if self._pending_signal.get("rsi_divergence", False):
            score += 1.5
            reasons.append("RSI Divergence detected!")

        self._pending_signal["filters_passed"].append("rsi")
        reason_str = " | ".join(reasons)
        logger.info(f"Stage 6: {reason_str} (score: +{score:.1f})")
        return True, reason_str, score

    # ----------------------------------------------------------
    # Stage 7: MACD Confirmation
    # ----------------------------------------------------------

    def check_macd(self) -> Tuple[bool, str, float]:
        """
        Stage 7: MACD histogram momentum confirmation.
        """
        if not self._pending_signal:
            return False, "No pending signal", 0

        if not config.MACD_FILTER_ENABLED:
            self._pending_signal["filters_passed"].append("macd_bypassed")
            return True, "MACD filter disabled", 0

        indicator = self.wh.get_indicator_data()
        if not indicator or "macd_hist" not in indicator:
            self._pending_signal["filters_passed"].append("macd_no_data")
            return True, "No MACD data (allowed)", 0

        macd_hist = indicator["macd_hist"]
        signal = self._pending_signal["signal"]
        score = 0.0

        self._pending_signal["macd_value"] = macd_hist

        if signal == "BUY" and macd_hist > 0:
            score += 1.0
            reason = f"MACD bullish momentum ({macd_hist:.2f})"
        elif signal == "SELL" and macd_hist < 0:
            score += 1.0
            reason = f"MACD bearish momentum ({macd_hist:.2f})"
        elif signal == "BUY" and macd_hist < 0:
            score += 0.3
            reason = f"MACD turning ({macd_hist:.2f}) - early entry"
        else:
            score += 0.3
            reason = f"MACD turning ({macd_hist:.2f}) - early entry"

        self._pending_signal["filters_passed"].append("macd")
        logger.info(f"Stage 7: {reason} (score: +{score:.1f})")
        return True, reason, score

    # ----------------------------------------------------------
    # Stage 8: Wick Filter
    # ----------------------------------------------------------

    def check_wick_filter(self) -> Tuple[bool, str]:
        """
        Stage 8: Reject weak impulse candles with excessive wicks.
        """
        if not self._pending_signal:
            return False, "No pending signal"

        if not config.WICK_FILTER_ENABLED:
            self._pending_signal["filters_passed"].append("wick_bypassed")
            return True, "Wick filter disabled"

        indicator = self.wh.get_indicator_data()
        if not indicator or indicator.get("high", 0) == 0:
            self._pending_signal["filters_passed"].append("wick_no_data")
            return True, "No candle data (allowed)"

        o = indicator["open"]
        h = indicator["high"]
        l = indicator["low"]
        c = indicator["close"]
        body = abs(c - o)

        if body < 0.01:
            self._pending_signal["filters_failed"].append("wick_doji")
            return False, "Doji candle (body too small)"

        total_range = h - l
        if total_range < 0.01:
            self._pending_signal["filters_passed"].append("wick_tiny_range")
            return True, "Range too small (allowed)"

        body_ratio = body / total_range

        if body_ratio < config.WICK_BODY_RATIO_MAX:
            self._pending_signal["filters_failed"].append("wick_too_long")
            return False, f"Weak candle body (body ratio: {body_ratio:.2f})"

        self._pending_signal["filters_passed"].append("wick")
        logger.info(f"Stage 8 PASS: Body ratio {body_ratio:.2f}")
        return True, f"Strong candle (body ratio: {body_ratio:.2f})"

    # ----------------------------------------------------------
    # Stage 9: Bollinger Bands Squeeze + Volume Filter
    # ----------------------------------------------------------

    def check_bb_volume(self) -> Tuple[bool, str, float]:
        """
        Stage 9: Bollinger Bands Squeeze and Volume filter (bonus scores).
        Data comes from the FREE Pine Script.
        Always passes, but adds bonus score.
        """
        if not self._pending_signal:
            return True, "No pending signal", 0

        score = 0.0
        reasons = []

        # BB Squeeze bonus
        if self._pending_signal.get("bb_squeeze", False):
            score += 1.0
            reasons.append("BB Squeeze detected (breakout imminent)")

        # Volume bonus
        if self._pending_signal.get("vol_high", False):
            score += 0.5
            reasons.append("Volume above average (strong move)")

        if reasons:
            self._pending_signal["filters_passed"].append("bb_volume")
            reason_str = " | ".join(reasons)
            logger.info(f"Stage 9: {reason_str} (score: +{score:.1f})")
        else:
            reason_str = "No BB/Volume bonus"

        return True, reason_str, score

    # ----------------------------------------------------------
    # Stage 10: Kill Zone Check (Bonus)
    # ----------------------------------------------------------

    def check_kill_zone(self) -> Tuple[bool, str, float]:
        """
        Check if current time is within a kill zone (high liquidity).
        Always passes, but adds bonus score if in kill zone.
        """
        if not config.KILL_ZONES_ENABLED:
            return True, "Kill zones disabled", 0

        score = 0.0
        reasons = []

        # Check server-side kill zone
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour

        for start, end in config.KILL_ZONES:
            if start <= hour < end:
                score += 0.5
                utc3_start = start + config.UTC_OFFSET
                utc3_end = end + config.UTC_OFFSET
                reasons.append(f"Kill Zone active ({utc3_start}:00-{utc3_end}:00 UTC+3)")
                break

        # Also check Pine Script kill zone flag
        if self._pending_signal and self._pending_signal.get("kill_zone_from_tv", False):
            if score == 0:
                score += 0.5
                reasons.append("Kill Zone confirmed by TradingView")

        if reasons:
            self._pending_signal["filters_passed"].append("kill_zone")
            reason_str = " | ".join(reasons)
            logger.info(f"Stage 10: {reason_str}")
        else:
            reason_str = "Outside kill zone (no bonus)"

        return True, reason_str, score

    # ----------------------------------------------------------
    # Stage 12: Calculate SL/TP Levels
    # ----------------------------------------------------------

    def calculate_levels(self) -> Tuple[bool, str]:
        """
        Calculate entry, SL, TP1, TP2, TP3 using ATR.
        """
        if not self._pending_signal:
            return False, "No pending signal"

        signal = self._pending_signal["signal"]
        price = self._pending_signal["price_at_detection"]

        # Get ATR value
        atr = self._pending_signal.get("atr_from_webhook", 0)
        indicator = self.wh.get_indicator_data()
        if indicator and indicator.get("atr", 0) > 0:
            atr = indicator["atr"]

        if atr <= 0:
            atr = 12.0
            logger.warning(f"No ATR data, using default: {atr}")

        self._pending_signal["atr_value"] = atr

        # Calculate SL
        sl_distance = round(atr * config.ATR_SL_MULTIPLIER, 2)
        sl_distance = max(config.MIN_SL_POINTS, min(config.MAX_SL_POINTS, sl_distance))

        # Calculate TP levels
        tp1_distance = round(atr * config.ATR_TP1_MULTIPLIER, 2)
        tp2_distance = round(atr * config.ATR_TP2_MULTIPLIER, 2)
        tp3_distance = round(atr * config.ATR_TP3_MULTIPLIER, 2)

        tp1_distance = max(config.MIN_TP_POINTS, tp1_distance)
        tp2_distance = max(config.MIN_TP_POINTS * 2, tp2_distance)
        tp3_distance = max(config.MIN_TP_POINTS * 3, tp3_distance)

        if signal == "BUY":
            sl = round(price - sl_distance, 2)
            tp1 = round(price + tp1_distance, 2)
            tp2 = round(price + tp2_distance, 2)
            tp3 = round(price + tp3_distance, 2)
        else:  # SELL
            sl = round(price + sl_distance, 2)
            tp1 = round(price - tp1_distance, 2)
            tp2 = round(price - tp2_distance, 2)
            tp3 = round(price - tp3_distance, 2)

        self._pending_signal["entry_price"] = price
        self._pending_signal["stop_loss"] = sl
        self._pending_signal["current_sl"] = sl
        self._pending_signal["tp1"] = tp1
        self._pending_signal["tp2"] = tp2
        self._pending_signal["tp3"] = tp3

        # Calculate risk-reward ratio
        risk = abs(price - sl)
        reward = abs(tp3 - price)
        rr = round(reward / risk, 2) if risk > 0 else 0
        self._pending_signal["risk_reward_ratio"] = rr

        # Calculate suggested lot size
        lot_size = self._calculate_lot_size(sl_distance)
        self._pending_signal["suggested_lot_size"] = lot_size

        logger.info(f"Levels: Entry={price:.2f} SL={sl:.2f} "
                     f"TP1={tp1:.2f} TP2={tp2:.2f} TP3={tp3:.2f} "
                     f"ATR={atr:.2f} RR=1:{rr:.1f} Lot={lot_size}")

        return True, f"Levels calculated (ATR: {atr:.2f}, RR: 1:{rr:.1f})"

    # ----------------------------------------------------------
    # Run Full Pipeline
    # ----------------------------------------------------------

    def run_pipeline(self) -> Tuple[bool, Optional[dict], str]:
        """
        Run the complete filtering pipeline on the pending signal.
        Returns: (accepted, trade_data, summary)
        """
        if not self._pending_signal:
            return False, None, "No pending signal"

        total_score = 0.0
        details = {}
        all_reasons = []

        # Stage 3: SMC Filter
        passed, reason, score = self.check_smc_filter()
        if not passed:
            return False, None, f"Rejected at SMC: {reason}"
        total_score += score
        details["smc"] = score
        if reason:
            all_reasons.append(reason)

        # Stage 4: Supertrend
        passed, reason, score = self.check_supertrend()
        if not passed:
            return False, None, f"Rejected at Supertrend: {reason}"
        total_score += score
        details["supertrend"] = score
        if reason:
            all_reasons.append(reason)

        # Stage 5: EMA Trend
        passed, reason, score = self.check_ema_trend()
        total_score += score
        details["ema_trend"] = score
        if reason:
            all_reasons.append(reason)

        # Stage 6: RSI
        passed, reason, score = self.check_rsi()
        if not passed:
            return False, None, f"Rejected at RSI: {reason}"
        total_score += score
        details["rsi"] = score
        if reason:
            all_reasons.append(reason)

        # Stage 7: MACD
        passed, reason, score = self.check_macd()
        total_score += score
        details["macd"] = score
        if reason:
            all_reasons.append(reason)

        # Stage 8: Wick Filter
        passed, reason = self.check_wick_filter()
        if not passed:
            return False, None, f"Rejected at Wick: {reason}"

        # Stage 9: BB Squeeze + Volume (bonus)
        passed, reason, score = self.check_bb_volume()
        total_score += score
        details["bb_volume"] = score
        if score > 0:
            all_reasons.append(reason)

        # Stage 10: Kill Zone (bonus)
        passed, reason, score = self.check_kill_zone()
        total_score += score
        details["kill_zone"] = score
        if score > 0:
            all_reasons.append(reason)

        # Add base score for valid signal from Pine Script
        base_score = config.CONFIDENCE_WEIGHTS.get("signal_base", 2.0)
        total_score += base_score
        details["signal_base"] = base_score

        # Add TradingView confidence bonus (if Pine Script sends it)
        tv_conf = self._pending_signal.get("confidence_from_tv", 0)
        if tv_conf > 0:
            # Normalize TV confidence to 0-1 range and add as bonus
            tv_bonus = min(tv_conf / 10.0, 1.0)
            total_score += tv_bonus
            details["tv_confidence"] = tv_bonus

        # Store confidence
        self._pending_signal["confidence_score"] = round(total_score, 1)
        self._pending_signal["confidence_details"] = details
        self._pending_signal["reasons"] = " | ".join(all_reasons)

        # Check minimum confidence
        if total_score < config.MIN_CONFIDENCE_SCORE:
            self._pending_signal["state"] = self.STATE_REJECTED
            summary = (f"Score too low: {total_score:.1f}/{config.MIN_CONFIDENCE_SCORE} "
                       f"({' | '.join(all_reasons)})")
            logger.info(f"Pipeline REJECTED: {summary}")
            return False, None, summary

        # Calculate levels
        self.calculate_levels()

        # ACCEPTED
        self._pending_signal["state"] = self.STATE_READY
        self._pending_signal["entry_time"] = datetime.now(UTC3).isoformat()

        summary = (f"ACCEPTED ✅ Score: {total_score:.1f}/10 | "
                   f"{' | '.join(all_reasons)}")
        logger.info(f"Pipeline {summary}")

        return True, self._pending_signal, summary

    # ----------------------------------------------------------
    # Trade Management
    # ----------------------------------------------------------

    def activate_trade(self) -> Optional[dict]:
        """Move pending signal to active trade."""
        if not self._pending_signal or self._pending_signal["state"] != self.STATE_READY:
            return None

        self._pending_signal["state"] = self.STATE_ACTIVE
        self._active_trade = self._pending_signal
        self._pending_signal = None
        return self._active_trade

    def check_price_targets(self, current_price: float) -> List[dict]:
        """
        Check if current price has hit any targets (TP1, TP2, TP3, SL).
        Returns list of triggered events.
        """
        if not self._active_trade or self._active_trade["state"] in (
            self.STATE_CLOSED, self.STATE_REJECTED
        ):
            return []

        events = []
        trade = self._active_trade
        signal = trade["signal"]
        current_sl = trade["current_sl"]

        # Check Stop Loss
        if signal == "BUY" and current_price <= current_sl:
            events.append(self._on_sl_hit(current_price))
        elif signal == "SELL" and current_price >= current_sl:
            events.append(self._on_sl_hit(current_price))

        # Check TP1
        if trade["state"] == self.STATE_ACTIVE:
            if signal == "BUY" and current_price >= trade["tp1"]:
                events.append(self._on_tp1_hit(current_price))
            elif signal == "SELL" and current_price <= trade["tp1"]:
                events.append(self._on_tp1_hit(current_price))

        # Check TP2
        if trade["state"] == self.STATE_TP1_HIT:
            if signal == "BUY" and current_price >= trade["tp2"]:
                events.append(self._on_tp2_hit(current_price))
            elif signal == "SELL" and current_price <= trade["tp2"]:
                events.append(self._on_tp2_hit(current_price))

        # Check TP3
        if trade["state"] == self.STATE_TP2_HIT:
            if signal == "BUY" and current_price >= trade["tp3"]:
                events.append(self._on_tp3_hit(current_price))
            elif signal == "SELL" and current_price <= trade["tp3"]:
                events.append(self._on_tp3_hit(current_price))

        return events

    def _on_tp1_hit(self, price: float) -> dict:
        """Handle TP1 hit."""
        trade = self._active_trade
        trade["state"] = self.STATE_TP1_HIT
        trade["tp1_hit_time"] = datetime.now(UTC3).isoformat()

        if config.MOVE_SL_TO_BREAKEVEN_ON_TP1:
            entry = trade["entry_price"]
            if trade["signal"] == "BUY":
                new_sl = round(entry + config.BREAKEVEN_OFFSET, 2)
            else:
                new_sl = round(entry - config.BREAKEVEN_OFFSET, 2)
            trade["current_sl"] = new_sl
            logger.info(f"TP1 HIT: SL moved to breakeven {new_sl:.2f}")

        pnl = abs(trade["tp1"] - trade["entry_price"])
        logger.info(f"TP1 HIT @ {price:.2f} (+{pnl:.2f} points)")

        return {
            "event": "TP1_HIT",
            "trade_id": trade["trade_id"],
            "price": price,
            "new_sl": trade["current_sl"],
            "pnl_points": round(pnl, 2),
        }

    def _on_tp2_hit(self, price: float) -> dict:
        """Handle TP2 hit."""
        trade = self._active_trade
        trade["state"] = self.STATE_TP2_HIT
        trade["tp2_hit_time"] = datetime.now(UTC3).isoformat()

        if config.TRAILING_STOP_ENABLED:
            trade["current_sl"] = trade["tp1"]
            logger.info(f"TP2 HIT: SL moved to TP1 level {trade['tp1']:.2f}")

        pnl = abs(trade["tp2"] - trade["entry_price"])
        logger.info(f"TP2 HIT @ {price:.2f} (+{pnl:.2f} points)")

        return {
            "event": "TP2_HIT",
            "trade_id": trade["trade_id"],
            "price": price,
            "new_sl": trade["current_sl"],
            "pnl_points": round(pnl, 2),
        }

    def _on_tp3_hit(self, price: float) -> dict:
        """Handle TP3 hit - trade fully closed."""
        trade = self._active_trade
        trade["state"] = self.STATE_CLOSED
        trade["tp3_hit_time"] = datetime.now(UTC3).isoformat()
        trade["close_price"] = price
        trade["result"] = "TP3_HIT"

        pnl = abs(trade["tp3"] - trade["entry_price"])
        trade["pnl_points"] = round(pnl, 2)
        logger.info(f"TP3 HIT @ {price:.2f} (+{pnl:.2f} points) - TRADE CLOSED")

        return {
            "event": "TP3_HIT",
            "trade_id": trade["trade_id"],
            "price": price,
            "pnl_points": round(pnl, 2),
            "final": True,
        }

    def _on_sl_hit(self, price: float) -> dict:
        """Handle Stop Loss hit."""
        trade = self._active_trade
        trade["close_price"] = price
        trade["close_time"] = datetime.now(UTC3).isoformat()

        entry = trade["entry_price"]
        if trade["signal"] == "BUY":
            pnl = round(price - entry, 2)
        else:
            pnl = round(entry - price, 2)

        trade["pnl_points"] = pnl

        if trade["state"] == self.STATE_TP1_HIT:
            trade["result"] = "TP1_HIT"
        elif trade["state"] == self.STATE_TP2_HIT:
            trade["result"] = "TP2_HIT"
        elif pnl >= -0.5:
            trade["result"] = "BREAKEVEN"
        else:
            trade["result"] = "LOSS"

        trade["state"] = self.STATE_CLOSED
        logger.info(f"SL HIT @ {price:.2f} (PnL: {pnl:+.2f} points) Result: {trade['result']}")

        return {
            "event": "SL_HIT",
            "trade_id": trade["trade_id"],
            "price": price,
            "pnl_points": pnl,
            "result": trade["result"],
            "final": True,
        }

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def get_active_trade(self) -> Optional[dict]:
        return self._active_trade

    def get_pending_signal(self) -> Optional[dict]:
        return self._pending_signal

    def has_active_trade(self) -> bool:
        if self._active_trade and self._active_trade["state"] not in (
            self.STATE_CLOSED, self.STATE_REJECTED
        ):
            return True
        return False

    def force_close(self, price: float, reason: str = "Manual close") -> Optional[dict]:
        """Force close the active trade."""
        if not self._active_trade:
            return None
        trade = self._active_trade
        trade["close_price"] = price
        trade["close_time"] = datetime.now(UTC3).isoformat()
        trade["state"] = self.STATE_CLOSED
        trade["result"] = "MANUAL_CLOSE"

        entry = trade["entry_price"]
        if trade["signal"] == "BUY":
            pnl = round(price - entry, 2)
        else:
            pnl = round(entry - price, 2)
        trade["pnl_points"] = pnl

        logger.info(f"Trade force closed: {reason} (PnL: {pnl:+.2f})")
        return trade

    def reset(self):
        """Reset pipeline state."""
        self._pending_signal = None
        if self._active_trade and self._active_trade["state"] in (
            self.STATE_CLOSED, self.STATE_REJECTED
        ):
            self._active_trade = None

    @staticmethod
    def _calculate_lot_size(sl_points: float) -> float:
        """Calculate suggested lot size based on risk management."""
        if sl_points <= 0:
            return 0.01
        risk_amount = config.DEFAULT_ACCOUNT_BALANCE * (config.RISK_PERCENTAGE / 100)
        lot_size = risk_amount / (sl_points * 100)
        lot_size = max(0.01, min(1.0, round(lot_size, 2)))
        return lot_size
