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
# 在文件顶部添加导入
from ..database.db import InvestorDataManager
from ..models.investor import InvestorData

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

# 独立爬虫控制API
@api_bp.route('/scraper/<scraper_type>/status', methods=['GET'])
def get_scraper_status_by_type(scraper_type):
    """获取特定爬虫状态"""
    try:
        jobs = scheduler.get_jobs()
        active_jobs = [job for job in jobs if scraper_type in job.id.lower()]
        
        is_running = len(active_jobs) > 0
        next_run = None
        
        if is_running and active_jobs:
            next_run = active_jobs[0].next_run_time.isoformat() if active_jobs[0].next_run_time else None
        
        return jsonify({
            'success': True,
            'data': {
                'running': is_running,
                'active_jobs': len(active_jobs),
                'next_run': next_run,
                'scraper_type': scraper_type
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/scraper/<scraper_type>/start', methods=['POST'])
def start_scraper_by_type(scraper_type):
    """启动特定爬虫"""
    try:
        from flask import current_app
        
        # 检查是否已经在运行
        jobs = scheduler.get_jobs()
        active_jobs = [job for job in jobs if scraper_type in job.id.lower()]
        
        if active_jobs:
            return jsonify({
                'success': False,
                'message': f'{scraper_type} 爬虫已经在运行中'
            })
        
        if scraper_type == 'coingecko':
            from ..scrapers.scheduler import start_crypto_scraping_jobs
            start_crypto_scraping_jobs(current_app)
        elif scraper_type == 'dropstab':
            from ..scrapers.scheduler import start_investor_scraping_jobs
            start_investor_scraping_jobs(current_app)
        else:
            return jsonify({
                'success': False,
                'error': f'未知的爬虫类型: {scraper_type}'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'{scraper_type} 爬虫已启动'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/scraper/<scraper_type>/stop', methods=['POST'])
def stop_scraper_by_type(scraper_type):
    """停止特定爬虫"""
    try:
        from ..scrapers.scheduler import set_scraper_stop_flag
        
        # 设置停止标志
        set_scraper_stop_flag(scraper_type, True)
        
        # 移除特定爬虫相关任务
        jobs = scheduler.get_jobs()
        removed_count = 0
        
        for job in jobs:
            if scraper_type in job.id.lower():
                scheduler.remove_job(job.id)
                removed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'{scraper_type} 爬虫停止信号已发送，移除了 {removed_count} 个任务'
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

# 添加投资者数据相关API接口
@api_bp.route('/investors', methods=['GET'])
def get_investors():
    """获取投资者数据"""
    try:
        limit = request.args.get('limit', 100, type=int)
        investor_type = request.args.get('type')
        
        investor_manager = InvestorDataManager()
        
        if investor_type:
            data = investor_manager.get_investors_by_type(investor_type, limit=limit)
        else:
            data = investor_manager.get_latest_data(limit=limit)
        
        # 转换为InvestorData对象并序列化
        investors = []
        for item in data:
            investor = InvestorData.from_dict(item)
            investors.append(investor.to_dict())
        
        return jsonify({
            'success': True,
            'data': investors,
            'count': len(investors)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/investors/stats', methods=['GET'])
def get_investor_stats():
    """获取投资者统计信息"""
    try:
        investor_manager = InvestorDataManager()
        stats = investor_manager.get_statistics()
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/investors/<name>', methods=['GET'])
def get_investor_by_name(name):
    """根据名称获取投资者信息"""
    try:
        investor_manager = InvestorDataManager()
        data = investor_manager.get_investor_by_name(name)
        
        if data:
            investor = InvestorData.from_dict(data)
            return jsonify({
                'success': True,
                'data': investor.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': '投资者不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500