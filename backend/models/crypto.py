#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密货币数据模型
"""

from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId

class CryptoData:
    """加密货币数据模型"""
    
    def __init__(self, data: Dict[str, Any] = None):
        if data:
            self._id = data.get('_id')
            self.id = data.get('id', '')  # CoinGecko ID
            self.symbol = data.get('symbol', '').upper()
            self.name = data.get('name', '')
            self.price_usd = float(data.get('price_usd', 0))
            self.price_change_24h = data.get('price_change_24h')
            self.price_change_percentage_24h = data.get('price_change_percentage_24h')
            self.price_change_percentage_7d = data.get('price_change_percentage_7d')
            self.price_change_percentage_30d = data.get('price_change_percentage_30d')
            self.market_cap = data.get('market_cap')
            self.volume_24h = data.get('volume_24h')
            self.circulating_supply = data.get('circulating_supply')
            self.total_supply = data.get('total_supply')
            self.max_supply = data.get('max_supply')
            self.rank = data.get('rank')
            self.ath = data.get('ath')
            self.ath_change_percentage = data.get('ath_change_percentage')
            self.ath_date = data.get('ath_date')  # 新增
            self.atl = data.get('atl')  # 新增
            self.atl_change_percentage = data.get('atl_change_percentage')  # 新增
            self.atl_date = data.get('atl_date')  # 新增
            self.last_updated = data.get('last_updated')  # 新增
            self.image = data.get('image')  # 新增
            self.fully_diluted_valuation = data.get('fully_diluted_valuation')  # 新增
            self.source = data.get('source', '')
            self.timestamp = data.get('timestamp', datetime.utcnow())
        else:
            self._id = None
            self.id = ''
            self.symbol = ''
            self.name = ''
            self.price_usd = 0.0
            self.price_change_24h = None
            self.price_change_percentage_24h = None
            self.price_change_percentage_7d = None
            self.price_change_percentage_30d = None
            self.market_cap = None
            self.volume_24h = None
            self.circulating_supply = None
            self.total_supply = None
            self.max_supply = None
            self.rank = None
            self.ath = None
            self.ath_change_percentage = None
            self.ath_date = None
            self.atl = None
            self.atl_change_percentage = None
            self.atl_date = None
            self.last_updated = None
            self.image = None
            self.fully_diluted_valuation = None
            self.source = ''
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            '_id': str(self._id) if self._id else None,
            'symbol': self.symbol,
            'name': self.name,
            'price_usd': self.price_usd,
            'price_change_24h': self.price_change_24h,
            'price_change_percentage_24h': self.price_change_percentage_24h,
            'market_cap': self.market_cap,
            'volume_24h': self.volume_24h,
            'circulating_supply': self.circulating_supply,
            'total_supply': self.total_supply,
            'rank': self.rank,
            'source': self.source,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp
        }
    
    def to_mongo_dict(self) -> Dict[str, Any]:
        """转换为MongoDB存储格式"""
        data = {
            'id': self.id,
            'symbol': self.symbol or 'UNKNOWN',
            'name': self.name or self.symbol or 'Unknown',
            'price_usd': self.price_usd or 0,
            'price_change_24h': self.price_change_24h,
            'price_change_percentage_24h': self.price_change_percentage_24h,
            'price_change_percentage_7d': self.price_change_percentage_7d,
            'price_change_percentage_30d': self.price_change_percentage_30d,
            'market_cap': self.market_cap,
            'volume_24h': self.volume_24h,
            'circulating_supply': self.circulating_supply,
            'total_supply': self.total_supply,
            'max_supply': self.max_supply,
            'rank': self.rank,
            'ath': self.ath,
            'ath_change_percentage': self.ath_change_percentage,
            'ath_date': self.ath_date,
            'atl': self.atl,
            'atl_change_percentage': self.atl_change_percentage,
            'atl_date': self.atl_date,
            'last_updated': self.last_updated,
            'image': self.image,
            'fully_diluted_valuation': self.fully_diluted_valuation,
            'source': self.source or 'coingecko',
            'timestamp': self.timestamp if isinstance(self.timestamp, datetime) else datetime.utcnow()
        }
        
        # 移除 None 值，但保留必要字段
        return {k: v for k, v in data.items() if k in ['id', 'symbol', 'name', 'price_usd', 'source', 'timestamp'] or v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CryptoData':
        """从字典创建实例"""
        return cls(data)
    
    def __repr__(self):
        return f'<CryptoData {self.symbol}: ${self.price_usd}>'