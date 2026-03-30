"""
GOLD SNIPER V2.0 - Keep Alive
================================
Prevents Render.com free tier from sleeping.
Pings the service URL every 5 minutes.
"""

import logging
import threading
import time
import requests

import config

logger = logging.getLogger(__name__)


class KeepAlive:
    """Periodically pings the service URL to prevent sleeping."""

    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        if not config.KEEP_ALIVE_ENABLED:
            logger.info("Keep-alive disabled")
            return
        if not config.KEEP_ALIVE_URL:
            logger.warning("Keep-alive URL not set, skipping")
            return
        self._running = True
        self._thread = threading.Thread(target=self._ping_loop, daemon=True)
        self._thread.start()
        logger.info(f"Keep-alive started: pinging {config.KEEP_ALIVE_URL} "
                     f"every {config.KEEP_ALIVE_INTERVAL}s")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _ping_loop(self):
        while self._running:
            try:
                resp = requests.get(
                    config.KEEP_ALIVE_URL + "/health",
                    timeout=10
                )
                logger.debug(f"Keep-alive ping: {resp.status_code}")
            except Exception as e:
                logger.warning(f"Keep-alive ping failed: {e}")
            time.sleep(config.KEEP_ALIVE_INTERVAL)
