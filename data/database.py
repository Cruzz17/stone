#!/usr/bin/env python3
"""
数据库管理模块
负责股票数据的存储和查询
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
import os


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "data/trading.db"):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path

        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 初始化数据库
        self._init_database()

        logger.info(f"数据库管理器初始化完成: {db_path}")

    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            # 股票基本信息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT,
                    industry TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 股票日线数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    date DATE,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    amount REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            """)

            # 交易信号表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    signal_type TEXT,
                    signal_strength REAL,
                    price REAL,
                    strategy TEXT,
                    reason TEXT,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 交易记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    action TEXT,
                    shares INTEGER,
                    price REAL,
                    amount REAL,
                    commission REAL,
                    strategy TEXT,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 持仓记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE,
                    shares INTEGER,
                    avg_price REAL,
                    current_price REAL,
                    market_value REAL,
                    unrealized_pnl REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 投资组合历史表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_value REAL,
                    cash REAL,
                    positions_value REAL,
                    total_pnl REAL,
                    total_pnl_pct REAL,
                    position_count INTEGER,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_symbol_date ON stock_daily(symbol, date)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON trading_signals(symbol, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp ON trades(symbol, timestamp)")

            conn.commit()

    def save_stock_data(self, symbol: str, data: pd.DataFrame):
        """
        保存股票数据

        Args:
            symbol: 股票代码
            data: 股票数据DataFrame
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 准备数据
                data_to_save = data.copy()
                data_to_save['symbol'] = symbol
                
                # 确保索引是日期格式
                if hasattr(data_to_save.index, 'strftime'):
                    # 如果索引是DatetimeIndex，直接使用strftime
                    data_to_save['date'] = data_to_save.index.strftime('%Y-%m-%d')
                elif 'date' in data_to_save.columns:
                    # 如果有date列，使用该列
                    data_to_save['date'] = pd.to_datetime(data_to_save['date']).dt.strftime('%Y-%m-%d')
                else:
                    # 如果索引不是日期格式，尝试转换
                    try:
                        data_to_save['date'] = pd.to_datetime(data_to_save.index).strftime('%Y-%m-%d')
                    except:
                        # 如果转换失败，使用当前日期
                        logger.warning(f"无法解析 {symbol} 的日期索引，使用当前日期")
                        data_to_save['date'] = datetime.now().strftime('%Y-%m-%d')

                # 选择需要的列
                columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
                if 'amount' in data_to_save.columns:
                    columns.append('amount')
                else:
                    data_to_save['amount'] = data_to_save['volume'] * data_to_save['close']
                    columns.append('amount')

                # 保存数据（使用REPLACE避免重复）
                for _, row in data_to_save[columns].iterrows():
                    conn.execute("""
                        REPLACE INTO stock_daily 
                        (symbol, date, open, high, low, close, volume, amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(row))

                conn.commit()
                logger.info(f"保存 {symbol} 数据 {len(data_to_save)} 条")

        except Exception as e:
            logger.error(f"保存股票数据失败 {symbol}: {e}")

    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None,
                       limit: int = None) -> pd.DataFrame:
        """
        获取股票数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制条数

        Returns:
            股票数据DataFrame
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT date, open, high, low, close, volume, amount FROM stock_daily WHERE symbol = ?"
                params = [symbol]

                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)

                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)

                query += " ORDER BY date DESC"

                if limit:
                    query += f" LIMIT {limit}"

                df = pd.read_sql_query(query, conn, params=params)

                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    df.sort_index(inplace=True)

                return df

        except Exception as e:
            logger.error(f"获取股票数据失败 {symbol}: {e}")
            return pd.DataFrame()

    def save_signal(self, symbol: str, signal_type: str, strength: float, price: float,
                    strategy: str, reason: str, timestamp: datetime = None):
        """保存交易信号"""
        if timestamp is None:
            timestamp = datetime.now()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO trading_signals 
                    (symbol, signal_type, signal_strength, price, strategy, reason, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (symbol, signal_type, strength, price, strategy, reason, timestamp))
                conn.commit()

        except Exception as e:
            logger.error(f"保存交易信号失败: {e}")

    def save_trade(self, symbol: str, action: str, shares: int, price: float,
                   amount: float, commission: float, strategy: str, timestamp: datetime = None):
        """保存交易记录"""
        if timestamp is None:
            timestamp = datetime.now()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO trades 
                    (symbol, action, shares, price, amount, commission, strategy, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (symbol, action, shares, price, amount, commission, strategy, timestamp))
                conn.commit()

        except Exception as e:
            logger.error(f"保存交易记录失败: {e}")

    def update_position(self, symbol: str, shares: int, avg_price: float, current_price: float):
        """更新持仓记录"""
        try:
            market_value = shares * current_price
            unrealized_pnl = (current_price - avg_price) * shares

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    REPLACE INTO positions 
                    (symbol, shares, avg_price, current_price, market_value, unrealized_pnl, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (symbol, shares, avg_price, current_price, market_value, unrealized_pnl, datetime.now()))
                conn.commit()

        except Exception as e:
            logger.error(f"更新持仓记录失败: {e}")

    def delete_position(self, symbol: str):
        """删除持仓记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
                conn.commit()

        except Exception as e:
            logger.error(f"删除持仓记录失败: {e}")

    def get_positions(self) -> pd.DataFrame:
        """获取当前持仓"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("""
                    SELECT symbol, shares, avg_price, current_price, market_value, unrealized_pnl, updated_at
                    FROM positions WHERE shares > 0
                """, conn)
                return df

        except Exception as e:
            logger.error(f"获取持仓记录失败: {e}")
            return pd.DataFrame()

    def save_portfolio_snapshot(self, total_value: float, cash: float, positions_value: float,
                                total_pnl: float, total_pnl_pct: float, position_count: int):
        """保存投资组合快照"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO portfolio_history 
                    (total_value, cash, positions_value, total_pnl, total_pnl_pct, position_count, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (total_value, cash, positions_value, total_pnl, total_pnl_pct, position_count, datetime.now()))
                conn.commit()

        except Exception as e:
            logger.error(f"保存投资组合快照失败: {e}")

    def get_portfolio_history(self, days: int = 30) -> pd.DataFrame:
        """获取投资组合历史"""
        try:
            start_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("""
                    SELECT * FROM portfolio_history 
                    WHERE timestamp >= ? 
                    ORDER BY timestamp
                """, conn, params=[start_date])

                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])

                return df

        except Exception as e:
            logger.error(f"获取投资组合历史失败: {e}")
            return pd.DataFrame()

    def get_recent_signals(self, limit: int = 50) -> pd.DataFrame:
        """获取最近的交易信号"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("""
                    SELECT * FROM trading_signals 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, conn, params=[limit])

                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])

                return df

        except Exception as e:
            logger.error(f"获取交易信号失败: {e}")
            return pd.DataFrame()

    def get_recent_trades(self, limit: int = 50) -> pd.DataFrame:
        """获取最近的交易记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("""
                    SELECT * FROM trades 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, conn, params=[limit])

                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])

                return df

        except Exception as e:
            logger.error(f"获取交易记录失败: {e}")
            return pd.DataFrame()