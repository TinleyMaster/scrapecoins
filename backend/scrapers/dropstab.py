#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DropsTab 投资者数据爬虫
"""

import requests
import time
import random
import pandas as pd
import re
from typing import List, Dict, Any
from .base_scraper import BaseScraper
from datetime import datetime
from ..database.db import InvestorDataManager
from ..models.investor import InvestorData

class DropstabScraper(BaseScraper):
    """DropsTab 投资者数据爬虫类"""
    
    def __init__(self, page_delay_min=10.0, page_delay_max=20.0, debug=True):
        super().__init__('dropstab', 'https://dropstab.com')
        self.page_delay_min = page_delay_min
        self.page_delay_max = page_delay_max
        self.base_rate_limit_delay = 5.0
        self.debug = debug
        self.max_retries = 3
        self.seen_investors = set()
        
        # 设置请求头
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        self.investor_manager = InvestorDataManager()
        
        if self.debug:
            print("🔧 调试模式已启用")
            print(f"📋 请求头配置: {dict(self.session.headers)}")
            print(f"⏱️  页面延迟范围: {self.page_delay_min}-{self.page_delay_max}秒")

    def get_supported_cryptos(self) -> List[str]:
        """获取支持的加密货币列表（投资者爬虫不需要加密货币列表）"""
        return []

    def scrape_crypto_data(self, crypto_ids: List[str]) -> List[Dict[str, Any]]:
        """爬取加密货币数据（投资者爬虫不需要实现此方法）"""
        return []

    def scrape_investors_data(self, max_pages=370):
        """通过API爬取投资者数据"""
        all_investors = []
        api_url = "https://api2.icodrops.com/portfolio/api/investors"
        
        print(f"🚀 开始通过API爬取投资者数据 (最多 {max_pages} 页)")
        print(f"🌐 API接口: {api_url}")
        print(f"💾 每页数据将立即保存到MongoDB数据库")
        
        # 测试数据库连接
        if not self.investor_manager.test_connection():
            print("❌ 数据库连接失败，无法保存数据")
            return []
        
        print("✅ 数据库连接测试成功，开始爬取...")
        
        try:
            for page in range(0, max_pages):  # API页码从0开始
                display_page = page + 1  # 用于显示的页码（从1开始）
                print(f"\n🔍 正在爬取第 {display_page}/{max_pages} 页投资者数据...")
                
                # 重试机制
                success = False
                for retry in range(self.max_retries):
                    try:
                        # 构建请求参数
                        params = {
                            "sort": "rank",
                            "order": "ASC",
                            "page": page,
                            "size": 20,
                            "filters": {}  
                        }
                        
                        print(f"📡 API请求参数: {params} (尝试 {retry + 1}/{self.max_retries})")
                        
                        if self.debug:
                            print(f"⏱️  执行速率限制延迟...")
                        
                        # 发送POST请求到API
                        self._rate_limit()
                        
                        # 添加随机延迟
                        extra_delay = random.uniform(1.0, 3.0)
                        time.sleep(extra_delay)
                        
                        start_time = time.time()
                        response = self.session.post(
                            api_url,
                            json=params,  # 发送JSON数据
                            timeout=60,
                            headers={
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                                **self.session.headers
                            }
                        )
                        request_time = time.time() - start_time
                        
                        print(f"📊 请求耗时: {request_time:.2f}秒, 状态码: {response.status_code}")
                        if self.debug:
                            print(f"📏 响应内容长度: {len(response.text)} 字符")
                        
                        response.raise_for_status()
                        success = True
                        break  # 成功则跳出重试循环
                        
                    except requests.exceptions.Timeout:
                        print(f"⏰ 第 {display_page} 页请求超时 (尝试 {retry + 1}/{self.max_retries})")
                        if retry < self.max_retries - 1:
                            time.sleep((retry + 1) * 5)
                    except requests.exceptions.ConnectionError as e:
                        print(f"🌐 第 {display_page} 页连接错误 (尝试 {retry + 1}/{self.max_retries}): {e}")
                        if retry < self.max_retries - 1:
                            time.sleep((retry + 1) * 10)
                    except requests.exceptions.RequestException as e:
                        print(f"❌ 第 {display_page} 页请求失败 (尝试 {retry + 1}/{self.max_retries}): {e}")
                        if retry < self.max_retries - 1:
                            time.sleep((retry + 1) * 10)
                
                if not success:
                    print(f"❌ 第 {display_page} 页所有重试都失败，跳过此页")
                    continue
                
                # 解析JSON响应
                try:
                    api_data = response.json()
                    if self.debug:
                        print(f"🔍 API响应结构: {list(api_data.keys()) if isinstance(api_data, dict) else 'N/A'}")
                        
                    # 从API响应中提取投资者数据
                    investors = self._parse_api_response(api_data)
                    
                    if not investors:
                        print(f"⚠️  第 {display_page} 页没有找到投资者数据")
                        # 检查是否到达最后一页
                        if api_data.get('last', False) or api_data.get('empty', True):
                            print(f"📄 已到达最后一页，停止爬取")
                            break
                        continue
                    
                    # 立即保存当前页面数据到数据库
                    print(f"💾 正在保存第 {page + 1} 页的 {len(investors)} 个投资者到数据库...")
                    saved_count = self._save_page_to_database(investors, page + 1)
                    
                    if saved_count > 0:
                        all_investors.extend(investors)
                        print(f"✅ 第 {page + 1} 页保存成功: {saved_count}/{len(investors)} 个投资者已保存到数据库")
                        print(f"📊 累计已保存: {len(all_investors)} 个投资者")
                    else:
                        print(f"❌ 第 {page + 1} 页数据保存失败")
                    
                    if self.debug and investors:
                        print(f"📋 本页投资者样本:")
                        for i, inv in enumerate(investors[:3], 1):
                            print(f"   {i}. {inv.get('name', 'N/A')} - {inv.get('ventureType', 'N/A')} - 排名: {inv.get('rank', 'N/A')}")
                        if len(investors) > 3:
                            print(f"   ... 还有 {len(investors) - 3} 个投资者")
                    
                    # 检查分页信息
                    total_pages = api_data.get('totalPages', 0)
                    current_page = api_data.get('number', 0)
                    is_last = api_data.get('last', False)
                    
                    print(f"📄 分页信息: 第 {current_page + 1}/{total_pages} 页")
                    
                    if is_last or current_page >= total_pages - 1:
                        print(f"📄 已到达最后一页，停止爬取")
                        break
                    
                    # 页面间延迟
                    if page < max_pages - 1:
                        delay = random.uniform(self.page_delay_min, self.page_delay_max)
                        print(f"⏱️  等待 {delay:.1f} 秒后继续...")
                        time.sleep(delay)
                        
                except ValueError as e:
                    print(f"❌ 第 {page + 1} 页JSON解析失败: {e}")
                    if self.debug:
                        print(f"🔍 响应内容预览: {response.text[:500]}...")
                    continue
                    
        except KeyboardInterrupt:
            print(f"\n⏹️  用户中断爬取，已获取并保存 {len(all_investors)} 个投资者数据")
        except Exception as e:
            print(f"❌ 爬取过程中出错: {e}")
            if self.debug:
                import traceback
                print(f"📋 错误堆栈: {traceback.format_exc()}")
        
        print(f"\n🎉 爬取完成！")
        print(f"📊 总计处理: {len(all_investors)} 个投资者")
        print(f"💾 已全部保存到MongoDB数据库")
        
        return all_investors

    def _parse_api_response(self, api_data):
        """解析API响应数据"""
        investors = []
        
        try:
            # 获取content数组
            content = api_data.get('content', [])
            if not content:
                print("❌ API响应中没有content数组")
                return investors
            
            print(f"📊 找到 {len(content)} 个投资者记录")
            
            for i, item in enumerate(content):
                try:
                    # 处理时间戳转换
                    last_round_date = item.get('lastRoundDate')
                    if last_round_date:
                        # 转换毫秒时间戳为datetime
                        last_round_date = datetime.fromtimestamp(last_round_date / 1000)
                    
                    # 映射API字段到本地字段 (排除coInvestments)
                    investor_data = {
                        # 基础信息
                        'id': item.get('id'),
                        'name': item.get('name', ''),
                        'investorSlug': item.get('investorSlug', ''),
                        'logo': item.get('logo', ''),
                        'image': item.get('image', ''),
                        'country': item.get('country', {}),
                        'ventureType': item.get('ventureType', ''),
                        'rank': item.get('rank'),
                        'rating': item.get('rating'),
                        'tier': item.get('tier', ''),
                        'lead': item.get('lead', False),
                        'description': item.get('description', ''),
                        
                        # 社交媒体和链接
                        'twitterUrl': item.get('twitterUrl', ''),
                        'links': item.get('links', []),
                        'twitterScore': item.get('twitterScore'),
                        
                        # 投资统计
                        'totalInvestments': item.get('totalInvestments'),
                        'leadInvestments': item.get('leadInvestments'),
                        'roundsPerYear': item.get('roundsPerYear'),
                        'publicSalesCount': item.get('publicSalesCount'),
                        'lastRoundDate': last_round_date,
                        
                        # ROI数据
                        'avgPublicRoi': item.get('avgPublicRoi', {}),
                        'avgPrivateRoi': item.get('avgPrivateRoi', {}),
                        
                        # 币安上市数据
                        'binanceListed': item.get('binanceListed', {}),
                        
                        # 投资分布
                        'roundsDistribution': item.get('roundsDistribution', {}),
                        
                        # 投资组合项目
                        'portfolioProjects': item.get('portfolioProjects', []),
                        
                        # 销售ID
                        'saleIds': item.get('saleIds', []),
                        
                        # 元数据
                        'source': 'icodrops_api',
                        'scraped_at': datetime.utcnow(),
                        'timestamp': datetime.utcnow()
                    }
                    
                    # 验证必要字段
                    if not investor_data['name']:
                        print(f"⚠️ 第 {i+1} 个记录缺少名称，跳过")
                        continue
                    
                    investors.append(investor_data)
                    
                    if (i + 1) % 10 == 0:
                        print(f"📈 已处理 {i + 1} 个投资者")
                    
                    # 调试信息：显示前3个记录的详细信息
                    if self.debug and i < 3:
                        print(f"✅ 解析投资者 {i+1}: {investor_data['name']}")
                        print(f"   - 排名: {investor_data['rank']}")
                        print(f"   - 类型: {investor_data['ventureType']}")
                        print(f"   - 评分: {investor_data['rating']}")
                        print(f"   - 投资总数: {investor_data['totalInvestments']}")
                        print(f"   - 平均公开ROI: {investor_data['avgPublicRoi']}")
                        print(f"   - 投资组合项目数: {len(investor_data['portfolioProjects'])}")
                    
                except Exception as e:
                    print(f"❌ 解析第 {i+1} 个记录时出错: {str(e)}")
                    if self.debug:
                        print(f"🔍 错误记录: {item}")
                    continue
            
            print(f"✅ 成功解析 {len(investors)} 个投资者数据")
            return investors
            
        except Exception as e:
            print(f"❌ 解析API响应时出错: {str(e)}")
            if self.debug:
                import traceback
                print(f"📋 错误堆栈: {traceback.format_exc()}")
            return investors

    def _determine_tier(self, rating):
        """根据评分确定投资者等级"""
        if rating is None:
            return 'Unknown'
        elif rating >= 4:
            return 'S'
        elif rating >= 3:
            return 'A'
        elif rating >= 2:
            return 'B'
        elif rating >= 1:
            return 'C'
        else:
            return 'D'

    def _save_page_to_database(self, investors_data, page_num):
        """保存单页数据到MongoDB数据库"""
        try:
            if not investors_data:
                print(f"⚠️  第 {page_num} 页没有数据可保存")
                return 0
            
            print(f"🔄 开始转换第 {page_num} 页的 {len(investors_data)} 条数据...")
            
            # 转换为InvestorData对象
            investor_objects = []
            conversion_errors = 0
            
            for i, item in enumerate(investors_data, 1):
                try:
                    investor_obj = InvestorData(item)
                    mongo_dict = investor_obj.to_mongo_dict()
                    investor_objects.append(mongo_dict)
                    
                    if self.debug and i <= 2:
                        print(f"✅ 第{i}个投资者数据转换成功: {mongo_dict.get('name', 'N/A')}")
                        print(f"   - ID: {mongo_dict.get('investor_id', 'N/A')}")
                        print(f"   - 排名: {mongo_dict.get('rank', 'N/A')}")
                        print(f"   - 总投资数: {mongo_dict.get('total_investments', 'N/A')}")
                except Exception as e:
                    conversion_errors += 1
                    print(f"⚠️  第{i}个数据转换失败: {e}")
                    if self.debug:
                        print(f"🔍 转换失败的数据: {item}")
                    continue
            
            if conversion_errors > 0:
                print(f"⚠️  数据转换完成: {len(investor_objects)} 成功, {conversion_errors} 失败")
            
            if not investor_objects:
                print(f"❌ 第 {page_num} 页没有有效数据可保存")
                return 0
            
            # 保存到数据库
            saved_count = 0
            update_count = 0
            insert_count = 0
            
            print(f"💾 正在保存 {len(investor_objects)} 条数据到数据库...")
            
            for i, investor_data in enumerate(investor_objects, 1):
                try:
                    # 使用upsert方式，根据investor_id或name更新或插入
                    query = {}
                    if investor_data.get('investor_id'):
                        query['investor_id'] = investor_data['investor_id']
                    else:
                        query['name'] = investor_data['name']
                    
                    result = self.investor_manager.collection.update_one(
                        query,
                        {'$set': investor_data},
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        insert_count += 1
                        saved_count += 1
                        if self.debug and i <= 2:
                            print(f"➕ 新插入: {investor_data['name']}")
                    elif result.modified_count > 0:
                        update_count += 1
                        saved_count += 1
                        if self.debug and i <= 2:
                            print(f"🔄 已更新: {investor_data['name']}")
                    elif self.debug and i <= 2:
                        print(f"➖ 无变化: {investor_data['name']}")
                except Exception as e:
                    print(f"❌ 保存投资者数据失败 {investor_data.get('name', 'Unknown')}: {e}")
                    if self.debug:
                        print(f"🔍 保存失败的数据: {investor_data}")
            
            print(f"✅ 第 {page_num} 页数据库保存完成: {saved_count}/{len(investor_objects)} 条记录")
            print(f"📊 保存详情: {insert_count} 新增, {update_count} 更新")
            return saved_count
        except Exception as e:
            print(f"❌ 第 {page_num} 页保存数据到数据库时出错: {e}")
            if self.debug:
                import traceback
                print(f"📋 错误堆栈: {traceback.format_exc()}")
            return 0
    
    def scrape_all_investors_data(self, max_pages=370, save_csv=True, save_db=True):
        """爬取所有投资者数据的主方法"""
        print(f"🚀 开始爬取 DropsTab 投资者数据 (最多 {max_pages} 页)")
        print(f"💾 实时保存模式: 每页数据将立即保存到数据库")
        
        if self.debug:
            print(f"📋 爬取配置:")
            print(f"   - 最大页数: {max_pages}")
            print(f"   - 保存CSV: {save_csv}")
            print(f"   - 实时保存到数据库: 启用")
            print(f"   - 调试模式: {self.debug}")
        
        start_time = time.time()
        # 注意：现在数据在爬取过程中已经保存到数据库了
        investors_data = self.scrape_investors_data(max_pages=max_pages)
        scrape_time = time.time() - start_time
        
        print(f"\n📊 爬取完成，共获取 {len(investors_data)} 个投资者数据")
        print(f"💾 所有数据已实时保存到MongoDB数据库")
        
        if self.debug:
            print(f"⏱️  总爬取耗时: {scrape_time:.2f}秒")
            print(f"📈 平均每个投资者耗时: {scrape_time/len(investors_data):.3f}秒" if investors_data else "")
        
        # 保存到CSV文件（可选）
        if save_csv and investors_data:
            print(f"💾 开始保存CSV文件...")
            self.save_to_csv(investors_data)
        
        print(f"🎉 所有操作完成!")
        
        return investors_data

    def _parse_investors_page(self, soup):
        """解析投资者页面数据"""
        investors = []
        
        try:
            # 查找投资者表格
            table = soup.find('table', class_='table table-striped table-hover')
            if not table:
                print("❌ 未找到投资者表格")
                return investors
            
            tbody = table.find('tbody')
            if not tbody:
                print("❌ 未找到表格主体")
                return investors
            
            rows = tbody.find_all('tr')
            print(f"📊 找到 {len(rows)} 行投资者数据")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 6:
                        print(f"⚠️ 第 {i+1} 行数据不完整，跳过")
                        continue
                    
                    # 解析投资者名称
                    name_cell = cells[0]
                    name_link = name_cell.find('a')
                    name = name_link.text.strip() if name_link else name_cell.text.strip()
                    
                    # 解析投资者类型
                    type_cell = cells[1]
                    investor_type = type_cell.text.strip()
                    
                    # 解析成功率
                    success_rate_cell = cells[2]
                    success_rate_text = success_rate_cell.text.strip()
                    success_rate = None
                    if success_rate_text and success_rate_text != '-':
                        try:
                            success_rate = float(success_rate_text.replace('%', ''))
                        except ValueError:
                            print(f"⚠️ 无法解析成功率: {success_rate_text}")
                    
                    # 解析倍数信息
                    multiplier_cell = cells[3]
                    multiplier_text = multiplier_cell.text.strip()
                    avg_multiplier = None
                    if multiplier_text and multiplier_text != '-':
                        try:
                            avg_multiplier = float(multiplier_text.replace('x', ''))
                        except ValueError:
                            print(f"⚠️ 无法解析平均倍数: {multiplier_text}")
                    
                    # 解析等级
                    tier_cell = cells[4]
                    tier = tier_cell.text.strip()
                    
                    # 解析最后活动时间
                    last_activity_cell = cells[5]
                    last_activity = last_activity_cell.text.strip()
                    
                    investor_data = {
                        'name': name,
                        'type': investor_type,
                        'success_rate': success_rate,
                        'avg_multiplier': avg_multiplier,
                        'tier': tier,
                        'last_activity': last_activity,
                        'scraped_at': datetime.utcnow()
                    }
                    
                    investors.append(investor_data)
                    
                    if (i + 1) % 10 == 0:
                        print(f"📈 已处理 {i + 1} 个投资者")
                    
                except Exception as e:
                    print(f"❌ 解析第 {i+1} 行时出错: {str(e)}")
                    continue
            
            print(f"✅ 成功解析 {len(investors)} 个投资者数据")
            return investors
            
        except Exception as e:
            print(f"❌ 解析投资者页面时出错: {str(e)}")
            
# 使用示例和测试代码
if __name__ == "__main__":
    # 创建爬虫实例
    scraper = DropstabScraper(page_delay_min=10, page_delay_max=20.0)
    
    # 测试爬取前几页
    print("🧪 测试模式：爬取前3页数据")
    test_data = scraper.scrape_all_investors_data(max_pages=3, save_csv=True, save_db=True)
    
    # 显示前5个投资者信息
    if test_data:
        print("\n📋 前5个投资者信息:")
        for i, investor in enumerate(test_data[:5], 1):
            print(f"{i}. {investor.get('投资者名称', 'N/A')} - {investor.get('类型', 'N/A')} - 成功率: {investor.get('成功率', 'N/A')}")
    
    # 如果需要爬取全部数据，取消下面的注释
    # print("\n🚀 开始爬取全部数据...")
    # full_data = scraper.scrape_all_investors_data(max_pages=370, save_csv=True, save_db=True)


    