"""
GOLD SNIPER V2.0 - News Filter
=================================
Fetches high-impact economic news from Forex Factory
and pauses trading before/after major news events.
"""

import logging
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

import config

logger = logging.getLogger(__name__)

UTC3 = timezone(timedelta(hours=config.UTC_OFFSET))


class NewsFilter:
    """
    Monitors economic calendar and pauses trading around
    high-impact news events that affect gold.
    """

    # News events that strongly affect gold
    GOLD_IMPACT_KEYWORDS = [
        "nonfarm", "nfp", "cpi", "ppi", "interest rate", "fed",
        "fomc", "gdp", "unemployment", "retail sales",
        "consumer confidence", "ism manufacturing", "ism services",
        "core cpi", "core pce", "pce", "jackson hole",
        "powell", "ecb", "boe", "gold", "treasury",
        "inflation", "payroll", "employment", "jobless claims",
    ]

    def __init__(self):
        self._news_events: List[dict] = []
        self._last_fetch: float = 0
        self._fetch_interval: int = 3600  # Fetch every hour
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start news monitoring."""
        if not config.NEWS_FILTER_ENABLED:
            logger.info("News filter disabled")
            return
        self._running = True
        self._thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self._thread.start()
        logger.info("News filter started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def is_safe_to_trade(self) -> Tuple[bool, str]:
        """
        Check if it's safe to trade right now.
        Returns (safe, reason).
        """
        if not config.NEWS_FILTER_ENABLED:
            return True, "News filter disabled"

        now = datetime.now(timezone.utc)

        for event in self._news_events:
            event_time = event.get("time")
            if not event_time:
                continue

            # Check if we're within the pause window
            before_window = event_time - timedelta(minutes=config.NEWS_PAUSE_MINUTES_BEFORE)
            after_window = event_time + timedelta(minutes=config.NEWS_PAUSE_MINUTES_AFTER)

            if before_window <= now <= after_window:
                event_name = event.get("title", "Unknown")
                impact = event.get("impact", "")
                minutes_to = int((event_time - now).total_seconds() / 60)

                if minutes_to > 0:
                    reason = f"⚠️ خبر قوي بعد {minutes_to} دقيقة: {event_name} ({impact})"
                else:
                    reason = f"⚠️ خبر قوي صدر منذ {abs(minutes_to)} دقيقة: {event_name} ({impact})"

                return False, reason

        return True, "No high-impact news nearby"

    def get_upcoming_news(self, hours: int = 4) -> List[dict]:
        """Get upcoming high-impact news within specified hours."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours)
        return [
            e for e in self._news_events
            if e.get("time") and now <= e["time"] <= cutoff
        ]

    def _fetch_loop(self):
        """Periodically fetch news data."""
        while self._running:
            try:
                if time.time() - self._last_fetch >= self._fetch_interval:
                    self._fetch_news()
                    self._last_fetch = time.time()
            except Exception as e:
                logger.error(f"News fetch error: {e}")
            time.sleep(60)

    def _fetch_news(self):
        """Fetch today's high-impact news from Forex Factory API."""
        try:
            # Use Forex Factory calendar API
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            url = f"https://nfs.faireconomy.media/ff_calendar_thisweek.json"

            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"News API returned {resp.status_code}")
                return

            data = resp.json()
            events = []

            for item in data:
                impact = item.get("impact", "").lower()
                if impact not in ("high", "medium"):
                    continue

                title = item.get("title", "").lower()
                country = item.get("country", "").upper()

                # Filter for USD-related news (affects gold)
                if country not in ("USD", "ALL"):
                    # Also check for gold-impacting keywords from other countries
                    is_gold_relevant = any(kw in title for kw in self.GOLD_IMPACT_KEYWORDS)
                    if not is_gold_relevant:
                        continue

                # Parse time
                date_str = item.get("date", "")
                try:
                    event_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    if event_time.tzinfo is None:
                        event_time = event_time.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue

                events.append({
                    "title": item.get("title", "Unknown"),
                    "country": country,
                    "impact": impact.upper(),
                    "time": event_time,
                    "forecast": item.get("forecast", ""),
                    "previous": item.get("previous", ""),
                })

            self._news_events = events
            logger.info(f"Fetched {len(events)} high-impact news events")

        except Exception as e:
            logger.error(f"News fetch error: {e}")

    def format_news_list(self) -> str:
        """Format upcoming news for display."""
        upcoming = self.get_upcoming_news(hours=12)
        if not upcoming:
            return "📰 لا توجد أخبار قوية قادمة خلال 12 ساعة"

        lines = ["📰 الأخبار القادمة:"]
        for e in upcoming:
            t = e["time"].astimezone(UTC3).strftime("%H:%M")
            impact_emoji = "🔴" if e["impact"] == "HIGH" else "🟡"
            lines.append(f"{impact_emoji} {t} | {e['country']} | {e['title']}")

        return "\n".join(lines)
