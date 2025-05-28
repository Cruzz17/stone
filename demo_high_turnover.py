#!/usr/bin/env python3
"""
高换手率股票回测系统演示
展示如何使用系统进行股票策略回测
"""

from datetime import datetime


def demo_quick_test():
    """演示快速测试功能"""
    print("=" * 60)
    print("🚀 高换手率股票回测系统演示")
    print("=" * 60)
    
    print("\n📋 系统功能:")
    print("1. 拉取过去一个月换手率最高的股票")
    print("2. 下载历史数据并计算技术指标")
    print("3. 运行多种量化策略回测")
    print("4. 分析收益和风险指标")
    print("5. 生成图表和报告")
    
    print("\n📊 预定义股票池 (24只活跃股票):")
    active_stocks = [
        "000858(五粮液)", "002415(海康威视)", "002594(比亚迪)", "300059(东方财富)",
        "300122(智飞生物)", "300124(汇川技术)", "600000(浦发银行)", "600036(招商银行)",
        "601318(中国平安)", "600519(贵州茅台)", "000001(平安银行)", "000002(万科A)",
        "002230(科大讯飞)", "002475(立讯精密)", "300015(爱尔眼科)", "300033(同花顺)"
    ]
    
    for i, stock in enumerate(active_stocks[:16], 1):
        print(f"   {i:2d}. {stock}")
    print("   ... 等24只股票")
    
    print("\n🎯 测试策略:")
    print("   📈 双均线策略 - 基于5日和20日均线交叉")
    print("   📉 RSI策略 - 基于14日RSI超买超卖")
    print("   🌊 MACD策略 - 基于MACD金叉死叉")
    
    print("\n💰 回测设置:")
    print("   初始资金: 1,000,000元")
    print("   手续费率: 万分之3")
    print("   印花税率: 千分之1")
    print("   数据周期: 60天")
    
    print("\n" + "=" * 60)
    
    # 询问是否运行
    choice = input("是否运行快速测试? (y/n): ").lower().strip()
    
    if choice == 'y':
        print("\n🔄 正在运行快速测试...")
        try:
            from quick_turnover_test import QuickTurnoverTest
            test = QuickTurnoverTest()
            test.run_quick_test()
        except Exception as e:
            print(f"❌ 运行失败: {e}")
            print("请检查依赖包是否正确安装")
    else:
        print("✅ 演示结束")

def demo_full_backtest():
    """演示完整回测功能"""
    print("\n" + "=" * 60)
    print("🔍 完整高换手率回测演示")
    print("=" * 60)
    
    print("\n📋 完整回测流程:")
    print("1. 🔍 获取全市场A股换手率数据")
    print("2. 📊 筛选换手率最高的100只股票")
    print("3. 📈 下载这些股票的历史数据")
    print("4. 🎯 运行多策略回测分析")
    print("5. 📋 生成详细报告和图表")
    print("6. 💾 导出结果到CSV文件")
    
    print("\n⚠️  注意事项:")
    print("   - 需要安装AKShare: pip install akshare")
    print("   - 获取换手率数据较耗时(约5-10分钟)")
    print("   - 建议首次使用选择较少股票数量")
    
    print("\n🔧 可配置参数:")
    print("   - 统计天数: 30天(默认)")
    print("   - 股票数量: 50-100只")
    print("   - 策略选择: 单策略或全部策略")
    print("   - 数据周期: 60-120天")
    
    choice = input("\n是否运行完整回测? (y/n): ").lower().strip()
    
    if choice == 'y':
        # 获取参数
        try:
            days = int(input("统计换手率天数 (默认30): ") or "30")
            top_n = int(input("选择股票数量 (默认50): ") or "50")
            data_days = int(input("历史数据天数 (默认60): ") or "60")
            
            print(f"\n🔄 正在运行完整回测...")
            print(f"   统计天数: {days}天")
            print(f"   股票数量: {top_n}只")
            print(f"   数据周期: {data_days}天")
            
            from high_turnover_backtest import HighTurnoverBacktest
            backtest_system = HighTurnoverBacktest()
            backtest_system.run_complete_backtest(
                days=days,
                top_n=top_n,
                strategy='all',
                data_days=data_days
            )
            
        except ValueError:
            print("❌ 参数输入错误，请输入数字")
        except Exception as e:
            print(f"❌ 运行失败: {e}")
            print("请检查网络连接和AKShare安装")
    else:
        print("✅ 演示结束")

def show_usage_examples():
    """显示使用示例"""
    print("\n" + "=" * 60)
    print("📚 使用示例")
    print("=" * 60)
    
    print("\n1️⃣ 快速测试 (推荐新手):")
    print("```bash")
    print("python quick_turnover_test.py")
    print("```")
    
    print("\n2️⃣ 完整回测:")
    print("```bash")
    print("python high_turnover_backtest.py")
    print("```")
    
    print("\n3️⃣ 自定义参数:")
    print("```python")
    print("from high_turnover_backtest import HighTurnoverBacktest")
    print("")
    print("# 创建回测系统")
    print("backtest = HighTurnoverBacktest()")
    print("")
    print("# 运行自定义回测")
    print("backtest.run_complete_backtest(")
    print("    days=30,        # 统计30天换手率")
    print("    top_n=100,      # 选择前100只股票")
    print("    strategy='all', # 测试所有策略")
    print("    data_days=90    # 下载90天数据")
    print(")")
    print("```")
    
    print("\n4️⃣ 单独测试某个策略:")
    print("```python")
    print("# 只测试MACD策略")
    print("backtest.run_complete_backtest(strategy='macd')")
    print("")
    print("# 只测试RSI策略")
    print("backtest.run_complete_backtest(strategy='rsi')")
    print("")
    print("# 只测试双均线策略")
    print("backtest.run_complete_backtest(strategy='double_ma')")
    print("```")

def show_results_explanation():
    """显示结果说明"""
    print("\n" + "=" * 60)
    print("📊 结果指标说明")
    print("=" * 60)
    
    print("\n💰 收益指标:")
    print("   📈 总收益率: 整个回测期间的总收益百分比")
    print("   📊 年化收益率: 按年计算的收益率")
    print("   🎯 超额收益: 相对基准指数的超额收益")
    
    print("\n⚠️  风险指标:")
    print("   📉 最大回撤: 资产价值的最大下跌幅度")
    print("   📊 波动率: 收益率的标准差，衡量风险")
    print("   🎯 夏普比率: 风险调整后的收益指标")
    
    print("\n🎯 交易指标:")
    print("   ✅ 胜率: 盈利交易占总交易的比例")
    print("   💰 盈亏比: 平均盈利与平均亏损的比值")
    print("   🔄 交易次数: 总的买卖交易次数")
    
    print("\n🌟 策略评价标准:")
    print("   🌟🌟🌟 优秀: 年化收益>20%, 夏普比率>1.5, 回撤<5%")
    print("   🌟🌟   良好: 年化收益>10%, 夏普比率>1.0, 回撤<10%")
    print("   🌟     一般: 年化收益>5%,  夏普比率>0.5, 回撤<20%")

def main():
    """主函数"""
    print("🎯 高换手率股票回测系统")
    print("=" * 60)
    print("本系统用于筛选高换手率股票并进行量化策略回测")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        print("\n📋 请选择功能:")
        print("1. 🚀 快速测试演示")
        print("2. 🔍 完整回测演示")
        print("3. 📚 查看使用示例")
        print("4. 📊 查看结果说明")
        print("5. ❌ 退出")
        
        choice = input("\n请输入选择 (1-5): ").strip()
        
        if choice == '1':
            demo_quick_test()
        elif choice == '2':
            demo_full_backtest()
        elif choice == '3':
            show_usage_examples()
        elif choice == '4':
            show_results_explanation()
        elif choice == '5':
            print("\n✅ 感谢使用！")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main() 