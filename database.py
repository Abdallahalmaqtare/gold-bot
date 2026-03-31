"""
GOLD SNIPER V2.0 - Database Module
====================================
SQLite database for trade history, statistics, and analytics.
Supports full trade lifecycle: PENDING → TP1_HIT → TP2_HIT → TP3_HIT → CLOSED
"""

import sqlite3
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

import config

logger = logging.getLogger(__name__)

UTC3 = timezone(timedelta(hours=config.UTC_OFFSET))


def _get_conn():
    """Get database connection."""
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize database tables."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL DEFAULT 'XAUUSD',
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                tp1 REAL NOT NULL,
                tp2 REAL NOT NULL,
                tp3 REAL NOT NULL,
                current_sl REAL,
                atr_value REAL,
                confidence_score REAL DEFAULT 0,
                reasons TEXT,
                
                -- Timestamps
                signal_time TEXT,
                entry_time TEXT,
                tp1_hit_time TEXT,
                tp2_hit_time TEXT,
                tp3_hit_time TEXT,
                close_time TEXT,
                
                -- Results
                close_price REAL,
                result TEXT DEFAULT 'PENDING',
                pnl_points REAL DEFAULT 0,
                
                -- Pipeline info
                pipeline_stage TEXT DEFAULT 'DETECTED',
                gainzalgo_signal TEXT,
                smc_confirmed INTEGER DEFAULT 0,
                supertrend_confirmed INTEGER DEFAULT 0,
                ema_confirmed INTEGER DEFAULT 0,
                rsi_value REAL,
                macd_value REAL,
                
                -- Risk Management
                suggested_lot_size REAL,
                risk_reward_ratio REAL,
                
                -- Metadata
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                breakeven INTEGER DEFAULT 0,
                tp1_hits INTEGER DEFAULT 0,
                tp2_hits INTEGER DEFAULT 0,
                tp3_hits INTEGER DEFAULT 0,
                total_pnl_points REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_rr REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                target_price REAL NOT NULL,
                triggered INTEGER DEFAULT 0,
                triggered_at TEXT,
                message_sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE INDEX IF NOT EXISTS idx_trades_result ON trades(result);
            CREATE INDEX IF NOT EXISTS idx_trades_trade_id ON trades(trade_id);
            CREATE INDEX IF NOT EXISTS idx_alerts_trade_id ON price_alerts(trade_id);
            CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON price_alerts(triggered);
        """)
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database init error: {e}")
    finally:
        conn.close()


def save_trade(trade: dict) -> bool:
    """Save a new trade to the database."""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO trades (
                trade_id, symbol, direction, entry_price, stop_loss,
                tp1, tp2, tp3, current_sl, atr_value, confidence_score,
                reasons, signal_time, entry_time, pipeline_stage,
                gainzalgo_signal, smc_confirmed, supertrend_confirmed,
                ema_confirmed, rsi_value, macd_value,
                suggested_lot_size, risk_reward_ratio
            ) VALUES (
                :trade_id, :symbol, :direction, :entry_price, :stop_loss,
                :tp1, :tp2, :tp3, :current_sl, :atr_value, :confidence_score,
                :reasons, :signal_time, :entry_time, :pipeline_stage,
                :gainzalgo_signal, :smc_confirmed, :supertrend_confirmed,
                :ema_confirmed, :rsi_value, :macd_value,
                :suggested_lot_size, :risk_reward_ratio
            )
        """, trade)
        conn.commit()
        logger.info(f"Trade saved: {trade['trade_id']}")
        return True
    except Exception as e:
        logger.error(f"Save trade error: {e}")
        return False
    finally:
        conn.close()


def update_trade(trade_id: str, updates: dict) -> bool:
    """Update an existing trade."""
    conn = _get_conn()
    try:
        set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
        updates["trade_id"] = trade_id
        updates["updated_at"] = datetime.now(UTC3).isoformat()
        conn.execute(
            f"UPDATE trades SET {set_clause}, updated_at = :updated_at WHERE trade_id = :trade_id",
            updates
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Update trade error: {e}")
        return False
    finally:
        conn.close()


def get_active_trades() -> List[dict]:
    """Get all active (non-closed) trades."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM trades WHERE result = 'PENDING' OR result LIKE 'TP%_HIT' ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_trade(trade_id: str) -> Optional[dict]:
    """Get a specific trade by ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_pending_alerts() -> List[dict]:
    """Get all untriggered price alerts."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM price_alerts WHERE triggered = 0 ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_price_alert(alert: dict) -> bool:
    """Save a price alert for monitoring."""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO price_alerts (trade_id, alert_type, target_price)
            VALUES (:trade_id, :alert_type, :target_price)
        """, alert)
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Save alert error: {e}")
        return False
    finally:
        conn.close()


def trigger_alert(alert_id: int) -> bool:
    """Mark an alert as triggered."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE price_alerts SET triggered = 1, triggered_at = ?, message_sent = 1 WHERE id = ?",
            (datetime.now(UTC3).isoformat(), alert_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Trigger alert error: {e}")
        return False
    finally:
        conn.close()


def get_daily_stats(date_str: str = None) -> dict:
    """Get statistics for a specific date or today."""
    if not date_str:
        date_str = datetime.now(UTC3).strftime("%Y-%m-%d")
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM daily_stats WHERE date = ?", (date_str,)).fetchone()
        if row:
            return dict(row)
        return {
            "date": date_str, "total_trades": 0, "wins": 0, "losses": 0,
            "breakeven": 0, "tp1_hits": 0, "tp2_hits": 0, "tp3_hits": 0,
            "total_pnl_points": 0, "win_rate": 0, "avg_rr": 0
        }
    finally:
        conn.close()


def update_daily_stats(date_str: str = None):
    """Recalculate and update daily statistics."""
    if not date_str:
        date_str = datetime.now(UTC3).strftime("%Y-%m-%d")
    conn = _get_conn()
    try:
        trades = conn.execute(
            "SELECT * FROM trades WHERE date(entry_time) = ? AND result != 'PENDING'",
            (date_str,)
        ).fetchall()

        total = len(trades)
        wins = sum(1 for t in trades if t["result"] in ("WIN", "TP1_HIT", "TP2_HIT", "TP3_HIT"))
        losses = sum(1 for t in trades if t["result"] == "LOSS")
        breakeven = sum(1 for t in trades if t["result"] == "BREAKEVEN")
        tp1_hits = sum(1 for t in trades if t["tp1_hit_time"] is not None)
        tp2_hits = sum(1 for t in trades if t["tp2_hit_time"] is not None)
        tp3_hits = sum(1 for t in trades if t["tp3_hit_time"] is not None)
        total_pnl = sum(t["pnl_points"] or 0 for t in trades)
        win_rate = round((wins / total * 100), 1) if total > 0 else 0

        conn.execute("""
            INSERT INTO daily_stats (date, total_trades, wins, losses, breakeven,
                tp1_hits, tp2_hits, tp3_hits, total_pnl_points, win_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_trades=?, wins=?, losses=?, breakeven=?,
                tp1_hits=?, tp2_hits=?, tp3_hits=?, total_pnl_points=?, win_rate=?
        """, (date_str, total, wins, losses, breakeven, tp1_hits, tp2_hits, tp3_hits, total_pnl, win_rate,
              total, wins, losses, breakeven, tp1_hits, tp2_hits, tp3_hits, total_pnl, win_rate))
        conn.commit()
    except Exception as e:
        logger.error(f"Update daily stats error: {e}")
    finally:
        conn.close()


def get_overall_stats() -> dict:
    """Get overall cumulative statistics."""
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN result IN ('WIN','TP1_HIT','TP2_HIT','TP3_HIT') THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN result = 'BREAKEVEN' THEN 1 ELSE 0 END) as breakeven,
                SUM(CASE WHEN tp1_hit_time IS NOT NULL THEN 1 ELSE 0 END) as tp1_hits,
                SUM(CASE WHEN tp2_hit_time IS NOT NULL THEN 1 ELSE 0 END) as tp2_hits,
                SUM(CASE WHEN tp3_hit_time IS NOT NULL THEN 1 ELSE 0 END) as tp3_hits,
                COALESCE(SUM(pnl_points), 0) as total_pnl,
                COALESCE(AVG(risk_reward_ratio), 0) as avg_rr
            FROM trades WHERE result != 'PENDING'
        """).fetchone()

        total = row["total"] or 0
        wins = row["wins"] or 0
        win_rate = round((wins / total * 100), 1) if total > 0 else 0

        return {
            "total": total,
            "wins": wins,
            "losses": row["losses"] or 0,
            "breakeven": row["breakeven"] or 0,
            "tp1_hits": row["tp1_hits"] or 0,
            "tp2_hits": row["tp2_hits"] or 0,
            "tp3_hits": row["tp3_hits"] or 0,
            "total_pnl": round(row["total_pnl"] or 0, 2),
            "avg_rr": round(row["avg_rr"] or 0, 2),
            "win_rate": win_rate,
        }
    finally:
        conn.close()


def get_recent_trades(limit: int = 10) -> List[dict]:
    """Get most recent trades."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def cleanup_old_data(days: int = 30):
    """Remove data older than specified days."""
    conn = _get_conn()
    try:
        cutoff = (datetime.now(UTC3) - timedelta(days=days)).isoformat()
        conn.execute("DELETE FROM trades WHERE created_at < ? AND result != 'PENDING'", (cutoff,))
        conn.execute("DELETE FROM price_alerts WHERE created_at < ? AND triggered = 1", (cutoff,))
        conn.commit()
        logger.info(f"Cleaned up data older than {days} days")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
    finally:
        conn.close()
