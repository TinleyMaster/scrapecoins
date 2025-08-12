#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除 MongoDB 数据的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database.db import CryptoDataManager
from backend.app import create_app

def delete_all_crypto_data():
    """删除所有加密货币数据"""
    app = create_app()
    
    with app.app_context():
        crypto_manager = CryptoDataManager()
        
        # 获取删除前的数据量
        count_before = crypto_manager.collection.count_documents({})
        print(f"删除前共有 {count_before} 条记录")
        
        # 删除所有数据
        deleted_count = crypto_manager.delete_all_data()
        
        print(f"成功删除 {deleted_count} 条记录")
        print("数据库已清空")

if __name__ == "__main__":
    delete_all_crypto_data()