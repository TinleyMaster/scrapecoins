#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 应用工厂
"""

import os
import atexit
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
from flask_pymongo import PyMongo
from apscheduler.schedulers.background import BackgroundScheduler

# 创建全局调度器实例
scheduler = BackgroundScheduler()
socketio = SocketIO(cors_allowed_origins="*")
mongo = PyMongo()

def create_app():
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    from .config import config
    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])
    
    # 初始化扩展
    socketio.init_app(app)
    mongo.init_app(app)
    
    # 注册蓝图
    from .api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 主页路由
    @app.route('/')
    def index():
        """主页"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
        return send_from_directory(frontend_dir, 'index.html')
    
    @app.route('/css/<path:filename>')
    def css_files(filename):
        """服务CSS文件"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
        return send_from_directory(os.path.join(frontend_dir, 'css'), filename)
    
    @app.route('/js/<path:filename>')
    def js_files(filename):
        """服务JavaScript文件"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
        return send_from_directory(os.path.join(frontend_dir, 'js'), filename)
    
    # 初始化数据库索引
    with app.app_context():
        from .database.db import create_indexes
        create_indexes()
    
    # 启动调度器但不自动启动爬虫任务
    if not scheduler.running:
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
    
    return app