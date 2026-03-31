"""
GOLD SNIPER V2.0 [FREE] - Webhook Handler
=============================================
Receives and processes signals from the FREE Pine Script.
All indicator data comes in a single webhook (no paid indicators).
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import config

logger = logging.getLogger(__name__)

UTC3 = timezone(timedelta(hours=config.UTC_OFFSET))


class WebhookHandler:
    """
    Manages incoming webhook data from TradingView Pine Script.
    Single webhook endpoint - all data comes from the FREE script.
    """

    def __init__(self):
        # Latest signal data (all-in-one from Pine Script)
        self._signal_data: Optional[Dict[str, Any]] = None

        # Parsed sub-components for pipeline queries
        self._smc_state: Optional[Dict[str, Any]] = None
        self._supertrend_state: Optional[Dict[str, Any]] = None
        self._indicator_data: Optional[Dict[str, Any]] = None

        # Anti-flicker
        self._last_signal_time: float = 0
        self._last_signal_direction: str = ""

    # ----------------------------------------------------------
    # Main Webhook Processor
    # ----------------------------------------------------------

    def process_webhook(self, data: dict) -> Optional[dict]:
        """
        Process the webhook from the FREE Pine Script.
        This is the ONLY webhook endpoint needed.
        All indicator + SMC data comes in one payload.
        """
        # Validate secret
        if data.get("secret") != config.WEBHOOK_SECRET:
            logger.warning("Webhook: invalid secret")
            return None

        # Validate symbol
        symbol = self._normalize_symbol(data.get("symbol", ""))
        if symbol != config.SYMBOL:
            logger.warning(f"Webhook: symbol {symbol} is not {config.SYMBOL}")
            return None

        # Validate signal type
        signal_type = data.get("signal", "").upper()
        if signal_type == "CALL":
            signal_type = "BUY"
        elif signal_type == "PUT":
            signal_type = "SELL"

        if signal_type not in ("BUY", "SELL"):
            logger.warning(f"Webhook: invalid signal type: {signal_type}")
            return None

        # Validate price
        price = float(data.get("price", 0))
        if price <= 0:
            logger.warning("Webhook: invalid price")
            return None

        # Anti-flicker check
        now = time.time()
        if (now - self._last_signal_time < config.MIN_SIGNAL_INTERVAL_SECONDS
                and self._last_signal_direction == signal_type):
            logger.info(f"Webhook: duplicate {signal_type} signal within cooldown, ignoring")
            return None

        # Parse all indicator data
        indicator_data = {
            "source": "pine_script_free",
            "symbol": symbol,
            "signal": signal_type,
            "price": price,
            "atr": float(data.get("atr", 0)),
            "rsi": float(data.get("rsi", 50)),
            "macd_hist": float(data.get("macd_hist", 0)),
            "ema_fast": float(data.get("ema_fast", 0)),
            "ema_slow": float(data.get("ema_slow", 0)),
            "ema_200": float(data.get("ema_200", 0)),
            "supertrend": data.get("supertrend", "").upper(),
            "supertrend_value": float(data.get("supertrend_value", 0)),
            # SMC data (built into Pine Script)
            "ob_type": data.get("ob_type", "none").lower(),
            "ob_high": float(data.get("ob_high", 0)),
            "ob_low": float(data.get("ob_low", 0)),
            "fvg_type": data.get("fvg_type", "none").lower(),
            "fvg_high": float(data.get("fvg_high", 0)),
            "fvg_low": float(data.get("fvg_low", 0)),
            "bos": data.get("bos", "none").lower(),
            "market_structure": data.get("market_structure", "NONE").upper(),
            # Bonus indicators
            "confidence_from_tv": float(data.get("confidence", 0)),
            "bb_squeeze": _parse_bool(data.get("bb_squeeze", False)),
            "vol_high": _parse_bool(data.get("vol_high", False)),
            "rsi_divergence": _parse_bool(data.get("rsi_divergence", False)),
            "kill_zone": _parse_bool(data.get("kill_zone", False)),
            # Candle data
            "high": float(data.get("high", 0)),
            "low": float(data.get("low", 0)),
            "open": float(data.get("open", 0)),
            "close": float(data.get("close", 0)),
            "volume": float(data.get("volume", 0)),
            # Timestamps
            "received_at": datetime.now(UTC3),
            "received_ts": now,
        }

        # Update sub-component states for pipeline queries
        self._update_sub_states(indicator_data)

        self._signal_data = indicator_data
        self._indicator_data = indicator_data
        self._last_signal_time = now
        self._last_signal_direction = signal_type

        logger.info(
            f"Signal received: {symbol} {signal_type} @ {price:.2f} | "
            f"ATR={indicator_data['atr']:.2f} RSI={indicator_data['rsi']:.1f} "
            f"MACD={indicator_data['macd_hist']:.3f} ST={indicator_data['supertrend']} "
            f"OB={indicator_data['ob_type']} FVG={indicator_data['fvg_type']} "
            f"BOS={indicator_data['bos']} MS={indicator_data['market_structure']} "
            f"Conf={indicator_data['confidence_from_tv']:.1f}"
        )

        return indicator_data

    # ----------------------------------------------------------
    # Legacy compatibility: process_multi_indicator maps to process_webhook
    # ----------------------------------------------------------

    def process_multi_indicator(self, data: dict) -> Optional[dict]:
        """Alias for process_webhook (backward compatibility)."""
        return self.process_webhook(data)

    # ----------------------------------------------------------
    # Sub-state Updates
    # ----------------------------------------------------------

    def _update_sub_states(self, data: dict):
        """Update individual sub-states from the all-in-one webhook data."""
        # Supertrend state
        if data["supertrend"] in ("UP", "DOWN"):
            self._supertrend_state = {
                "symbol": data["symbol"],
                "trend": data["supertrend"],
                "supertrend_value": data["supertrend_value"],
                "price": data["price"],
                "received_at": data["received_at"],
            }

        # SMC state
        self._smc_state = {
            "symbol": data["symbol"],
            "order_block": data["ob_type"],
            "ob_high": data["ob_high"],
            "ob_low": data["ob_low"],
            "fvg": data["fvg_type"],
            "fvg_high": data["fvg_high"],
            "fvg_low": data["fvg_low"],
            "bos": data["bos"],
            "market_structure": data["market_structure"],
            "price": data["price"],
            "received_at": data["received_at"],
        }

    # ----------------------------------------------------------
    # Query Methods (used by Pipeline)
    # ----------------------------------------------------------

    def get_signal_data(self) -> Optional[dict]:
        """Get the latest signal data."""
        return self._signal_data

    def get_smc_state(self) -> Optional[dict]:
        """Get the latest SMC state."""
        return self._smc_state

    def get_supertrend_state(self) -> Optional[dict]:
        """Get the latest Supertrend state."""
        return self._supertrend_state

    def get_indicator_data(self) -> Optional[dict]:
        """Get the latest indicator data."""
        return self._indicator_data

    def clear_signal(self):
        """Clear the current signal after processing."""
        self._signal_data = None
        logger.info("Signal cleared")

    def clear_all(self):
        """Clear all stored data."""
        self._signal_data = None
        self._smc_state = None
        self._supertrend_state = None
        self._indicator_data = None

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    @staticmethod
    def _normalize_symbol(raw: str) -> str:
        """Normalize symbol name."""
        s = raw.upper().replace("/", "").replace("_", "").replace("=X", "").strip()
        if s in ("GOLD", "GC", "GC=F", "XAUUSD", "XAU/USD", "XAUUSD."):
            return "XAUUSD"
        return s


def _parse_bool(val) -> bool:
    """Parse boolean from various formats."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)
