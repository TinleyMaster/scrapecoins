#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoinGecko API 爬虫
"""

import requests
import time
import random
from typing import List, Dict, Any
from .base_scraper import BaseScraper

class CoinGeckoScraper(BaseScraper):
    """CoinGecko API 爬虫类"""
    
    def __init__(self, page_delay_min=2.0, page_delay_max=5.0):
        super().__init__('coingecko', 'https://api.coingecko.com/api/v3')
        self.page_delay_min = page_delay_min
        self.page_delay_max = page_delay_max
        self.base_rate_limit_delay = 1.5  # 基础延迟
    
    def _get_random_delay(self) -> float:
        """获取随机延迟时间"""
        return random.uniform(self.page_delay_min, self.page_delay_max)
    
    def _smart_delay(self, page_num: int, total_pages: int):
        """智能延迟策略"""
        # 基础随机延迟
        base_delay = self._get_random_delay()
        
        # 根据页数调整延迟（越往后延迟越长，避免被限制）
        page_factor = 1 + (page_num - 1) * 0.1  # 每页增加10%延迟
        
        # 添加一些随机波动
        random_factor = random.uniform(0.8, 1.2)
        
        final_delay = base_delay * page_factor * random_factor
        
        print(f"页面 {page_num}/{total_pages} 延迟: {final_delay:.2f}秒")
        time.sleep(final_delay)
    
    def scrape_all_crypto_data(self, per_page=250, max_pages=20) -> List[Dict[str, Any]]:
        """爬取所有加密货币数据（带随机延迟）"""
        all_data = []
        
        try:
            print(f"开始爬取所有加密货币数据，每页{per_page}个，最多{max_pages}页")
            print(f"使用随机延迟: {self.page_delay_min}-{self.page_delay_max}秒")
            
            for page in range(1, max_pages + 1):
                print(f"正在爬取第 {page}/{max_pages} 页...")
                
                url = f"{self.base_url}/coins/markets"
                params = {
                    'vs_currency': 'usd',
                    'order': 'market_cap_desc',
                    'per_page': per_page,
                    'page': page,
                    'sparkline': False,
                    'price_change_percentage': '24h,7d,30d'
                }
                
                try:
                    response = self._make_request(url, params)
                    data = response.json()
                    
                    if not data or len(data) == 0:
                        print(f"第{page}页没有更多数据，停止爬取")
                        break
                    
                    # 处理数据格式
                    page_data = []
                    for item in data:
                        processed_item = {
                            'id': item.get('id'),
                            'symbol': item.get('symbol', '').upper(),
                            'name': item.get('name'),
                            'current_price': item.get('current_price'),
                            'market_cap': item.get('market_cap'),
                            'market_cap_rank': item.get('market_cap_rank'),
                            'total_volume': item.get('total_volume'),
                            'price_change_24h': item.get('price_change_24h'),
                            'price_change_percentage_24h': item.get('price_change_percentage_24h'),
                            'price_change_percentage_7d': item.get('price_change_percentage_7d_in_currency'),
                            'price_change_percentage_30d': item.get('price_change_percentage_30d_in_currency'),
                            'circulating_supply': item.get('circulating_supply'),
                            'total_supply': item.get('total_supply'),
                            'max_supply': item.get('max_supply'),
                            'ath': item.get('ath'),
                            'ath_change_percentage': item.get('ath_change_percentage'),
                            'ath_date': item.get('ath_date'),
                            'atl': item.get('atl'),
                            'atl_change_percentage': item.get('atl_change_percentage'),
                            'atl_date': item.get('atl_date'),
                            'last_updated': item.get('last_updated'),
                            'image': item.get('image'),
                            'fully_diluted_valuation': item.get('fully_diluted_valuation')
                        }
                        page_data.append(processed_item)
                    
                    all_data.extend(page_data)
                    print(f"第{page}页获取 {len(page_data)} 个加密货币，累计 {len(all_data)} 个")
                    
                    # 如果这页数据少于预期，说明已经到最后一页
                    if len(data) < per_page:
                        print(f"第{page}页数据不足{per_page}个，已到最后一页")
                        break
                    
                except requests.RequestException as e:
                    print(f"第{page}页请求失败: {e}，跳过此页")
                    # 即使失败也要延迟，避免连续请求
                    if page < max_pages:
                        error_delay = random.uniform(3.0, 8.0)  # 错误时延迟更长
                        print(f"请求失败，延迟 {error_delay:.2f}秒 后继续")
                        time.sleep(error_delay)
                    continue
                
                # 智能延迟策略（最后一页不需要延迟）
                if page < max_pages:
                    self._smart_delay(page, max_pages)
            
            print(f"CoinGecko: 总共成功获取 {len(all_data)} 个加密货币数据")
            return all_data
            
        except Exception as e:
            print(f"CoinGecko 全量爬取失败: {e}")
            return all_data  # 返回已获取的数据
    
    def scrape_crypto_data(self, crypto_ids: List[str]) -> List[Dict[str, Any]]:
        """爬取指定加密货币数据（保留原方法作为备用）"""
        try:
            # 将crypto_ids转换为CoinGecko API格式
            ids_param = ','.join(crypto_ids)
            
            url = f"{self.base_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'ids': ids_param,
                'order': 'market_cap_desc',
                'per_page': 250,
                'page': 1,
                'sparkline': False,
                'price_change_percentage': '24h'
            }
            
            response = self._make_request(url, params)
            data = response.json()
            
            # 处理数据格式
            processed_data = []
            for item in data:
                processed_item = {
                    'id': item.get('id'),
                    'symbol': item.get('symbol', '').upper(),
                    'name': item.get('name'),
                    'current_price': item.get('current_price'),
                    'market_cap': item.get('market_cap'),
                    'market_cap_rank': item.get('market_cap_rank'),
                    'total_volume': item.get('total_volume'),
                    'price_change_24h': item.get('price_change_24h'),
                    'price_change_percentage_24h': item.get('price_change_percentage_24h'),
                    'circulating_supply': item.get('circulating_supply'),
                    'total_supply': item.get('total_supply'),
                    'max_supply': item.get('max_supply'),
                    'ath': item.get('ath'),
                    'ath_change_percentage': item.get('ath_change_percentage'),
                    'ath_date': item.get('ath_date'),
                    'atl': item.get('atl'),
                    'atl_change_percentage': item.get('atl_change_percentage'),
                    'atl_date': item.get('atl_date'),
                    'last_updated': item.get('last_updated')
                }
                processed_data.append(processed_item)
            
            print(f"CoinGecko: 成功获取 {len(processed_data)} 个加密货币数据")
            return processed_data
            
        except requests.RequestException as e:
            print(f"CoinGecko API 请求失败: {e}")
            return []
        except Exception as e:
            print(f"CoinGecko 数据处理失败: {e}")
            return []
    
    def get_supported_cryptos(self) -> List[str]:
        """获取支持的加密货币列表"""
        try:
            url = f"{self.base_url}/coins/list"
            response = self._make_request(url)
            data = response.json()
            
            # 返回所有加密货币ID
            return [coin['id'] for coin in data]
            
        except Exception as e:
            print(f"获取支持的加密货币列表失败: {e}")
            return []
    
    def get_trending_cryptos(self) -> List[Dict[str, Any]]:
        """获取热门加密货币"""
        try:
            url = f"{self.base_url}/search/trending"
            response = self._make_request(url)
            data = response.json()
            
            trending_coins = []
            for coin in data.get('coins', []):
                coin_data = coin.get('item', {})
                trending_coins.append({
                    'id': coin_data.get('id'),
                    'symbol': coin_data.get('symbol'),
                    'name': coin_data.get('name'),
                    'market_cap_rank': coin_data.get('market_cap_rank'),
                    'thumb': coin_data.get('thumb'),
                    'large': coin_data.get('large')
                })
            
            return trending_coins
            
        except Exception as e:
            print(f"获取热门加密货币失败: {e}")
            return []
    
    def get_global_data(self) -> Dict[str, Any]:
        """获取全球加密货币市场数据"""
        try:
            url = f"{self.base_url}/global"
            response = self._make_request(url)
            data = response.json()
            
            global_data = data.get('data', {})
            return {
                'active_cryptocurrencies': global_data.get('active_cryptocurrencies'),
                'upcoming_icos': global_data.get('upcoming_icos'),
                'ongoing_icos': global_data.get('ongoing_icos'),
                'ended_icos': global_data.get('ended_icos'),
                'markets': global_data.get('markets'),
                'total_market_cap': global_data.get('total_market_cap', {}).get('usd'),
                'total_volume': global_data.get('total_volume', {}).get('usd'),
                'market_cap_percentage': global_data.get('market_cap_percentage', {}),
                'market_cap_change_percentage_24h_usd': global_data.get('market_cap_change_percentage_24h_usd'),
                'updated_at': global_data.get('updated_at')
            }
            
        except Exception as e:
            print(f"获取全球市场数据失败: {e}")
            return {}