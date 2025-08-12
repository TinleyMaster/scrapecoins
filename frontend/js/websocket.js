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
            this.socket = io();
            this.setupEventListeners();
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateStatus('disconnected');
        }
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

        this.socket.on('connect_error', (error) => {
            console.error('WebSocket连接错误:', error);
            this.updateStatus('disconnected');
            this.attemptReconnect();
        });
    }

    handleCryptoUpdate(data) {
        if (data && data.data) {
            // 更新加密货币卡片
            updateCryptoCards(data.data);
            
            // 更新图表
            if (window.priceChart) {
                updatePriceChart(data.data);
            }
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