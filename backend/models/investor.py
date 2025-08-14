#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资者数据模型
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from bson import ObjectId

class InvestorData:
    """投资者数据模型"""
    
    def __init__(self, data: Dict[str, Any] = None):
        if data:
            self._id = data.get('_id')
            # 基础信息
            self.investor_id = data.get('id')
            self.name = data.get('name', '')
            self.investor_slug = data.get('investorSlug', '')
            self.logo = data.get('logo', '')
            self.image = data.get('image', '')
            self.country = data.get('country', {})
            self.venture_type = data.get('ventureType', '')
            self.rank = data.get('rank')
            self.rating = data.get('rating')
            self.tier = data.get('tier', '')
            self.lead = data.get('lead', False)
            self.description = data.get('description', '')
            
            # 社交媒体和链接
            self.twitter_url = data.get('twitterUrl', '')
            self.links = data.get('links', [])
            self.twitter_score = data.get('twitterScore')
            
            # 投资统计
            self.total_investments = data.get('totalInvestments')
            self.lead_investments = data.get('leadInvestments')
            self.rounds_per_year = data.get('roundsPerYear')
            self.public_sales_count = data.get('publicSalesCount')
            self.last_round_date = data.get('lastRoundDate')
            
            # ROI数据
            self.avg_public_roi = data.get('avgPublicRoi', {})
            self.avg_private_roi = data.get('avgPrivateRoi', {})
            
            # 币安上市数据
            self.binance_listed = data.get('binanceListed', {})
            
            # 投资分布
            self.rounds_distribution = data.get('roundsDistribution', {})
            
            # 投资组合项目
            self.portfolio_projects = data.get('portfolioProjects', [])
            
            # 销售ID
            self.sale_ids = data.get('saleIds', [])
            
            # 元数据
            self.source = data.get('source', 'icodrops_api')
            self.scraped_at = data.get('scraped_at', datetime.utcnow())
            self.timestamp = data.get('timestamp', datetime.utcnow())
            
            # 兼容旧字段
            self.type = data.get('type', '') or self.venture_type
            self.success_rate = data.get('success_rate', '')
            self.success_rate_numeric = data.get('success_rate_numeric')
            self.avg_return = data.get('avg_return', '')
            self.avg_return_numeric = data.get('avg_return_numeric')
            self.median_return = data.get('median_return', '')
            self.median_return_numeric = data.get('median_return_numeric')
            self.investments_count = data.get('investments_count', '') or self.total_investments
            self.investments_count_numeric = data.get('investments_count_numeric') or self.total_investments
            self.last_investment = data.get('last_investment', '')
            self.days_ago = data.get('days_ago', '')
        else:
            # 初始化默认值
            self._id = None
            self.investor_id = None
            self.name = ''
            self.investor_slug = ''
            self.logo = ''
            self.image = ''
            self.country = {}
            self.venture_type = ''
            self.rank = None
            self.rating = None
            self.tier = ''
            self.lead = False
            self.description = ''
            self.twitter_url = ''
            self.links = []
            self.twitter_score = None
            self.total_investments = None
            self.lead_investments = None
            self.rounds_per_year = None
            self.public_sales_count = None
            self.last_round_date = None
            self.avg_public_roi = {}
            self.avg_private_roi = {}
            self.binance_listed = {}
            self.rounds_distribution = {}
            self.portfolio_projects = []
            self.sale_ids = []
            self.source = 'icodrops_api'
            self.scraped_at = datetime.utcnow()
            self.timestamp = datetime.utcnow()
            # 兼容旧字段
            self.type = ''
            self.success_rate = ''
            self.success_rate_numeric = None
            self.avg_return = ''
            self.avg_return_numeric = None
            self.median_return = ''
            self.median_return_numeric = None
            self.investments_count = ''
            self.investments_count_numeric = None
            self.last_investment = ''
            self.days_ago = ''
    
    def to_mongo_dict(self) -> Dict[str, Any]:
        """转换为MongoDB兼容的字典格式"""
        data = {
            # 基础信息
            'investor_id': self.investor_id,
            'name': self.name,
            'investor_slug': self.investor_slug,
            'logo': self.logo,
            'image': self.image,
            'country': self.country,
            'venture_type': self.venture_type,
            'rank': self.rank,
            'rating': self.rating,
            'tier': self.tier,
            'lead': self.lead,
            'description': self.description,
            
            # 社交媒体和链接
            'twitter_url': self.twitter_url,
            'links': self.links,
            'twitter_score': self.twitter_score,
            
            # 投资统计
            'total_investments': self.total_investments,
            'lead_investments': self.lead_investments,
            'rounds_per_year': self.rounds_per_year,
            'public_sales_count': self.public_sales_count,
            'last_round_date': self.last_round_date,
            
            # ROI数据
            'avg_public_roi': self.avg_public_roi,
            'avg_private_roi': self.avg_private_roi,
            
            # 币安上市数据
            'binance_listed': self.binance_listed,
            
            # 投资分布
            'rounds_distribution': self.rounds_distribution,
            
            # 投资组合项目
            'portfolio_projects': self.portfolio_projects,
            
            # 销售ID
            'sale_ids': self.sale_ids,
            
            # 元数据
            'source': self.source,
            'scraped_at': self.scraped_at,
            'timestamp': self.timestamp,
            
            # 兼容旧字段
            'type': self.type,
            'success_rate': self.success_rate,
            'success_rate_numeric': self.success_rate_numeric,
            'avg_return': self.avg_return,
            'avg_return_numeric': self.avg_return_numeric,
            'median_return': self.median_return,
            'median_return_numeric': self.median_return_numeric,
            'investments_count': self.investments_count,
            'investments_count_numeric': self.investments_count_numeric,
            'last_investment': self.last_investment,
            'days_ago': self.days_ago
        }
        
        # 移除None值
        return {k: v for k, v in data.items() if v is not None}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = self.to_mongo_dict()
        data['_id'] = self._id
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvestorData':
        """从字典创建InvestorData对象"""
        return cls(data)
    
    def __repr__(self):
        return f'<InvestorData {self.name}: {self.venture_type}, 排名: {self.rank}>'
    
    def __str__(self):
        return self.__repr__()