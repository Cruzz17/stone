#!/usr/bin/env python3
"""
启动真实数据模拟交易
"""

import time
from loguru import logger
from utils.config_loader import config
from trading.simulation_engine import RealSimulationEngine


def main():
    """主函数"""
    print("🚀 启动真实数据模拟交易系统")
    print("=" * 60)

    try:
        # 加载配置
        config_data = config.config
        
        # 如果配置为空，使用默认配置
        if config_data is None:
            config_data = {
                'trading': {'initial_capital': 100000},
                'position_management': {
                    'max_single_position': 0.25,
                    'max_total_position': 0.90,
                    'cash_reserve': 0.10
                },
                'risk_management': {
                    'stop_loss': 0.08,
                    'take_profit': 0.15
                },
                'strategies': {
                    'double_ma': {'weight': 0.4},
                    'rsi': {'weight': 0.3},
                    'macd': {'weight': 0.3}
                },
                'stock_pool': {
                    'default_stocks': ['000001', '000002', '600000', '600036', '000858']
                },
                'simulation': {
                    'signal_combination': 'weighted_average',
                    'min_signal_confidence': 0.6
                }
            }
            print("使用默认配置")

        # 创建模拟交易引擎
        engine = RealSimulationEngine(config_data)

        # 启动模拟交易
        engine.start_simulation()

        print("✅ 模拟交易系统已启动")
        print("📊 实时监控中...")
        print("按 Ctrl+C 停止")

        # 监控循环
        try:
            while True:
                time.sleep(10)

                # 获取状态
                status = engine.get_current_status()

                if status:
                    portfolio = status.get('portfolio_status')
                    market = status.get('market_status', {})

                    print(f"\r⏰ {market.get('current_time', '')} | "
                          f"总资产: ¥{portfolio.total_value:,.0f} | "
                          f"盈亏: {portfolio.total_pnl_pct:+.2%} | "
                          f"持仓: {portfolio.position_count} | "
                          f"信号: {status.get('total_signals', 0)} | "
                          f"交易: {status.get('total_trades', 0)}", end="")

        except KeyboardInterrupt:
            print("\n\n🛑 收到停止信号")

        finally:
            # 停止模拟交易
            engine.stop_simulation()
            print("✅ 模拟交易系统已停止")

            # 显示最终统计
            final_status = engine.get_current_status()
            if final_status:
                portfolio = final_status.get('portfolio_status')
                print(f"\n📊 最终统计:")
                print(f"   总资产: ¥{portfolio.total_value:,.2f}")
                print(f"   总收益: ¥{portfolio.total_pnl:,.2f} ({portfolio.total_pnl_pct:+.2%})")
                print(f"   持仓数: {portfolio.position_count}")
                print(f"   交易数: {final_status.get('total_trades', 0)}")
                print(f"   信号数: {final_status.get('total_signals', 0)}")

    except Exception as e:
        logger.error(f"系统异常: {e}")
        print(f"❌ 系统异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
