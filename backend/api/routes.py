#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 路由
"""

from flask import Blueprint, jsonify, request
from ..database.db import CryptoDataManager
from ..models.crypto import CryptoData
from ..app import scheduler
from datetime import datetime

api_bp = Blueprint('api', __name__)
crypto_manager = CryptoDataManager()

@api_bp.route('/cryptos', methods=['GET'])
def get_all_cryptos():
    """获取所有加密货币数据"""
    try:
        limit = request.args.get('limit', 100, type=int)
        data = crypto_manager.get_latest_data(limit=limit)
        
        # 转换为CryptoData对象并序列化
        cryptos = [CryptoData(item).to_dict() for item in data]
        
        return jsonify({
            'success': True,
            'data': cryptos,
            'count': len(cryptos)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cryptos/<symbol>', methods=['GET'])
def get_crypto_by_symbol(symbol):
    """获取特定加密货币数据"""
    try:
        data = crypto_manager.get_crypto_by_symbol(symbol)
        
        if not data:
            return jsonify({
                'success': False,
                'error': f'Cryptocurrency {symbol} not found'
            }), 404
        
        crypto = CryptoData(data).to_dict()
        
        return jsonify({
            'success': True,
            'data': crypto
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cryptos/<symbol>/history', methods=['GET'])
def get_crypto_history(symbol):
    """获取加密货币历史数据"""
    try:
        hours = request.args.get('hours', 24, type=int)
        data = crypto_manager.get_price_history(symbol, hours)
        
        # 转换为CryptoData对象并序列化
        history = [CryptoData(item).to_dict() for item in data]
        
        return jsonify({
            'success': True,
            'data': history,
            'count': len(history)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/symbols', methods=['GET'])
def get_all_symbols():
    """获取所有支持的加密货币符号"""
    try:
        symbols = crypto_manager.get_all_symbols()
        
        return jsonify({
            'success': True,
            'data': symbols,
            'count': len(symbols)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'message': 'API is running',
        'database': 'MongoDB'
    })

# 爬虫控制API接口
@api_bp.route('/scraper/status', methods=['GET'])
def get_scraper_status():
    """获取爬虫状态"""
    try:
        jobs = scheduler.get_jobs()
        active_jobs = len([job for job in jobs if 'crypto' in job.id.lower()])
        
        is_running = active_jobs > 0
        next_run = None
        
        if is_running:
            # 获取下次运行时间
            for job in jobs:
                if 'crypto' in job.id.lower():
                    next_run = job.next_run_time.isoformat() if job.next_run_time else None
                    break
        
        return jsonify({
            'success': True,
            'is_running': is_running,
            'active_jobs': active_jobs,
            'next_run': next_run,
            'message': '爬虫运行中' if is_running else '爬虫已停止'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/scraper/start', methods=['POST'])
def start_scraper():
    """启动爬虫"""
    try:
        from flask import current_app
        from ..scrapers.scheduler import start_scraping_jobs
        
        # 检查是否已经在运行
        jobs = scheduler.get_jobs()
        active_jobs = [job for job in jobs if 'crypto' in job.id.lower()]
        
        if active_jobs:
            return jsonify({
                'success': False,
                'message': '爬虫已经在运行中'
            })
        
        # 启动爬虫调度
        start_scraping_jobs(current_app)
        
        return jsonify({
            'success': True,
            'message': '爬虫已启动'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/scraper/stop', methods=['POST'])
def stop_scraper():
    """停止爬虫"""
    try:
        # 移除所有爬虫相关任务
        jobs = scheduler.get_jobs()
        removed_count = 0
        
        for job in jobs:
            if 'crypto' in job.id.lower():
                scheduler.remove_job(job.id)
                removed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'爬虫已停止，移除了 {removed_count} 个任务'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/scraper/run-once', methods=['POST'])
def run_scraper_once():
    """手动执行一次爬取"""
    try:
        from flask import current_app
        from ..scrapers.scheduler import scrape_crypto_data, set_app_instance
        
        # 设置全局应用实例
        set_app_instance(current_app)
        
        # 添加一次性爬取任务
        scheduler.add_job(
            func=scrape_crypto_data,
            trigger="date",
            run_date=datetime.now(),
            id=f'crypto_scraper_manual_{datetime.now().timestamp()}',
            name='手动加密货币数据爬取',
            replace_existing=False
        )
        
        return jsonify({
            'success': True,
            'message': '手动爬取任务已启动'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500