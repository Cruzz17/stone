#!/usr/bin/env python3
"""
真实数据获取器
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import threading
from loguru import logger

try:
    import akshare as ak

    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AKShare未安装，将使用模拟数据")


class RealDataFetcher:
    """真实数据获取器"""

    def __init__(self, db_manager):
        """
        初始化数据获取器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.stock_pool = []
        self.current_prices = {}
        self.is_updating = False
        self.update_thread = None

        logger.info("真实数据获取器初始化完成")

    def set_stock_pool(self, stock_pool: List[str]):
        """设置股票池"""
        self.stock_pool = stock_pool
        logger.info(f"设置股票池: {stock_pool}")

    def refresh_historical_data(self, days: int = 100):
        """刷新历史数据"""
        logger.info(f"开始刷新 {days} 天历史数据...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        for symbol in self.stock_pool:
            try:
                if AKSHARE_AVAILABLE:
                    # 使用AKShare获取真实数据
                    data = self._fetch_real_data(symbol, start_date, end_date)
                else:
                    # 生成模拟数据
                    data = self._generate_mock_data(symbol, start_date, end_date)

                if not data.empty:
                    # 保存到数据库

                    self.db_manager.save_stock_data(symbol, data)
                    logger.info(f"已更新 {symbol} 的 {len(data)} 条历史数据")

            except Exception as e:
                logger.error(f"更新 {symbol} 历史数据失败: {e}")

        logger.info("历史数据刷新完成")

    def _fetch_real_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """获取真实股票数据"""
        try:
            # 转换股票代码格式
            if symbol.startswith('60'):
                ak_symbol = f"{symbol}.SH"
            elif symbol.startswith('00') or symbol.startswith('30'):
                ak_symbol = f"{symbol}.SZ"
            else:
                ak_symbol = symbol

            # 获取股票历史数据
            data = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust=""
            )

            if data.empty:
                return pd.DataFrame()

            # 重命名列
            data = data.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            })

            # 确保数据类型正确
            data['date'] = pd.to_datetime(data['date'])
            for col in ['open', 'high', 'low', 'close']:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            data['volume'] = pd.to_numeric(data['volume'], errors='coerce')

            # 设置日期为索引
            data.set_index('date', inplace=True)

            return data[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            logger.error(f"获取 {symbol} 真实数据失败: {e}")
            return pd.DataFrame()

    def _generate_mock_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """生成模拟数据"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # 只保留工作日

        if not dates:
            return pd.DataFrame()

        # 生成模拟价格数据
        np.random.seed(hash(symbol) % 2 ** 32)
        base_price = 10 + (hash(symbol) % 100)

        prices = []
        current_price = base_price

        for _ in dates:
            # 随机波动
            change = np.random.normal(0, 0.02)
            current_price *= (1 + change)
            current_price = max(current_price, 1.0)  # 确保价格不为负

            # 生成OHLC数据
            high = current_price * (1 + abs(np.random.normal(0, 0.01)))
            low = current_price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = low + (high - low) * np.random.random()
            close_price = current_price
            volume = int(np.random.uniform(1000000, 10000000))

            prices.append({
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

        data = pd.DataFrame(prices)
        data['date'] = dates
        
        # 设置日期为索引
        data.set_index('date', inplace=True)

        return data[['open', 'high', 'low', 'close', 'volume']]

    def start_real_time_update(self, interval: int = 30):
        """启动实时数据更新"""
        if self.is_updating:
            return

        self.is_updating = True
        self.update_thread = threading.Thread(target=self._update_loop, args=(interval,), daemon=True)
        self.update_thread.start()
        logger.info(f"启动实时数据更新，间隔: {interval}秒")

    def stop_real_time_update(self):
        """停止实时数据更新"""
        self.is_updating = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        logger.info("停止实时数据更新")

    def _update_loop(self, interval: int):
        """更新循环"""
        while self.is_updating:
            try:
                self._update_current_prices()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"实时数据更新异常: {e}")
                time.sleep(10)

    def _update_current_prices(self):
        """更新当前价格"""
        for symbol in self.stock_pool:
            try:
                if AKSHARE_AVAILABLE:
                    # 获取实时价格
                    price = self._fetch_current_price(symbol)
                else:
                    # 生成模拟价格
                    price = self._generate_mock_price(symbol)

                if price > 0:
                    self.current_prices[symbol] = price

            except Exception as e:
                logger.error(f"更新 {symbol} 当前价格失败: {e}")

    def _fetch_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            # 获取实时行情
            data = ak.stock_zh_a_spot_em()
            stock_data = data[data['代码'] == symbol]

            if not stock_data.empty:
                return float(stock_data.iloc[0]['最新价'])

            return 0.0

        except Exception as e:
            logger.error(f"获取 {symbol} 实时价格失败: {e}")
            return 0.0

    def _generate_mock_price(self, symbol: str) -> float:
        """生成模拟当前价格"""
        # 基于历史数据生成模拟价格
        historical_data = self.db_manager.get_stock_data(symbol, limit=1)

        if not historical_data.empty:
            last_price = historical_data.iloc[-1]['close']
            # 添加随机波动
            change = np.random.normal(0, 0.005)
            return round(last_price * (1 + change), 2)

        # 如果没有历史数据，返回随机价格
        return round(10 + (hash(symbol) % 50), 2)

    def get_current_prices(self) -> Dict[str, float]:
        """获取当前价格字典"""
        return self.current_prices.copy()

    def get_market_status(self) -> Dict:
        """获取市场状态"""
        now = datetime.now()

        # 简单的交易时间判断（9:30-15:00，周一到周五）
        is_trading_day = now.weekday() < 5
        is_trading_time = (
                is_trading_day and
                ((9 <= now.hour < 11) or (13 <= now.hour < 15) or
                 (now.hour == 11 and now.minute <= 30) or
                 (now.hour == 9 and now.minute >= 30))
        )

        return {
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'is_trading_day': is_trading_day,
            'is_trading_time': is_trading_time,
            'market_status': 'open' if is_trading_time else 'closed'
        }
    @property
    def last_update_time(self):
        """获取最后更新时间"""
        return getattr(self, '_last_update_time', datetime.now())
    
    @last_update_time.setter
    def last_update_time(self, value):
        """设置最后更新时间"""
        self._last_update_time = value
