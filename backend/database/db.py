#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB 数据库连接和操作
"""

from flask import current_app
from pymongo import ASCENDING, DESCENDING

def get_db():
    """获取数据库连接"""
    from ..app import mongo
    return mongo.db

def create_indexes():
    """创建数据库索引"""
    db = get_db()
    
    # 为crypto_data集合创建索引
    crypto_collection = db.crypto_data
    
    # 创建复合索引
    crypto_collection.create_index([
        ('symbol', ASCENDING),
        ('timestamp', DESCENDING)
    ])
    
    # 创建单字段索引
    crypto_collection.create_index('symbol')
    crypto_collection.create_index('timestamp')
    crypto_collection.create_index('source')
    crypto_collection.create_index('rank')
    
    # 为investor_data集合创建索引
    investor_collection = db.investor_data
    
    # 创建投资者数据索引
    investor_collection.create_index([
        ('name', ASCENDING),
        ('timestamp', DESCENDING)
    ])
    
    investor_collection.create_index('name')
    investor_collection.create_index('type')
    investor_collection.create_index('tier')
    investor_collection.create_index('timestamp')
    investor_collection.create_index('source')
    investor_collection.create_index('rank')
    
    print("MongoDB索引创建完成")

class CryptoDataManager:
    """加密货币数据管理器"""
    
    def __init__(self):
        self.collection = get_db().crypto_data
    
    def insert_crypto_data(self, data):
        """插入加密货币数据"""
        if isinstance(data, list):
            return self.collection.insert_many(data)
        else:
            return self.collection.insert_one(data)
    
    def get_latest_data(self, symbol=None, limit=100):
        """获取最新数据"""
        query = {}
        if symbol:
            query['symbol'] = symbol.upper()
        
        cursor = self.collection.find(query).sort('timestamp', DESCENDING).limit(limit)
        return list(cursor)
    
    def get_crypto_by_symbol(self, symbol):
        """根据符号获取最新的加密货币数据"""
        return self.collection.find_one(
            {'symbol': symbol.upper()},
            sort=[('timestamp', DESCENDING)]
        )
    
    def get_price_history(self, symbol, hours=24):
        """获取价格历史数据"""
        from datetime import datetime, timedelta
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        return list(self.collection.find({
            'symbol': symbol.upper(),
            'timestamp': {'$gte': start_time}
        }).sort('timestamp', ASCENDING))
    
    def get_all_symbols(self):
        """获取所有加密货币符号"""
        return self.collection.distinct('symbol')
    
    def delete_old_data(self, days=30):
        """删除旧数据"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = self.collection.delete_many({
            'timestamp': {'$lt': cutoff_date}
        })
        return result.deleted_count
    
    def delete_all_data(self):
        """删除所有加密货币数据"""
        result = self.collection.delete_many({})
        print(f"已删除 {result.deleted_count} 条记录")
        return result.deleted_count
    
    def delete_by_symbol(self, symbol):
        """删除指定符号的所有数据"""
        result = self.collection.delete_many({'symbol': symbol.upper()})
        print(f"已删除 {symbol.upper()} 的 {result.deleted_count} 条记录")
        return result.deleted_count
    
    def clear_collection(self):
        """清空整个集合"""
        result = self.collection.drop()
        print("crypto_data 集合已清空")
        return result
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            # 尝试执行一个简单的查询
            self.collection.find_one()
            return True
        except Exception as e:
            print(f"数据库连接测试失败: {e}")
            return False

class InvestorDataManager:
    """投资者数据管理器"""
    
    def __init__(self):
        self.collection = get_db().investor_data
    
    def insert_investor_data(self, data):
        """插入投资者数据"""
        if isinstance(data, list):
            return self.collection.insert_many(data)
        else:
            return self.collection.insert_one(data)
    
    def get_latest_data(self, name=None, limit=100):
        """获取最新投资者数据"""
        query = {}
        if name:
            query['name'] = name
        
        cursor = self.collection.find(query).sort('timestamp', DESCENDING).limit(limit)
        return list(cursor)
    
    def get_investor_by_name(self, name):
        """根据名称获取投资者数据"""
        return self.collection.find_one({'name': name})
    
    def get_investors_by_type(self, investor_type, limit=100):
        """根据类型获取投资者数据"""
        cursor = self.collection.find({'type': investor_type}).sort('timestamp', DESCENDING).limit(limit)
        return list(cursor)
    
    def get_all_names(self):
        """获取所有投资者名称"""
        return self.collection.distinct('name')
    
    def delete_old_data(self, days=30):
        """删除旧数据"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        result = self.collection.delete_many({'timestamp': {'$lt': cutoff_date}})
        return result.deleted_count
    
    def delete_all_data(self):
        """删除所有数据"""
        result = self.collection.delete_many({})
        return result.deleted_count
    
    def delete_by_name(self, name):
        """根据名称删除投资者数据"""
        result = self.collection.delete_many({'name': name})
        return result.deleted_count
    
    def clear_collection(self):
        """清空集合"""
        self.collection.drop()
        return True
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            # 尝试执行一个简单的查询
            self.collection.find_one()
            return True
        except Exception as e:
            print(f"投资者数据库连接测试失败: {e}")
            return False
    
    def get_statistics(self):
        """获取投资者数据统计信息"""
        try:
            total_count = self.collection.count_documents({})
            
            # 按类型统计
            type_stats = list(self.collection.aggregate([
                {'$group': {'_id': '$type', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]))
            
            # 按层级统计
            tier_stats = list(self.collection.aggregate([
                {'$group': {'_id': '$tier', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]))
            
            return {
                'total_count': total_count,
                'type_distribution': type_stats,
                'tier_distribution': tier_stats
            }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return None