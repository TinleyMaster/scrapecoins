#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础爬虫类
"""

import requests
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..config import Config

class BaseScraper(ABC):
    """基础爬虫抽象类"""
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.last_request_time = 0
        self.rate_limit_delay = 1  # 请求间隔（秒）
    
    def _rate_limit(self):
        """实现请求频率限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict = None) -> requests.Response:
        """发送HTTP请求"""
        self._rate_limit()
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=Config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == Config.MAX_RETRIES - 1:
                    raise e
                time.sleep(2 ** attempt)  # 指数退避
    
    @abstractmethod
    def scrape_crypto_data(self, crypto_ids: List[str]) -> List[Dict[str, Any]]:
        """抽象方法：爬取加密货币数据"""
        pass
    
    @abstractmethod
    def get_supported_cryptos(self) -> List[str]:
        """抽象方法：获取支持的加密货币列表"""
        pass