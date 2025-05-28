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

    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None, limit: int = None) -> pd.DataFrame:
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
            # 首先尝试从数据库获取
            data = self.db_manager.get_stock_data(symbol, start_date, end_date, limit)
            
            if not data.empty:
                return data
            
            # 如果数据库没有数据，尝试从网络获取
            if start_date and end_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                
                if AKSHARE_AVAILABLE:
                    data = self._fetch_real_data(symbol, start_dt, end_dt)
                else:
                    data = self._generate_mock_data(symbol, start_dt, end_dt)
                
                if not data.empty:
                    # 保存到数据库
                    self.db_manager.save_stock_data(symbol, data)
                    return data
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取股票数据失败 {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            data: 股票数据DataFrame
            
        Returns:
            包含技术指标的DataFrame
        """
        try:
            if data.empty:
                return data
            
            data = data.copy()
            
            # 移动平均线
            data['ma5'] = data['close'].rolling(window=5).mean()
            data['ma10'] = data['close'].rolling(window=10).mean()
            data['ma20'] = data['close'].rolling(window=20).mean()
            data['ma60'] = data['close'].rolling(window=60).mean()
            
            # RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = data['close'].ewm(span=12).mean()
            exp2 = data['close'].ewm(span=26).mean()
            data['macd'] = exp1 - exp2
            data['macd_signal'] = data['macd'].ewm(span=9).mean()
            data['macd_hist'] = data['macd'] - data['macd_signal']
            
            # 布林带
            data['bb_middle'] = data['close'].rolling(window=20).mean()
            bb_std = data['close'].rolling(window=20).std()
            data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
            data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
            
            # KDJ
            low_min = data['low'].rolling(window=9).min()
            high_max = data['high'].rolling(window=9).max()
            rsv = (data['close'] - low_min) / (high_max - low_min) * 100
            data['k'] = rsv.ewm(com=2).mean()
            data['d'] = data['k'].ewm(com=2).mean()
            data['j'] = 3 * data['k'] - 2 * data['d']
            
            return data
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return data
    
    def get_index_data(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指数数据
        
        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            指数数据DataFrame
        """
        try:
            if not AKSHARE_AVAILABLE:
                # 如果AKShare不可用，生成模拟指数数据
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                return self._generate_mock_data(index_code, start_dt, end_dt)
            
            # 获取指数历史数据
            data = ak.stock_zh_index_daily(symbol=index_code)
            
            if data.empty:
                return pd.DataFrame()
            
            # 重命名列
            data = data.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # 确保数据类型正确
            data['date'] = pd.to_datetime(data['date'])
            data.set_index('date', inplace=True)
            
            # 筛选日期范围
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            data = data[(data.index >= start_dt) & (data.index <= end_dt)]
            
            return data[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logger.error(f"获取指数数据失败 {index_code}: {e}")
            # 返回模拟数据作为备用
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            return self._generate_mock_data(index_code, start_dt, end_dt)
