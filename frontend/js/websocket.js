// WebSocket 连接管理
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.statusElement = document.getElementById('connection-status');
    }

    connect() {
        try {
            // 检查Socket.IO是否已加载
            if (typeof io === 'undefined') {
                console.error('Socket.IO库未加载，请检查网络连接或CDN可用性');
                this.updateStatus('disconnected');
                // 尝试动态加载Socket.IO
                this.loadSocketIO();
                return;
            }
            
            this.socket = io();
            this.setupEventListeners();
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateStatus('disconnected');
        }
    }

    loadSocketIO() {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/socket.io-client@4.7.2/dist/socket.io.min.js';
        script.onload = () => {
            console.log('Socket.IO库动态加载成功');
            this.connect();
        };
        script.onerror = () => {
            console.error('Socket.IO库动态加载失败');
            this.updateStatus('disconnected');
        };
        document.head.appendChild(script);
    }

    setupEventListeners() {
        this.socket.on('connect', () => {
            console.log('WebSocket连接成功');
            this.reconnectAttempts = 0;
            this.updateStatus('connected');
        });

        this.socket.on('disconnect', () => {
            console.log('WebSocket连接断开');
            this.updateStatus('disconnected');
            this.attemptReconnect();
        });

        this.socket.on('crypto_update', (data) => {
            console.log('收到加密货币数据更新:', data);
            this.handleCryptoUpdate(data);
        });

        // 添加日志事件监听
        this.socket.on('scraper_log', (data) => {
            console.log('收到爬虫日志:', data);
            this.handleScraperLog(data);
        });

        this.socket.on('connect_error', (error) => {
            console.error('WebSocket连接错误:', error);
            this.updateStatus('disconnected');
            this.attemptReconnect();
        });
    }

    handleCryptoUpdate(data) {
        if (data && data.data) {
            // 直接更新应用数据
            if (window.cryptoApp) {
                window.cryptoApp.currentData = data.data;
                window.cryptoApp.updateDisplay();
            }
        }
    }

    // 新增：处理爬虫日志
    handleScraperLog(data) {
        if (window.cryptoApp) {
            window.cryptoApp.addLogMessage(data.message, data.type || 'info', data.timestamp);
        }
    }

    updateStatus(status) {
        if (!this.statusElement) return;

        this.statusElement.className = `status-indicator ${status}`;
        
        switch (status) {
            case 'connected':
                this.statusElement.textContent = '已连接';
                break;
            case 'connecting':
                this.statusElement.textContent = '连接中...';
                break;
            case 'disconnected':
                this.statusElement.textContent = '连接断开';
                break;
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.updateStatus('connecting');
            
            setTimeout(() => {
                console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
}

// 全局WebSocket管理器实例
let wsManager;

// 页面加载完成后初始化WebSocket连接
document.addEventListener('DOMContentLoaded', () => {
    wsManager = new WebSocketManager();
    wsManager.connect();
});

// 页面卸载时断开连接
window.addEventListener('beforeunload', () => {
    if (wsManager) {
        wsManager.disconnect();
    }
});