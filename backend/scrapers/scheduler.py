#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫调度器
"""

import time
import random
from flask import current_app
from ..app import scheduler
from ..database.db import CryptoDataManager
from ..models.crypto import CryptoData
from .coingecko import CoinGeckoScraper
from datetime import datetime, timedelta

# 全局应用实例
_app_instance = None
_app_config = None  # 添加配置缓存

def get_next_random_interval(min_interval, max_interval):
    """获取下次爬取的随机间隔（秒）"""
    return random.randint(min_interval, max_interval)

def schedule_next_scrape():
    """调度下次爬取任务"""
    try:
        if not _app_config:
            print("❌ 应用配置未初始化")
            return
            
        min_interval = _app_config.get('SCRAPE_INTERVAL_MIN', 600)
        max_interval = _app_config.get('SCRAPE_INTERVAL_MAX', 1800)
        
        next_interval = get_next_random_interval(min_interval, max_interval)
        next_run_time = datetime.now() + timedelta(seconds=next_interval)
        
        # 移除现有的调度任务
        try:
            scheduler.remove_job('crypto_scraper_scheduled')
        except:
            pass
        
        # 添加新的调度任务
        scheduler.add_job(
            func=scrape_crypto_data_and_reschedule_scheduled,
            trigger="date",
            run_date=next_run_time,
            id='crypto_scraper_scheduled',
            name='定时单页加密货币数据爬取',
            replace_existing=True
        )
        
        print(f"下次单页爬取时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} (间隔: {next_interval//60}分{next_interval%60}秒)")
        
    except Exception as e:
        print(f"调度下次爬取任务失败: {e}")

def scrape_crypto_data_and_reschedule():
    """爬取数据并重新调度"""
    scrape_crypto_data()
    schedule_next_scrape()

def scrape_crypto_data():
    """爬取加密货币数据的定时任务（统一为单页爬取）"""
    start_time = datetime.now()
    print(f"\n=== 开始爬取任务 {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    try:
        # 直接使用存储的应用实例，不使用代理
        if not _app_instance:
            print("❌ 应用实例未设置")
            return
            
        # 使用推送的应用上下文
        with _app_instance.app_context():
            print("📱 应用上下文创建成功")
            
            # 测试数据库连接
            crypto_manager = CryptoDataManager()
            if not crypto_manager.test_connection():
                print("❌ 数据库连接失败，终止爬取任务")
                return
            
            # 获取配置 - 强制设置为单页爬取
            per_page = _app_config.get('CRYPTO_PER_PAGE', 250) if _app_config else 250
            max_pages = 1  # 强制设置为1页
            page_delay_min = _app_config.get('PAGE_DELAY_MIN', 2.0) if _app_config else 2.0
            page_delay_max = _app_config.get('PAGE_DELAY_MAX', 5.0) if _app_config else 5.0
            
            print(f"📊 开始单页爬取 - 每页{per_page}个币种")
            
            # 创建爬虫实例
            scraper = CoinGeckoScraper(page_delay_min, page_delay_max)
            
            # 爬取单页数据 - 使用正确的方法名
            print(f"🔍 爬取第1页数据...")
            
            # 使用 scrape_all_crypto_data 方法，但限制为1页
            scraped_data = scraper.scrape_all_crypto_data(per_page=per_page, max_pages=max_pages)
            
            if scraped_data:
                print(f"✅ 第1页爬取成功: {len(scraped_data)}条数据")
                
                # 转换为 CryptoData 对象
                crypto_objects = []
                for item in scraped_data:
                    try:
                        crypto_obj = CryptoData({
                            'id': item.get('id'),
                            'symbol': item.get('symbol'),
                            'name': item.get('name'),
                            'price_usd': item.get('current_price'),
                            'price_change_percentage_24h': item.get('price_change_percentage_24h'),
                            'market_cap': item.get('market_cap'),
                            'volume_24h': item.get('total_volume'),
                            'circulating_supply': item.get('circulating_supply'),
                            'rank': item.get('market_cap_rank'),
                            'source': 'coingecko',
                            'timestamp': start_time  # 使用 datetime 对象而不是字符串
                        })
                        crypto_objects.append(crypto_obj)
                    except Exception as e:
                        print(f"❌ 数据转换失败 {item.get('symbol', 'Unknown')}: {e}")
                
                # 保存数据
                if crypto_objects:
                    saved_count = _save_scraped_data(crypto_objects, start_time)
                    print(f"💾 数据保存完成: {saved_count}条")
                else:
                    print("❌ 没有有效数据可保存")
            else:
                print(f"❌ 第1页爬取失败")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"\n=== 爬取任务完成 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
            print(f"⏱️  总耗时: {duration:.2f}秒")
            
    except Exception as e:
        print(f"❌ 爬取数据时出错: {e}")
        import traceback
        traceback.print_exc()

def _save_scraped_data(scraped_data, start_time):
    """保存爬取的数据到数据库"""
    if not scraped_data:
        return 0
    
    try:
        crypto_manager = CryptoDataManager()
        saved_count = 0
        duplicate_count = 0
        
        # 统计重复的symbol
        symbol_counts = {}
        for crypto in scraped_data:
            symbol = crypto.symbol
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        # 报告重复情况
        duplicates = {symbol: count for symbol, count in symbol_counts.items() if count > 1}
        if duplicates:
            print(f"⚠️  发现重复symbol: {duplicates}")
            duplicate_count = sum(count - 1 for count in duplicates.values())
        
        print(f"📊 数据保存统计:")
        print(f"  - API返回数据: {len(scraped_data)}条")
        print(f"  - 重复数据: {duplicate_count}条")
        print(f"  - 预期保存: {len(scraped_data) - duplicate_count}条")
        
        for crypto in scraped_data:
            try:
                # 使用 to_mongo_dict() 方法，避免 _id 字段问题
                mongo_data = crypto.to_mongo_dict()
                
                # 使用id作为主键进行upsert操作
                result = crypto_manager.collection.update_one(
                    {'id': crypto.id},  # 使用id作为查询条件
                    {'$set': mongo_data},
                    upsert=True
                )
                
                if result.upserted_id or result.modified_count > 0:
                    saved_count += 1
                    
            except Exception as e:
                print(f"❌ 保存数据失败 {crypto.symbol}: {e}")
        
        print(f"✅ 实际保存: {saved_count}条数据")
        
        # 验证数据库中的记录数
        total_in_db = crypto_manager.collection.count_documents({})
        print(f"📊 数据库总记录数: {total_in_db}条")
        
        return saved_count
        
    except Exception as e:
        print(f"❌ 保存数据时出错: {e}")
        return 0

def scrape_crypto_data_and_reschedule_scheduled():
    """定时调度的爬取任务"""
    scrape_crypto_data()
    schedule_next_scrape()

def set_app_instance(app):
    """设置全局应用实例"""
    global _app_instance, _app_config
    # 存储实际的应用实例，而不是代理
    _app_instance = app._get_current_object() if hasattr(app, '_get_current_object') else app
    # 缓存配置
    _app_config = dict(app.config)
    print(f"✅ 应用实例已设置: {type(_app_instance)}")

def start_scraping_jobs(app):
    """启动爬虫定时任务"""
    global _app_instance, _app_config
    
    # 设置应用实例和配置
    set_app_instance(app)
    
    with app.app_context():
        min_interval = app.config.get('SCRAPE_INTERVAL_MIN', 600)
        max_interval = app.config.get('SCRAPE_INTERVAL_MAX', 1800)
        page_delay_min = app.config.get('PAGE_DELAY_MIN', 2.0)
        page_delay_max = app.config.get('PAGE_DELAY_MAX', 5.0)
        
        print(f"爬虫调度已启动:")
        print(f"  间隔范围: {min_interval//60}-{max_interval//60}分钟")
        print(f"  页面延迟: {page_delay_min}-{page_delay_max}秒")
        print(f"  爬取策略: 统一单页爬取")
        print(f"  每页数量: {app.config.get('CRYPTO_PER_PAGE', 250)}")
        print(f"  爬取页数: 1页 (最重要的加密货币)")
        
        # 🚀 立即执行第一次爬取
        print("\n🚀 手动启动 - 立即执行首次单页数据爬取...")
        
        # 添加立即执行的任务
        scheduler.add_job(
            func=scrape_crypto_data_and_reschedule,
            trigger="date",
            run_date=datetime.now(),  # 立即执行
            id='crypto_scraper_initial',
            name='初始单页加密货币数据爬取',
            replace_existing=True
        )
        
        print("首次单页爬取任务已调度，将在几秒内开始执行...")
        
        # 调度后续的单页爬取任务
        schedule_next_scrape()
