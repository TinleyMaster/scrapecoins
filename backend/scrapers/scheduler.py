#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫调度器
"""

import time
import random
from flask import current_app
from ..app import scheduler, socketio
from ..database.db import CryptoDataManager
from ..models.crypto import CryptoData
from .coingecko import CoinGeckoScraper
from datetime import datetime, timedelta

# 全局应用实例
_app_instance = None
_app_config = None  # 添加配置缓存

# 新增：统一的停止标志存储
_scraper_stop_flags = {
    "coingecko": False,
    "dropstab": False,
    "tokenomist": False,
}


def set_scraper_stop_flag(scraper_type, flag=True):
    """设置爬虫停止标志（供 /scraper/<type>/stop 使用）"""
    try:
        _scraper_stop_flags[scraper_type] = bool(flag)
        log_and_emit(f"🛑 已设置 {scraper_type} 爬虫停止标志为 {flag}", "warning")
    except Exception as e:
        print(f"设置停止标志失败: {e}")


def send_log_to_frontend(message, log_type="info"):
    """发送日志消息到前端"""
    try:
        socketio.emit(
            "scraper_log",
            {
                "message": message,
                "type": log_type,
                "timestamp": datetime.now().isoformat(),
            },
        )
    except Exception as e:
        print(f"发送日志到前端失败: {e}")


def log_and_emit(message, log_type="info"):
    """同时打印到控制台和发送到前端"""
    print(message)
    send_log_to_frontend(message, log_type)


def get_next_random_interval(min_interval, max_interval):
    """获取下次爬取的随机间隔（秒）"""
    return random.randint(min_interval, max_interval)


def schedule_next_scrape():
    """调度下次爬取任务"""
    try:
        if not _app_config:
            print("❌ 应用配置未初始化")
            return

        min_interval = _app_config.get("SCRAPE_INTERVAL_MIN", 600)
        max_interval = _app_config.get("SCRAPE_INTERVAL_MAX", 1800)

        next_interval = get_next_random_interval(min_interval, max_interval)
        next_run_time = datetime.now() + timedelta(seconds=next_interval)

        # 移除现有的调度任务
        try:
            scheduler.remove_job("crypto_scraper_scheduled")
        except:
            pass

        # 添加新的调度任务
        scheduler.add_job(
            func=scrape_crypto_data_and_reschedule_scheduled,
            trigger="date",
            run_date=next_run_time,
            id="crypto_scraper_scheduled",
            name="定时单页加密货币数据爬取",
            replace_existing=True,
        )

        # 同时发送到控制台和前端日志系统
        next_time_message = f"⏰ 下次单页爬取时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} (间隔: {next_interval // 60}分{next_interval % 60}秒)"
        log_and_emit(next_time_message, "info")

    except Exception as e:
        log_and_emit(f"❌ 调度下次爬取任务失败: {e}", "error")


def scrape_crypto_data_and_reschedule():
    """爬取数据并重新调度"""
    scrape_crypto_data()
    schedule_next_scrape()


def scrape_crypto_data():
    """爬取加密货币数据的定时任务（统一为单页爬取）"""
    start_time = datetime.now()
    log_and_emit(
        f"=== 开始爬取任务 {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===", "info"
    )

    try:
        # 直接使用存储的应用实例，不使用代理
        if not _app_instance:
            log_and_emit("❌ 应用实例未设置", "error")
            return

        # 使用推送的应用上下文
        with _app_instance.app_context():
            log_and_emit("📱 应用上下文创建成功", "success")

            # 测试数据库连接
            crypto_manager = CryptoDataManager()
            if not crypto_manager.test_connection():
                log_and_emit("❌ 数据库连接失败，终止爬取任务", "error")
                return

            # 获取配置 - 强制设置为单页爬取
            per_page = _app_config.get("CRYPTO_PER_PAGE", 250) if _app_config else 250
            max_pages = 1  # 强制设置为1页
            page_delay_min = (
                _app_config.get("PAGE_DELAY_MIN", 2.0) if _app_config else 2.0
            )
            page_delay_max = (
                _app_config.get("PAGE_DELAY_MAX", 5.0) if _app_config else 5.0
            )

            log_and_emit(f"📊 开始单页爬取 - 每页{per_page}个币种", "info")

            # 创建爬虫实例
            scraper = CoinGeckoScraper(page_delay_min, page_delay_max)

            # 爬取单页数据 - 使用正确的方法名
            log_and_emit(f"🔍 正在爬取第 1/1 页...", "info")

            # 使用 scrape_all_crypto_data 方法，但限制为1页
            scraped_data = scraper.scrape_all_crypto_data(
                per_page=per_page, max_pages=max_pages
            )

            if scraped_data:
                log_and_emit(f"✅ 第1页爬取成功: {len(scraped_data)}条数据", "success")

                # 转换为 CryptoData 对象
                crypto_objects = []
                for item in scraped_data:
                    try:
                        crypto_obj = CryptoData(
                            {
                                "id": item.get("id"),
                                "symbol": item.get("symbol"),
                                "name": item.get("name"),
                                "price_usd": item.get("current_price"),
                                "price_change_percentage_24h": item.get(
                                    "price_change_percentage_24h"
                                ),
                                "market_cap": item.get("market_cap"),
                                "volume_24h": item.get("total_volume"),
                                "circulating_supply": item.get("circulating_supply"),
                                "rank": item.get("market_cap_rank"),
                                "source": "coingecko",
                                "timestamp": start_time,  # 使用 datetime 对象而不是字符串
                            }
                        )
                        crypto_objects.append(crypto_obj)
                    except Exception as e:
                        log_and_emit(
                            f"❌ 数据转换失败 {item.get('symbol', 'Unknown')}: {e}",
                            "warning",
                        )

                # 保存数据
                if crypto_objects:
                    saved_count = _save_scraped_data(crypto_objects, start_time)
                    log_and_emit(f"💾 数据保存完成: {saved_count}条", "success")
                else:
                    log_and_emit("❌ 没有有效数据可保存", "error")
            else:
                log_and_emit(f"❌ 第1页爬取失败", "error")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_and_emit(
                f"=== 爬取任务完成 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ===", "info"
            )
            log_and_emit(f"⏱️  总耗时: {duration:.2f}秒", "info")

    except Exception as e:
        log_and_emit(f"❌ 爬取数据时出错: {e}", "error")
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
        duplicates = {
            symbol: count for symbol, count in symbol_counts.items() if count > 1
        }
        if duplicates:
            print(f"⚠️  发现重复symbol: {duplicates}")
            duplicate_count = sum(count - 1 for count in duplicates.values())

        print(f"📊 数据保存统计:")
        print(f"  - API返回数据: {len(scraped_data)}条")
        print(f"  - 重复数据: {duplicate_count}条")
        print(f"  - 预期保存: {len(scraped_data) - duplicate_count}条")

        # 在_save_scraped_data方法中，为每条记录设置当前时间戳
        for crypto in scraped_data:
            try:
                # 使用当前时间作为timestamp，确保数据的时效性
                crypto.timestamp = datetime.now()
                mongo_data = crypto.to_mongo_dict()

                result = crypto_manager.collection.update_one(
                    {"id": crypto.id}, {"$set": mongo_data}, upsert=True
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
    _app_instance = (
        app._get_current_object() if hasattr(app, "_get_current_object") else app
    )
    # 缓存配置
    _app_config = dict(app.config)
    print(f"✅ 应用实例已设置: {type(_app_instance)}")


def start_crypto_scraping_jobs(app):
    """启动加密货币爬虫定时任务"""
    global _app_instance, _app_config

    set_app_instance(app)

    with app.app_context():
        min_interval = app.config.get("SCRAPE_INTERVAL_MIN", 600)
        max_interval = app.config.get("SCRAPE_INTERVAL_MAX", 1800)

        log_and_emit(
            f"🪙 CoinGecko 爬虫调度已启动 (间隔: {min_interval // 60}-{max_interval // 60}分钟)",
            "info",
        )

        # 立即执行第一次爬取
        scheduler.add_job(
            func=scrape_crypto_data_and_reschedule,
            trigger="date",
            run_date=datetime.now(),
            id="crypto_scraper_initial",
            name="初始加密货币数据爬取",
            replace_existing=True,
        )

        schedule_next_scrape()


def start_investor_scraping_jobs(app):
    """启动投资者爬虫定时任务"""
    global _app_instance, _app_config

    set_app_instance(app)

    with app.app_context():
        min_interval = app.config.get("INVESTOR_SCRAPE_INTERVAL_MIN", 60)  # 1分钟
        max_interval = app.config.get("INVESTOR_SCRAPE_INTERVAL_MAX", 600)  # 10分钟

        log_and_emit(
            f"💼 DropsTab 投资者爬虫调度已启动 (间隔: {min_interval // 60}-{max_interval // 60}分钟)",
            "info",
        )

        # 立即执行第一次爬取
        scheduler.add_job(
            func=scrape_investor_data_and_reschedule,
            trigger="date",
            run_date=datetime.now(),
            id="investor_scraper_initial",
            name="初始投资者数据爬取",
            replace_existing=True,
        )

        schedule_next_investor_scrape()


def start_tokenomist_scraping_jobs(app):
    """启动 Tokenomist 代币解锁爬虫定时任务（即时执行一次并调度下一次）"""
    global _app_instance, _app_config
    set_app_instance(app)
    # 清除停止标志
    set_scraper_stop_flag("tokenomist", False)
    with app.app_context():
        # 使用 Tokenomist 专用配置
        min_interval = app.config.get("TOKENOMIST_SCRAPE_INTERVAL_MIN", 7200)  # 2小时
        max_interval = app.config.get("TOKENOMIST_SCRAPE_INTERVAL_MAX", 7200)  # 2小时
        log_and_emit(
            f"🔓 Tokenomist 爬虫调度已启动 (间隔: {min_interval // 3600}小时)",
            "info",
        )
        # 立即执行一次
        scheduler.add_job(
            func=scrape_tokenomist_data_and_reschedule,
            trigger="date",
            run_date=datetime.now(),
            id="tokenomist_scraper_initial",
            name="初始 Tokenomist 代币解锁爬取",
            replace_existing=True,
        )
        schedule_next_tokenomist_scrape()


def scrape_tokenomist_data_and_reschedule():
    """执行一次 Tokenomist 爬取并调度下一次"""
    scrape_tokenomist_data()
    schedule_next_tokenomist_scrape()


def scrape_tokenomist_data():
    """Tokenomist 代币解锁爬取任务（调用 Playwright 脚本）"""
    start_time = datetime.now()
    log_and_emit(
        f"=== 开始 Tokenomist 代币解锁爬取 {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===",
        "info",
    )
    try:
        if not _app_instance:
            log_and_emit("❌ 应用实例未设置", "error")
            return

        # 如果已下达停止标志，直接跳过本次执行
        if _scraper_stop_flags.get("tokenomist"):
            log_and_emit("⏹️ 已设置 Tokenomist 停止标志，跳过本次执行", "warning")
            return

        with _app_instance.app_context():
            # 懒加载，避免无 Playwright 时模块导入失败影响其他爬虫
            from ..scrapers.tokenomist_scraper import TokenomistScraper
            import asyncio

            # 执行一次异步爬取
            log_and_emit("🚀 正在启动 Playwright 无头浏览器...", "info")
            # 传入 should_stop 回调，使运行中的任务也能及时退出
            asyncio.run(
                TokenomistScraper(
                    should_stop=lambda: _scraper_stop_flags.get("tokenomist", False)
                ).run()
            )
            log_and_emit("✅ Tokenomist 爬取任务完成", "success")

    except Exception as e:
        log_and_emit(f"❌ Tokenomist 爬取失败: {e}", "error")


def schedule_next_tokenomist_scrape():
    """调度下一次 Tokenomist 爬取（使用专用2小时间隔），如已下达停止标志则不再调度"""
    try:
        if not _app_config:
            print("❌ 应用配置未初始化")
            return

        # 如设置了停止标志则不调度
        if _scraper_stop_flags.get("tokenomist"):
            log_and_emit("⏹️ 已设置 Tokenomist 停止标志，停止后续调度", "warning")
            try:
                scheduler.remove_job("tokenomist_scraper_scheduled")
            except Exception:
                pass
            return

        # 使用 Tokenomist 专用配置
        min_interval = _app_config.get("TOKENOMIST_SCRAPE_INTERVAL_MIN", 7200)  # 2小时
        max_interval = _app_config.get("TOKENOMIST_SCRAPE_INTERVAL_MAX", 7200)  # 2小时
        next_interval = get_next_random_interval(min_interval, max_interval)
        next_run_time = datetime.now() + timedelta(seconds=next_interval)

        # 先移除旧的
        try:
            scheduler.remove_job("tokenomist_scraper_scheduled")
        except Exception:
            pass

        scheduler.add_job(
            func=scrape_tokenomist_data_and_reschedule,
            trigger="date",
            run_date=next_run_time,
            id="tokenomist_scraper_scheduled",
            name="定时 Tokenomist 代币解锁爬取",
            replace_existing=True,
        )

        log_and_emit(
            f"⏰ 下次 Tokenomist 爬取时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} (间隔: {next_interval // 3600}小时{(next_interval % 3600) // 60}分钟)",
            "info",
        )

    except Exception as e:
        log_and_emit(f"❌ 调度下一次 Tokenomist 爬取失败: {e}", "error")


# 保持原有的统一启动方法以兼容旧接口
def start_scraping_jobs(app):
    """启动所有爬虫定时任务"""
    start_crypto_scraping_jobs(app)
    start_investor_scraping_jobs(app)
    # 可选：同时启动 Tokenomist（如不希望默认启动可注释掉）
    # start_tokenomist_scraping_jobs(app)


def scrape_investor_data_and_reschedule():
    """爬取投资者数据并重新调度"""
    scrape_investor_data()
    schedule_next_investor_scrape()


def scrape_investor_data():
    """执行一次 DropsTab 投资者数据爬取"""
    start_time = datetime.now()
    log_and_emit(
        f"=== 开始 DropsTab 投资者数据爬取 {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===",
        "info",
    )
    try:
        if not _app_instance:
            log_and_emit("❌ 应用实例未设置", "error")
            return

        with _app_instance.app_context():
            # 懒加载，避免导入开销或依赖问题
            from ..scrapers.dropstab import DropstabScraper

            # 读取可选的最大页数配置（如未配置则使用爬虫默认的 370）
            max_pages = None
            if _app_config:
                max_pages = _app_config.get("INVESTOR_MAX_PAGES", None)

            scraper = DropstabScraper()
            if max_pages is not None:
                log_and_emit(f"🚀 正在爬取投资者数据（最多 {max_pages} 页）...", "info")
                scraper.scrape_investors_data(max_pages=max_pages)
            else:
                log_and_emit("🚀 正在爬取投资者数据（使用默认最大页数）...", "info")
                scraper.scrape_investors_data()

            log_and_emit("✅ 投资者数据爬取完成", "success")

    except Exception as e:
        log_and_emit(f"❌ 投资者数据爬取失败: {e}", "error")


def schedule_next_investor_scrape():
    """调度下次 DropsTab 投资者数据爬取"""
    try:
        if not _app_config:
            print("❌ 应用配置未初始化")
            return

        # 如果设置了停止标志则不再调度
        if _scraper_stop_flags.get("dropstab"):
            log_and_emit("⏹️ 已设置 DropsTab 停止标志，停止后续调度", "warning")
            try:
                scheduler.remove_job("investor_scraper_scheduled")
            except Exception:
                pass
            return

        min_interval = _app_config.get("INVESTOR_SCRAPE_INTERVAL_MIN", 60)
        max_interval = _app_config.get("INVESTOR_SCRAPE_INTERVAL_MAX", 600)
        next_interval = get_next_random_interval(min_interval, max_interval)
        next_run_time = datetime.now() + timedelta(seconds=next_interval)

        # 先移除旧任务（若存在）
        try:
            scheduler.remove_job("investor_scraper_scheduled")
        except Exception:
            pass

        scheduler.add_job(
            func=scrape_investor_data_and_reschedule,
            trigger="date",
            run_date=next_run_time,
            id="investor_scraper_scheduled",
            name="定时投资者数据爬取",
            replace_existing=True,
        )

        log_and_emit(
            f"⏰ 下次投资者数据爬取时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} (间隔: {next_interval // 60}分{next_interval % 60}秒)",
            "info",
        )
    except Exception as e:
        log_and_emit(f"❌ 调度下一次投资者数据爬取失败: {e}", "error")
