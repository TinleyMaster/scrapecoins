#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密货币爬虫项目启动文件
"""

from backend.app import create_app, socketio
from backend.config import Config

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=8000)