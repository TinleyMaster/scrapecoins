#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tokenomist.ai 代币解锁信息爬虫

依赖安装:
pip install playwright pymongo
playwright install chromium

技术方案:
- 使用 Playwright 处理 JavaScript 动态渲染
- 遵守 robots.txt 规则 (Allow: /*)
- 通过 DOM 解析提取数据，避免直接调用 API
"""

import asyncio
import re
import csv
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Callable
from playwright.async_api import async_playwright, Browser, Page
import pymongo
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class TokenUnlockData:
    """代币解锁数据模型"""
    
    def __init__(self, data: Dict[str, Any] = None):
        if data:
            self.token_name = data.get('token_name', '')
            self.unlock_time = data.get('unlock_time', '')
            self.unlock_amount = data.get('unlock_amount', '')
            self.unlock_percentage = data.get('unlock_percentage', '')
            self.current_price = data.get('current_price', '')
            self.price_change_24h = data.get('price_change_24h', '')
            self.market_cap = data.get('market_cap', '')
            self.circulating_supply = data.get('circulating_supply', '')
            self.released_percentage = data.get('released_percentage', '')
            self.next_7d_emission = data.get('next_7d_emission', '')
            self.source = data.get('source', 'tokenomist.ai')
            self.timestamp = data.get('timestamp', datetime.utcnow())
        else:
            self.token_name = ''
            self.unlock_time = ''
            self.unlock_amount = ''
            self.unlock_percentage = ''
            self.current_price = ''
            self.price_change_24h = ''
            self.market_cap = ''
            self.circulating_supply = ''
            self.released_percentage = ''
            self.next_7d_emission = ''
            self.source = 'tokenomist.ai'
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'token_name': self.token_name,
            'unlock_time': self.unlock_time,
            'unlock_amount': self.unlock_amount,
            'unlock_percentage': self.unlock_percentage,
            'current_price': self.current_price,
            'price_change_24h': self.price_change_24h,
            'market_cap': self.market_cap,
            'circulating_supply': self.circulating_supply,
            'released_percentage': self.released_percentage,
            'next_7d_emission': self.next_7d_emission,
            'source': self.source,
            'timestamp': self.timestamp
        }

class TokenomistScraper:
    """Tokenomist.ai 爬虫类"""
    
    def __init__(self, should_stop: Optional[Callable[[], bool]] = None):
        self.base_url = "https://tokenomist.ai/"
        self.alt_base_urls = ["https://www.tokenomist.ai/"]
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.browser_config = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-gpu",
            ],
        }
        # 从环境变量注入代理（如需要）
        proxy_server = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        if proxy_server:
            self.browser_config["proxy"] = {"server": proxy_server}

        # 停止回调（默认始终返回 False）
        self.should_stop = should_stop or (lambda: False)

        # Mongo 相关
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None

        # 重试配置
        self.max_retries = 3
        self.retry_delay = 2
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/crypto_db')
        self.db_name = 'crypto_db'
        self.collection_name = 'token_unlocks'
        
        # 浏览器配置
        self.browser_config = {
            'headless': True,  # 无头模式
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920x1080'
            ]
        }
        
        # 用户代理 - 模拟 Chrome 浏览器
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/119.0.0.0 Safari/537.36'
        )
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 2
        
        # MongoDB 连接
        self.client = None
        self.db = None
        self.collection = None
    
    def connect_to_mongodb(self):
        """连接到 MongoDB 数据库"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            # 测试连接
            self.client.admin.command('ping')
            print("✓ MongoDB 连接成功")
            
            # 创建索引以提高查询性能
            self.collection.create_index([
                ('token_name', pymongo.ASCENDING),
                ('timestamp', pymongo.DESCENDING)
            ])
            self.collection.create_index('unlock_time')
            self.collection.create_index('source')
            
        except Exception as e:
            print(f"✗ MongoDB 连接失败: {e}")
            raise
    
    def close_mongodb_connection(self):
        """关闭 MongoDB 连接"""
        if self.client:
            self.client.close()
            print("✓ MongoDB 连接已关闭")
    
    async def setup_page(self, browser: Browser) -> Page:
        """设置页面配置"""
        context = await browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
            ignore_https_errors=True,  # 可选
        )

        # 拦截并屏蔽重资源，提升加载速度与稳定性
        async def _route_handler(route):
            rtype = route.request.resource_type
            if rtype in ("image", "media", "font"):
                await route.abort()
            else:
                await route.continue_()
        await context.route("**/*", _route_handler)

        # 创建新页面
        page = await context.new_page()

        # 提升默认超时时间（注意：这些是同步方法，不能 await）
        page.set_default_navigation_timeout(90000)  # 90s
        page.set_default_timeout(45000)             # 45s

        # 设置额外的请求头，避免被识别为爬虫
        await page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        return page
    
    async def wait_for_table_data(self, page: Page) -> bool:
        """等待表格数据加载完成"""
        try:
            # 等待表格容器出现
            await page.wait_for_selector('table, .table, [data-testid="table"]', timeout=30000)
            print("✓ 表格容器已加载")
            
            # 等待表格行数据出现（至少有一行数据）
            await page.wait_for_selector('tbody tr, .table-row', timeout=30000)
            print("✓ 表格数据已加载")
            
            # 额外等待 JavaScript 完全渲染（避免数据不完整）
            await page.wait_for_timeout(3000)
            
            return True
            
        except Exception as e:
            print(f"✗ 等待表格数据超时: {e}")
            return False
    
    def parse_unlock_time(self, time_text: str) -> str:
        """解析解锁时间为具体 UTC 日期时间（ISO 格式）。支持绝对日期和相对时间。"""
        if not time_text:
            return ''
        
        text = re.sub(r'\s+', ' ', time_text.strip())
    
        # 1) 绝对日期解析：先从文本中提取出可能的日期片段，再尝试不同格式
        absolute_patterns = [
            # 纯日期片段捕获
            (r'(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?)', ['%Y-%m-%d', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M']),
            (r'(\d{1,2}/\d{1,2}/\d{4}(?:\s+\d{2}:\d{2})?)', ['%m/%d/%Y', '%m/%d/%Y %H:%M']),
            (r'(\d{1,2}\s+[A-Za-z]{3,9},?\s*\d{4})', ['%d %b %Y', '%d %B %Y', '%d %b, %Y', '%d %B, %Y']),
            (r'([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})', ['%b %d, %Y', '%B %d, %Y']),
        ]
        for pattern, fmts in absolute_patterns:
            m = re.search(pattern, text)
            if m:
                piece = m.group(1)
                for fmt in fmts:
                    try:
                        dt = datetime.strptime(piece, fmt)
                        # 无时区信息，按 UTC 00:00 处理（或保持已有的时分）
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        # 若格式只有日期，补齐 00:00:00
                        if fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d %b %Y', '%d %B %Y', '%d %b, %Y', '%d %B, %Y']:
                            dt = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
                        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                    except Exception:
                        continue
    
        # 2) 相对时间解析：例如 "3d 2h", "in 5 days", "2 hours 30 minutes", "1w 2d"
        # 累加 weeks/days/hours/minutes/seconds
        total = timedelta(0)
        for num, unit in re.findall(r'(\d+)\s*(weeks?|w|days?|d|hours?|h|minutes?|mins?|m|seconds?|secs?|s)', text, flags=re.I):
            n = int(num)
            u = unit.lower()
            if u.startswith('w'):
                total += timedelta(weeks=n)
            elif u.startswith('d'):
                total += timedelta(days=n)
            elif u.startswith('h'):
                total += timedelta(hours=n)
            elif u.startswith('m'):
                total += timedelta(minutes=n)
            elif u.startswith('s'):
                total += timedelta(seconds=n)
    
        if total.total_seconds() > 0 or re.search(r'\bin\s+\d+', text, flags=re.I):
            # "in X ..." 场景没匹配到单位也算相对时间的提示，这里仅在捕到单位时生效
            if total.total_seconds() > 0:
                dt = datetime.now(timezone.utc) + total
                return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
        # 未能解析，返回空字符串（避免把原始描述作为时间写入 DB）
        return ''
    
    def clean_amount_text(self, amount_text: str) -> str:
        """清理解锁金额文本"""
        if not amount_text:
            return ''
        
        # 移除多余空白字符
        amount_text = re.sub(r'\s+', ' ', amount_text.strip())
        
        # 优先匹配美元金额格式 $X.XXm, $X.XXb, $X.XXk
        dollar_match = re.search(r'\$[\d,]+\.?\d*[kmb]?', amount_text, re.I)
        if dollar_match:
            return dollar_match.group(0)
        
        # 匹配代币数量格式 X.XX TOKEN
        token_match = re.search(r'([\d,.]+ \w+)', amount_text)
        if token_match:
            return token_match.group(1)
        
        # 匹配纯数字+单位格式 X.XXm, X.XXb, X.XXk
        number_match = re.search(r'[\d,]+\.?\d*[kmb]?', amount_text, re.I)
        if number_match:
            return number_match.group(0)
        
        return amount_text
    
    def clean_price_text(self, price_text: str) -> str:
        """清理价格文本"""
        if not price_text:
            return ''
        
        # 提取价格格式 $X.XX
        match = re.search(r'\$[\d,]+\.?\d*', price_text)
        if match:
            return match.group(0)
        
        return price_text.strip()
    
    def clean_percentage_text(self, percent_text: str) -> str:
        """清理百分比文本"""
        if not percent_text:
            return ''
        
        # 提取百分比格式 +/-X.XX%
        match = re.search(r'[+-]?\d+\.?\d*%', percent_text)
        if match:
            return match.group(0)
        
        return percent_text.strip()
    
    async def extract_table_data(self, page: Page) -> List[Dict[str, Any]]:
        """提取表格数据（获取所有字段）"""
        data_list = []
        
        try:
            # 使用更精确的表格行选择器
            rows = await page.query_selector_all('table tbody tr.group.cursor-pointer')
            print(f"✓ 找到 {len(rows)} 条数据行")
            
            for i, row in enumerate(rows):
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) < 9:  # 跳过广告行或不完整行（需要至少9列）
                        continue
                    
                    # 1) 项目符号（第2列 - Project Name）
                    name_cell = cells[1]
                    name_text = await name_cell.inner_text()
                    token_name = name_text.strip().split('\n')[0].strip()
                    
                    # 2) 价格（第3列 - Price）
                    price_text = await cells[2].inner_text()
                    current_price = self.clean_price_text(price_text)
                    
                    # 3) 24h 涨幅（第4列 - 24h %）
                    pct_text = await cells[3].inner_text()
                    price_change_24h = self.clean_percentage_text(pct_text)
                    
                    # 4) 市值（第5列 - M.Cap）
                    market_cap_text = await cells[4].inner_text()
                    market_cap = self.clean_amount_text(market_cap_text)
                    
                    # 5) 流通供应量（第6列 - Cir. Supply）
                    cir_supply_text = await cells[5].inner_text()
                    circulating_supply = self.clean_amount_text(cir_supply_text)
                    
                    # 6) 释放百分比（第7列 - Released Percentage）
                    released_pct_cell = cells[6]
                    released_pct_text = await released_pct_cell.inner_text()
                    released_percentage = self.clean_percentage_text(released_pct_text)
                    
                    # 7) 即将解锁（第8列 - Upcoming Unlock）
                    upcoming_text = await cells[7].inner_text()
                    upcoming_clean = re.sub(r'\s+', ' ', upcoming_text.strip())
                    
                    # 先提取金额（优先匹配美元格式）
                    unlock_amount = self.clean_amount_text(upcoming_clean)
                    
                    # 提取百分比
                    unlock_percentage = ''
                    pct_match = re.search(r'(\d+\.\d+%)', upcoming_clean)
                    if pct_match:
                        unlock_percentage = pct_match.group(1)
                    
                    # 提取倒计时信息（匹配 XD XH XM XS 格式）
                    countdown_match = re.search(r'(\d+D(?:\s*\d+H)?(?:\s*\d+M)?(?:\s*\d+S)?)', upcoming_clean, re.I)
                    if not countdown_match:
                        # 如果没有找到倒计时，尝试其他格式
                        countdown_match = re.search(r'(\d+d(?:\s*\d+h)?|in\s+\d+\s+days?|\d+\s+days?|\d+\s+hours?)', upcoming_clean, re.I)
                    
                    countdown_text = countdown_match.group(1) if countdown_match else ''
                    
                    # 解析为具体 UTC 时间
                    unlock_time = self.parse_unlock_time(countdown_text or upcoming_clean)
                    
                    # 8) 未来7天排放量（第9列 - Next 7D Emission）
                    if len(cells) > 8:
                        next_7d_text = await cells[8].inner_text()
                        next_7d_emission = self.clean_amount_text(next_7d_text)
                    else:
                        next_7d_emission = ''
                    
                    if i < 3:
                        print(f"🔎 行 {i+1}: {token_name} | 价格: {current_price} | 市值: {market_cap} | 流通量: {circulating_supply} | 释放%: {released_percentage} | 解锁: {unlock_amount} ({unlock_percentage}) | 倒计时: {countdown_text} | 时间: {unlock_time} | 7天排放: {next_7d_emission}")
                    
                    # 构建完整数据
                    token_data = {
                        'token_name': token_name,
                        'current_price': current_price,
                        'price_change_24h': price_change_24h,
                        'market_cap': market_cap,
                        'circulating_supply': circulating_supply,
                        'released_percentage': released_percentage,
                        'unlock_amount': unlock_amount,
                        'unlock_percentage': unlock_percentage,
                        'unlock_time': unlock_time,
                        'next_7d_emission': next_7d_emission,
                        'source': 'tokenomist.ai',
                        'timestamp': datetime.utcnow()
                    }
                    
                    # 只要有项目名就记录
                    if token_name:
                        data_list.append(token_data)
                        
                except Exception as e:
                    print(f"❌ 解析第 {i+1} 行时出错: {e}")
                    continue
            
            print(f"✅ 成功提取 {len(data_list)} 条有效数据")
            return data_list
            
        except Exception as e:
            print(f"❌ 提取表格数据时出错: {e}")
            return []
    
    async def scrape_with_retry(self) -> List[Dict[str, Any]]:
        """带重试机制的爬取方法"""
        for attempt in range(self.max_retries):
            # 开始尝试前检查停止信号
            if self.should_stop():
                print("⏹️ 检测到停止信号，取消当前爬取任务")
                return []
            try:
                print(f"📡 开始第 {attempt + 1} 次爬取尝试...")
                
                async with async_playwright() as p:
                    # 启动浏览器
                    browser = await p.chromium.launch(**self.browser_config)

                    try:
                        # 设置页面
                        page = await self.setup_page(browser)

                        # 依次尝试主域名与备用域名
                        last_exc = None
                        for nav_url in [self.base_url] + getattr(self, "alt_base_urls", []):
                            if self.should_stop():
                                print("⏹️ 检测到停止信号，终止导航并退出")
                                await browser.close()
                                return []
                            try:
                                print(f"🌐 正在访问: {nav_url}")
                                response = await page.goto(
                                    nav_url,
                                    wait_until='domcontentloaded',
                                    timeout=90000
                                )
                                if response is None or (getattr(response, "status", None) is None or response.status < 400):
                                    print(f"✓ 页面加载成功: {nav_url}")
                                    break
                                raise Exception(f"页面响应状态异常: {response.status}")
                            except Exception as ne:
                                print(f"⚠️ 访问 {nav_url} 失败: {ne}")
                                last_exc = ne
                                continue
                        else:
                            # 所有候选 URL 都失败
                            raise last_exc or Exception("所有候选 URL 访问失败")

                        # 可选：等待到较空闲的网络状态（不强制）
                        try:
                            await page.wait_for_load_state('networkidle', timeout=15000)
                        except Exception:
                            print("⚠️ networkidle 未达成，继续进行...")

                        if self.should_stop():
                            print("⏹️ 检测到停止信号，跳过表格等待并退出")
                            await browser.close()
                            return []

                        # 等待表格数据加载
                        if not await self.wait_for_table_data(page):
                            print("⚠️ 表格数据第一次等待超时，尝试刷新页面后重试等待...")
                            try:
                                await page.reload(wait_until='domcontentloaded', timeout=60000)
                                await page.wait_for_timeout(2000)
                            except Exception as re:
                                print(f"⚠️ 刷新页面异常: {re}")

                            if self.should_stop():
                                print("⏹️ 检测到停止信号，刷新后仍停止退出")
                                await browser.close()
                                return []

                            if not await self.wait_for_table_data(page):
                                raise Exception("表格数据加载超时")

                        if self.should_stop():
                            print("⏹️ 检测到停止信号，取消数据提取并退出")
                            await browser.close()
                            return []

                        # 提取表格数据
                        data = await self.extract_table_data(page)
                        if data:
                            print(f"✓ 爬取成功，获取 {len(data)} 条数据")
                            return data
                        else:
                            raise Exception("未提取到有效数据")

                    finally:
                        # 关闭浏览器
                        await browser.close()

            except Exception as e:
                print(f"✗ 第 {attempt + 1} 次爬取失败: {e}")

                if attempt < self.max_retries - 1:
                    # 重试前检查停止信号
                    if self.should_stop():
                        print("⏹️ 检测到停止信号，中止后续重试")
                        return []
                    print(f"⏳ {self.retry_delay} 秒后重试...")
                    await asyncio.sleep(self.retry_delay)
                    self.retry_delay *= 2  # 指数退避

        print("✗ 所有重试都失败")
        return []
    
    def save_to_mongodb(self, data_list: List[Dict[str, Any]]) -> bool:
        """保存数据到 MongoDB（去重：按 source + token_name upsert）"""
        if not data_list:
            print("⚠️ 无数据需要保存")
            return False
        
        try:
            # 转换为 TokenUnlockData 对象
            token_unlock_docs = []
            for data in data_list:
                token_unlock = TokenUnlockData(data)
                token_unlock_docs.append(token_unlock.to_dict())
            
            # 批量 upsert，使用简化的去重策略：仅 source + token_name
            ops = []
            for doc in token_unlock_docs:
                # 去重策略：只使用 source 和 token_name
                filter_doc = {
                    'source': doc.get('source', 'tokenomist.ai'),
                    'token_name': doc.get('token_name', '').strip(),  # 去除空格
                }
                
                update_doc = {
                    '$set': {
                        # 即将解锁相关字段
                        'unlock_time': doc.get('unlock_time', ''),
                        'unlock_amount': doc.get('unlock_amount', ''),
                        'unlock_percentage': doc.get('unlock_percentage', ''),
                        # 其他字段
                        'current_price': doc.get('current_price', ''),
                        'price_change_24h': doc.get('price_change_24h', ''),
                        'market_cap': doc.get('market_cap', ''),
                        'circulating_supply': doc.get('circulating_supply', ''),
                        'released_percentage': doc.get('released_percentage', ''),
                        'next_7d_emission': doc.get('next_7d_emission', ''),
                        'timestamp': doc.get('timestamp', datetime.utcnow()),
                    }
                }
                ops.append(pymongo.UpdateOne(filter_doc, update_doc, upsert=True))
            
            if not ops:
                print("⚠️ 无可写入操作")
                return False
            
            result = self.collection.bulk_write(ops, ordered=False)
            upserted = result.upserted_count
            modified = result.modified_count
            matched = result.matched_count
            print(f"✓ 去重写入完成：upsert={upserted}, modified={modified}, matched={matched}")
            return True
        
        except Exception as e:
            print(f"✗ 保存到 MongoDB 失败: {e}")
            return False
    
    def save_to_csv(self, data_list: List[Dict[str, Any]], archive_dir: str = 'data/archives') -> bool:
        """保存数据到 CSV 文件（按时间命名存档）"""
        if not data_list:
            print("⚠️ 无数据需要保存到CSV")
            return False
        
        try:
            # 创建存档目录
            os.makedirs(archive_dir, exist_ok=True)
            
            # 生成时间戳文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'tokenomist_unlocks_{timestamp}.csv'
            filepath = os.path.join(archive_dir, filename)
            
            # 保存到时间戳文件
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                if data_list:
                    fieldnames = data_list[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    # 写入表头
                    writer.writeheader()
                    
                    # 写入数据
                    writer.writerows(data_list)
            
            print(f"✓ 数据已存档到: {filepath}")
            
            # 同时保存到根目录的最新文件（保持向后兼容）
            latest_filename = 'token_unlocks.csv'
            with open(latest_filename, 'w', newline='', encoding='utf-8') as csvfile:
                if data_list:
                    fieldnames = data_list[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data_list)
            
            print(f"✓ 最新数据已保存到: {latest_filename}")
            return True
        
        except Exception as e:
            print(f"✗ 保存到 CSV 失败: {e}")
            return False

    def save_to_csv_with_cleanup(self, data_list: List[Dict[str, Any]], archive_dir: str = 'data/archives', keep_days: int = 30) -> bool:
        """保存数据到 CSV 文件并清理旧文件"""
        if not self.save_to_csv(data_list, archive_dir):
            return False
        
        try:
            # 清理超过指定天数的旧文件
            import time
            current_time = time.time()
            cutoff_time = current_time - (keep_days * 24 * 60 * 60)
            
            if os.path.exists(archive_dir):
                for filename in os.listdir(archive_dir):
                    if filename.startswith('tokenomist_unlocks_') and filename.endswith('.csv'):
                        filepath = os.path.join(archive_dir, filename)
                        file_time = os.path.getctime(filepath)
                        
                        if file_time < cutoff_time:
                            os.remove(filepath)
                            print(f"🗑️ 已清理旧文件: {filename}")
            
            return True
        
        except Exception as e:
            print(f"⚠️ 清理旧文件时出错: {e}")
            return True  # 保存成功，清理失败不影响主要功能
        
        except Exception as e:
            print(f"⚠️ 清理旧文件时出错: {e}")
            return True  # 保存成功，清理失败不影响主要功能

    async def run(self):
        """主运行方法"""
        print("🚀 Tokenomist.ai 代币解锁信息爬虫启动")
        print("=" * 50)
        
        # 连接数据库
        self.connect_to_mongodb()
        
        try:
            # 执行爬取
            data = await self.scrape_with_retry()
            
            if data:
                # 保存到 MongoDB
                self.save_to_mongodb(data)
                
                # 保存到 CSV 存档（带自动清理）
                self.save_to_csv_with_cleanup(data, archive_dir='data/archives', keep_days=30)
                
                print(f"🎉 爬取完成！获取 {len(data)} 条代币解锁信息")
            else:
                print("😞 爬取失败，未获取到数据")
        
        finally:
            # 关闭数据库连接
            self.close_mongodb_connection()

# 独立运行脚本
async def main():
    """
    主函数 - 运行代币解锁信息爬虫
    
    合规说明:
    - 遵守 robots.txt 规则 (Allow: /*)
    - 使用合理的请求间隔和重试机制
    - 仅爬取公开页面数据，不调用私有API
    - 生产环境建议增加更长的请求间隔
    """
    scraper = TokenomistScraper()
    await scraper.run()

if __name__ == "__main__":
    # 运行爬虫
    asyncio.run(main())


async def check_pagination_info(self, page: Page) -> Dict[str, Any]:
    """检查分页信息"""
    try:
        # 查找分页信息文本 "1–50 of 28" 格式
        pagination_selector = 'div:has-text("of")'
        pagination_elements = await page.query_selector_all(pagination_selector)
        
        for element in pagination_elements:
            text = await element.inner_text()
            # 匹配 "X–Y of Z" 格式
            match = re.search(r'(\d+)\s*–\s*(\d+)\s+of\s+(\d+)', text)
            if match:
                start_item = int(match.group(1))
                end_item = int(match.group(2))
                total_items = int(match.group(3))
                items_per_page = end_item - start_item + 1
                total_pages = (total_items + items_per_page - 1) // items_per_page
                current_page = (start_item + items_per_page - 1) // items_per_page
                
                print(f"📄 分页信息: 第 {current_page}/{total_pages} 页, 显示 {start_item}-{end_item}/{total_items} 项")
                
                return {
                    'current_page': current_page,
                    'total_pages': total_pages,
                    'total_items': total_items,
                    'items_per_page': items_per_page,
                    'start_item': start_item,
                    'end_item': end_item
                }
        
        # 如果没找到分页信息，假设只有一页
        print("📄 未找到分页信息，假设只有一页数据")
        return {
            'current_page': 1,
            'total_pages': 1,
            'total_items': 0,
            'items_per_page': 50,
            'start_item': 1,
            'end_item': 50
        }
        
    except Exception as e:
        print(f"✗ 检查分页信息失败: {e}")
        return {
            'current_page': 1,
            'total_pages': 1,
            'total_items': 0,
            'items_per_page': 50,
            'start_item': 1,
            'end_item': 50
        }

async def navigate_to_next_page(self, page: Page) -> bool:
    """导航到下一页"""
    try:
        # 查找Next按钮
        next_selectors = [
            'button:has-text("Next"):not([disabled])',
            'button[aria-label*="next"]:not([disabled])',
            'button[aria-label*="Next"]:not([disabled])',
            '.pagination button:last-child:not([disabled])'
        ]
        
        next_button = None
        for selector in next_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button:
                    print(f"✓ 找到Next按钮: {selector}")
                    break
            except:
                continue
        
        if not next_button:
            print("⚠️ 未找到可用的Next按钮（可能已是最后一页）")
            return False
        
        # 点击Next按钮
        print("🔄 点击Next按钮...")
        await next_button.click()
        
        # 等待页面加载
        await page.wait_for_timeout(2000)
        
        # 等待表格重新加载
        try:
            await page.wait_for_selector('table tbody tr', timeout=10000)
            print("✓ 下一页加载完成")
            return True
        except:
            print("⚠️ 下一页表格加载超时")
            return False
            
    except Exception as e:
        print(f"✗ 导航到下一页失败: {e}")
        return False

async def scrape_all_pages(self, page: Page) -> List[Dict[str, Any]]:
    """爬取所有分页数据"""
    all_data = []
    current_page = 1
    max_pages = 10  # 设置最大页数限制，避免无限循环
    
    while current_page <= max_pages:
        # 检查停止信号
        if self.should_stop():
            print("⏹️ 检测到停止信号，终止分页爬取")
            break
            
        print(f"📖 正在爬取第 {current_page} 页...")
        
        # 检查分页信息
        pagination_info = await self.check_pagination_info(page)
        
        # 等待当前页表格数据加载
        if not await self.wait_for_table_data(page):
            print(f"⚠️ 第 {current_page} 页表格数据加载失败")
            break
        
        # 提取当前页数据
        page_data = await self.extract_table_data(page)
        if page_data:
            all_data.extend(page_data)
            print(f"✓ 第 {current_page} 页提取到 {len(page_data)} 条数据")
        else:
            print(f"⚠️ 第 {current_page} 页未提取到数据")
        
        # 检查是否还有下一页
        if current_page >= pagination_info['total_pages']:
            print(f"✓ 已到达最后一页 ({pagination_info['total_pages']})")
            break
        
        # 导航到下一页
        if not await self.navigate_to_next_page(page):
            print("⚠️ 无法导航到下一页，结束爬取")
            break
        
        current_page += 1
        
        # 页面间隔，避免请求过快
        await page.wait_for_timeout(1000)
    
    print(f"🎯 分页爬取完成，总共获取 {len(all_data)} 条数据")
    return all_data