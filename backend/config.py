#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目配置文件
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """基础配置类"""
    
    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # MongoDB 配置
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/crypto_db')
    
    # API 配置
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 5000))
    
    # 爬虫配置 - 随机间隔
    SCRAPE_INTERVAL_MIN = int(os.getenv('SCRAPE_INTERVAL_MIN', 600))  # 最小间隔10分钟
    SCRAPE_INTERVAL_MAX = int(os.getenv('SCRAPE_INTERVAL_MAX', 1800))  # 最大间隔30分钟
    SCRAPE_INTERVAL = int(os.getenv('SCRAPE_INTERVAL', 900))  # 默认15分钟（作为备用）
    
    # 页面间随机延迟配置
    PAGE_DELAY_MIN = float(os.getenv('PAGE_DELAY_MIN', 2.0))  # 页面间最小延迟2秒
    PAGE_DELAY_MAX = float(os.getenv('PAGE_DELAY_MAX', 5.0))  # 页面间最大延迟5秒
    
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    
    # 全量爬取配置
    CRYPTO_PER_PAGE = int(os.getenv('CRYPTO_PER_PAGE', 250))  # 每页最大数量
    MAX_PAGES = int(os.getenv('MAX_PAGES', 20))  # 最大页数，可获取5000个币种
    ENABLE_FULL_SCRAPE = os.getenv('ENABLE_FULL_SCRAPE', 'true').lower() == 'true'
    
    # 备用的核心加密货币列表（API失败时使用）
    FALLBACK_CRYPTOS = [
        'bitcoin', 'ethereum', 'binancecoin', 'cardano', 
        'solana', 'polkadot', 'dogecoin', 'avalanche-2',
        'chainlink', 'polygon', 'litecoin', 'uniswap',
        'cosmos', 'algorand', 'stellar', 'vechain'
    ]
    
    # 爬取的网站配置
    SCRAPER_CONFIGS = {
        'coingecko': {
            'base_url': 'https://api.coingecko.com/api/v3',
            'enabled': True,
            'rate_limit': 50  # 每分钟请求数
        },
        'coinmarketcap': {
            'base_url': 'https://coinmarketcap.com',
            'enabled': True,
            'rate_limit': 30
        }
    }

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}