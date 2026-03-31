"""
GOLD SNIPER V2.0 - Price Monitor
===================================
Real-time gold price monitoring for trade management.
Checks TP1/TP2/TP3/SL targets and sends Telegram alerts.

Sources:
  - yfinance (Yahoo Finance) for live gold prices
  - Webhook-based price updates from TradingView
"""

import logging
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable

import config

logger = logging.getLogger(__name__)

UTC3 = timezone(timedelta(hours=config.UTC_OFFSET))


class PriceMonitor:
    """
    Monitors gold price in real-time and checks trade targets.
    """

    def __init__(self):
        self._current_price: float = 0.0
        self._last_update: float = 0
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list = []
        self._price_source = config.PRICE_SOURCE
        self._yf_ticker = None

    def start(self):
        """Start the price monitoring loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Price monitor started")

    def stop(self):
        """Stop the price monitoring loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Price monitor stopped")

    def update_price_from_webhook(self, price: float):
        """Update price from webhook data."""
        if price > 0:
            self._current_price = price
            self._last_update = time.time()

    def get_current_price(self) -> float:
        """Get the latest gold price."""
        return self._current_price

    def get_last_update_time(self) -> float:
        """Get timestamp of last price update."""
        return self._last_update

    def register_callback(self, callback: Callable):
        """Register a callback for price events."""
        self._callbacks.append(callback)

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                price = self._fetch_price()
                if price and price > 0:
                    self._current_price = price
                    self._last_update = time.time()

                    # Notify callbacks
                    for cb in self._callbacks:
                        try:
                            cb(price)
                        except Exception as e:
                            logger.error(f"Price callback error: {e}")

            except Exception as e:
                logger.error(f"Price monitor error: {e}")

            time.sleep(config.PRICE_CHECK_INTERVAL)

    def _fetch_price(self) -> Optional[float]:
        """Fetch current gold price from configured source."""
        if self._price_source == "yfinance":
            return self._fetch_yfinance()
        elif self._price_source == "webhook":
            # Price comes from webhooks, no active fetching needed
            return self._current_price if self._current_price > 0 else None
        else:
            return self._fetch_yfinance()

    def _fetch_yfinance(self) -> Optional[float]:
        """Fetch gold price from Yahoo Finance."""
        try:
            import yfinance as yf
            if self._yf_ticker is None:
                self._yf_ticker = yf.Ticker(config.YF_SYMBOL)

            data = self._yf_ticker.history(period="1d", interval="1m")
            if data is not None and not data.empty:
                price = float(data['Close'].iloc[-1])
                return round(price, config.PRICE_PRECISION)
            return None
        except Exception as e:
            logger.error(f"yfinance error: {e}")
            # Try alternative method
            return self._fetch_yfinance_fast()

    def _fetch_yfinance_fast(self) -> Optional[float]:
        """Fast alternative price fetch using yfinance download."""
        try:
            import yfinance as yf
            data = yf.download(config.YF_SYMBOL, period="1d", interval="1m", progress=False)
            if data is not None and not data.empty:
                price = float(data['Close'].iloc[-1])
                return round(price, config.PRICE_PRECISION)
            return None
        except Exception as e:
            logger.error(f"yfinance fast error: {e}")
            return None


class TradeMonitor:
    """
    Monitors active trades and triggers events when targets are hit.
    """

    def __init__(self, price_monitor: PriceMonitor, pipeline, telegram_sender):
        self.price_monitor = price_monitor
        self.pipeline = pipeline
        self.telegram = telegram_sender
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start trade monitoring."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Trade monitor started")

    def stop(self):
        """Stop trade monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def _monitor_loop(self):
        """Main trade monitoring loop."""
        from message_formatter import (
            format_tp1_hit, format_tp2_hit, format_tp3_hit, format_sl_hit
        )
        from database import update_trade, update_daily_stats

        while self._running:
            try:
                if not self.pipeline.has_active_trade():
                    time.sleep(config.PRICE_CHECK_INTERVAL)
                    continue

                current_price = self.price_monitor.get_current_price()
                if current_price <= 0:
                    time.sleep(config.PRICE_CHECK_INTERVAL)
                    continue

                # Check targets
                events = self.pipeline.check_price_targets(current_price)

                for event in events:
                    trade = self.pipeline.get_active_trade()
                    if not trade:
                        continue

                    event_type = event.get("event", "")
                    trade_id = event.get("trade_id", "")

                    if event_type == "TP1_HIT":
                        msg = format_tp1_hit(trade, event)
                        self.telegram(msg)
                        update_trade(trade_id, {
                            "tp1_hit_time": trade.get("tp1_hit_time", ""),
                            "current_sl": trade.get("current_sl", 0),
                            "result": "TP1_HIT",
                        })
                        logger.info(f"TP1 HIT notification sent for {trade_id}")

                    elif event_type == "TP2_HIT":
                        msg = format_tp2_hit(trade, event)
                        self.telegram(msg)
                        update_trade(trade_id, {
                            "tp2_hit_time": trade.get("tp2_hit_time", ""),
                            "current_sl": trade.get("current_sl", 0),
                            "result": "TP2_HIT",
                        })
                        logger.info(f"TP2 HIT notification sent for {trade_id}")

                    elif event_type == "TP3_HIT":
                        msg = format_tp3_hit(trade, event)
                        self.telegram(msg)
                        update_trade(trade_id, {
                            "tp3_hit_time": trade.get("tp3_hit_time", ""),
                            "close_price": event.get("price", 0),
                            "pnl_points": event.get("pnl_points", 0),
                            "result": "TP3_HIT",
                            "close_time": datetime.now(UTC3).isoformat(),
                        })
                        update_daily_stats()
                        self.pipeline.reset()
                        logger.info(f"TP3 HIT - Trade {trade_id} fully closed")

                    elif event_type == "SL_HIT":
                        msg = format_sl_hit(trade, event)
                        self.telegram(msg)
                        update_trade(trade_id, {
                            "close_price": event.get("price", 0),
                            "pnl_points": event.get("pnl_points", 0),
                            "result": event.get("result", "LOSS"),
                            "close_time": datetime.now(UTC3).isoformat(),
                        })
                        update_daily_stats()
                        self.pipeline.reset()
                        logger.info(f"SL HIT - Trade {trade_id} closed ({event.get('result')})")

            except Exception as e:
                logger.error(f"Trade monitor error: {e}")

            time.sleep(config.PRICE_CHECK_INTERVAL)
