#!/usr/bin/env python3
"""
沪A股票历史数据下载器
支持批量下载指定时间段的股票数据，用于策略回测和分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
import time
import os
from loguru import logger
from data.database import DatabaseManager
from utils.real_data_fetcher import RealDataFetcher

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("AKShare可用，将获取真实数据")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AKShare未安装，将生成模拟数据")


class HistoricalDataDownloader:
    """历史数据下载器"""
    
    def __init__(self):
        """初始化下载器"""
        self.db_manager = DatabaseManager()
        self.data_fetcher = RealDataFetcher(self.db_manager)
        
        # 沪A常用股票池
        self.default_stocks = [
            # 银行股
            '600036',  # 招商银行
            '000001',  # 平安银行
            '600000',  # 浦发银行
            '601166',  # 兴业银行
            '000002',  # 万科A
            
            # 科技股
            '000858',  # 五粮液
            '600519',  # 贵州茅台
            '000002',  # 万科A
            '600036',  # 招商银行
            '000001',  # 平安银行
            
            # 指数ETF
            '510050',  # 50ETF
            '510300',  # 沪深300ETF
            '159919',  # 沪深300ETF
            
            # 热门股票
            '600519',  # 贵州茅台
            '000858',  # 五粮液
            '002415',  # 海康威视
            '000002',  # 万科A
            '600036',  # 招商银行
        ]
        
        logger.info("历史数据下载器初始化完成")
    
    def download_stock_data(self, symbol: str, start_date: str, end_date: str = None) -> bool:
        """
        下载单只股票的历史数据
        
        Args:
            symbol: 股票代码（如：000001）
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD），默认为今天
            
        Returns:
            是否下载成功
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        logger.info(f"开始下载 {symbol} 从 {start_date} 到 {end_date} 的数据")
        
        try:
            if AKSHARE_AVAILABLE:
                data = self._fetch_akshare_data(symbol, start_date, end_date)
            else:
                data = self._generate_mock_data(symbol, start_date, end_date)
            
            if not data.empty:
                self.db_manager.save_stock_data(symbol, data)
                logger.info(f"✅ {symbol} 数据下载完成，共 {len(data)} 条记录")
                return True
            else:
                logger.warning(f"⚠️ {symbol} 未获取到数据")
                return False
                
        except Exception as e:
            logger.error(f"❌ {symbol} 数据下载失败: {e}")
            return False
    
    def _fetch_akshare_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用AKShare获取真实数据"""
        try:
            # 获取股票历史数据
            data = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust=""  # 不复权
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
                '成交量': 'volume',
                '成交额': 'amount'
            })
            
            # 数据类型转换
            data['date'] = pd.to_datetime(data['date'])
            for col in ['open', 'high', 'low', 'close']:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            data['volume'] = pd.to_numeric(data['volume'], errors='coerce')
            
            # 设置日期为索引
            data.set_index('date', inplace=True)
            
            # 过滤无效数据
            data = data.dropna()
            
            return data[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logger.error(f"AKShare获取 {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def _generate_mock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟数据（当AKShare不可用时）"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 生成交易日期（排除周末）
        dates = pd.date_range(start=start, end=end, freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        if not dates:
            return pd.DataFrame()
        
        # 生成模拟价格数据
        np.random.seed(hash(symbol) % 2**32)
        base_price = 10 + (hash(symbol) % 50)
        
        prices = []
        current_price = base_price
        
        for date in dates:
            # 随机波动
            change = np.random.normal(0, 0.02)
            current_price *= (1 + change)
            current_price = max(current_price, 1.0)
            
            # 生成OHLC数据
            volatility = abs(np.random.normal(0, 0.01))
            high = current_price * (1 + volatility)
            low = current_price * (1 - volatility)
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
        
        data = pd.DataFrame(prices, index=dates)
        return data
    
    def batch_download(self, stock_list: List[str], start_date: str, 
                      end_date: str = None, delay: float = 1.0) -> dict:
        """
        批量下载股票数据
        
        Args:
            stock_list: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            delay: 请求间隔（秒），避免频率限制
            
        Returns:
            下载结果统计
        """
        results = {'success': [], 'failed': []}
        total = len(stock_list)
        
        logger.info(f"开始批量下载 {total} 只股票的数据")
        
        for i, symbol in enumerate(stock_list, 1):
            logger.info(f"进度: {i}/{total} - 正在下载 {symbol}")
            
            success = self.download_stock_data(symbol, start_date, end_date)
            
            if success:
                results['success'].append(symbol)
            else:
                results['failed'].append(symbol)
            
            # 延迟避免请求过于频繁
            if i < total:
                time.sleep(delay)
        
        logger.info(f"批量下载完成！成功: {len(results['success'])}, 失败: {len(results['failed'])}")
        
        if results['failed']:
            logger.warning(f"下载失败的股票: {results['failed']}")
        
        return results
    
    def download_popular_stocks(self, months: int = 6) -> dict:
        """
        下载热门股票数据
        
        Args:
            months: 下载几个月的数据
            
        Returns:
            下载结果
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        logger.info(f"下载热门股票最近 {months} 个月的数据")
        
        return self.batch_download(
            self.default_stocks,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
    
    def get_stock_list_by_market(self, market: str = 'all') -> List[str]:
        """
        获取市场股票列表
        
        Args:
            market: 市场类型 ('sh', 'sz', 'all')
            
        Returns:
            股票代码列表
        """
        if not AKSHARE_AVAILABLE:
            logger.warning("AKShare不可用，返回默认股票列表")
            return self.default_stocks
        
        try:
            if market == 'sh' or market == 'all':
                # 获取上海A股列表
                sh_stocks = ak.stock_info_a_code_name()
                sh_list = sh_stocks[sh_stocks['code'].str.startswith('60')]['code'].tolist()
            else:
                sh_list = []
            
            if market == 'sz' or market == 'all':
                # 获取深圳A股列表
                sz_stocks = ak.stock_info_a_code_name()
                sz_list = sz_stocks[
                    sz_stocks['code'].str.startswith('00') | 
                    sz_stocks['code'].str.startswith('30')
                ]['code'].tolist()
            else:
                sz_list = []
            
            all_stocks = sh_list + sz_list
            logger.info(f"获取到 {len(all_stocks)} 只股票")
            
            return all_stocks[:100]  # 限制数量避免过多
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return self.default_stocks
    
    def check_data_coverage(self, symbol: str) -> dict:
        """
        检查股票数据覆盖情况
        
        Args:
            symbol: 股票代码
            
        Returns:
            数据覆盖信息
        """
        try:
            data = self.db_manager.get_stock_data(symbol)
            
            if data.empty:
                return {
                    'symbol': symbol,
                    'has_data': False,
                    'record_count': 0,
                    'date_range': None
                }
            
            return {
                'symbol': symbol,
                'has_data': True,
                'record_count': len(data),
                'start_date': data.index.min().strftime('%Y-%m-%d'),
                'end_date': data.index.max().strftime('%Y-%m-%d'),
                'date_range': f"{data.index.min().strftime('%Y-%m-%d')} 到 {data.index.max().strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            logger.error(f"检查 {symbol} 数据覆盖失败: {e}")
            return {
                'symbol': symbol,
                'has_data': False,
                'error': str(e)
            }


def main():
    """主函数 - 提供交互式下载界面"""
    downloader = HistoricalDataDownloader()
    
    print("🚀 沪A股票历史数据下载器")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 下载单只股票数据")
        print("2. 批量下载热门股票数据")
        print("3. 批量下载自定义股票列表")
        print("4. 检查数据覆盖情况")
        print("5. 退出")
        
        choice = input("\n请输入选择 (1-5): ").strip()
        
        if choice == '1':
            # 下载单只股票
            symbol = input("请输入股票代码 (如: 000001): ").strip()
            months = input("请输入下载月数 (默认6个月): ").strip() or "6"
            
            try:
                months = int(months)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=months * 30)
                
                downloader.download_stock_data(
                    symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
            except ValueError:
                print("❌ 月数格式错误")
        
        elif choice == '2':
            # 下载热门股票
            months = input("请输入下载月数 (默认6个月): ").strip() or "6"
            
            try:
                months = int(months)
                results = downloader.download_popular_stocks(months)
                print(f"\n✅ 下载完成！成功: {len(results['success'])}, 失败: {len(results['failed'])}")
            except ValueError:
                print("❌ 月数格式错误")
        
        elif choice == '3':
            # 批量下载自定义列表
            stocks_input = input("请输入股票代码，用逗号分隔 (如: 000001,600036,000858): ").strip()
            months = input("请输入下载月数 (默认6个月): ").strip() or "6"
            
            try:
                stock_list = [s.strip() for s in stocks_input.split(',') if s.strip()]
                months = int(months)
                
                if not stock_list:
                    print("❌ 股票列表为空")
                    continue
                
                end_date = datetime.now()
                start_date = end_date - timedelta(days=months * 30)
                
                results = downloader.batch_download(
                    stock_list,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                print(f"\n✅ 下载完成！成功: {len(results['success'])}, 失败: {len(results['failed'])}")
                
            except ValueError:
                print("❌ 输入格式错误")
        
        elif choice == '4':
            # 检查数据覆盖
            symbol = input("请输入股票代码 (如: 000001): ").strip()
            
            coverage = downloader.check_data_coverage(symbol)
            print(f"\n📊 {symbol} 数据覆盖情况:")
            
            if coverage['has_data']:
                print(f"✅ 有数据")
                print(f"📈 记录数: {coverage['record_count']}")
                print(f"📅 时间范围: {coverage['date_range']}")
            else:
                print("❌ 无数据")
        
        elif choice == '5':
            print("👋 再见！")
            break
        
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == '__main__':
    main() 