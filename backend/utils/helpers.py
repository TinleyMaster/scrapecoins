#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数
"""

from typing import Any, Dict, Optional
from decimal import Decimal, InvalidOperation

def format_number(value: Any, decimal_places: int = 2) -> Optional[float]:
    """格式化数字，处理None值和无效数据"""
    if value is None:
        return None
    
    try:
        if isinstance(value, str):
            # 移除逗号和其他非数字字符
            cleaned_value = value.replace(',', '').replace('$', '').strip()
            if not cleaned_value or cleaned_value == '-':
                return None
            value = float(cleaned_value)
        
        return round(float(value), decimal_places)
    except (ValueError, TypeError, InvalidOperation):
        return None

def calculate_percentage_change(old_value: float, new_value: float) -> Optional[float]:
    """计算百分比变化"""
    if old_value is None or new_value is None or old_value == 0:
        return None
    
    try:
        change = ((new_value - old_value) / old_value) * 100
        return round(change, 2)
    except (ZeroDivisionError, TypeError):
        return None

def validate_crypto_data(data: Dict[str, Any]) -> bool:
    """验证加密货币数据的完整性"""
    required_fields = ['symbol', 'name', 'current_price']
    
    for field in required_fields:
        if field not in data or data[field] is None:
            return False
    
    # 验证价格是否为有效数字
    try:
        price = float(data['current_price'])
        if price <= 0:
            return False
    except (ValueError, TypeError):
        return False
    
    return True

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """安全的浮点数转换"""
    if value is None:
        return default
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def format_market_cap(market_cap: Optional[float]) -> str:
    """格式化市值显示"""
    if market_cap is None:
        return "N/A"
    
    if market_cap >= 1e12:
        return f"${market_cap/1e12:.2f}T"
    elif market_cap >= 1e9:
        return f"${market_cap/1e9:.2f}B"
    elif market_cap >= 1e6:
        return f"${market_cap/1e6:.2f}M"
    elif market_cap >= 1e3:
        return f"${market_cap/1e3:.2f}K"
    else:
        return f"${market_cap:.2f}"

def format_volume(volume: Optional[float]) -> str:
    """格式化交易量显示"""
    return format_market_cap(volume)  # 使用相同的格式化逻辑