// 主要的前端逻辑
class CryptoApp {
    constructor() {
        this.cryptoGrid = document.getElementById('crypto-grid');
        this.tableContainer = document.getElementById('table-container');
        this.tableBody = document.getElementById('crypto-table-body');
        this.priceChart = null;
        this.chartData = {
            labels: [],
            datasets: []
        };
        this.currentView = 'card';
        this.currentData = [];
        this.sortColumn = 'rank';
        this.sortDirection = 'asc';
        this.scraperStatus = null;
        this.init();
    }

    async init() {
        try {
            // 初始化图表
            this.initChart();
            
            // 设置事件监听器
            this.setupEventListeners();
            
            // 加载初始数据
            await this.loadInitialData();
            
            // 设置定时刷新
            this.setupAutoRefresh();
        } catch (error) {
            console.error('应用初始化失败:', error);
            this.showError('应用初始化失败，请刷新页面重试');
        }
    }

    setupEventListeners() {
        // 只保留表格视图按钮（如果需要的话）
        const tableViewBtn = document.getElementById('table-view-btn');
        if (tableViewBtn) {
            tableViewBtn.addEventListener('click', () => {
                this.switchView('table');
            });
        }
        
        // 爬虫控制按钮
        const scraperStatusBtn = document.getElementById('scraper-status-btn');
        if (scraperStatusBtn) {
            scraperStatusBtn.addEventListener('click', () => {
                this.checkScraperStatus();
            });
        }
        
        const startScraperBtn = document.getElementById('start-scraper-btn');
        if (startScraperBtn) {
            startScraperBtn.addEventListener('click', () => {
                this.startScraper();
            });
        }
        
        const stopScraperBtn = document.getElementById('stop-scraper-btn');
        if (stopScraperBtn) {
            stopScraperBtn.addEventListener('click', () => {
                this.stopScraper();
            });
        }
        
        const runOnceBtn = document.getElementById('run-once-btn');
        if (runOnceBtn) {
            runOnceBtn.addEventListener('click', () => {
                this.runScraperOnce();
            });
        }
        
        // 导出按钮
        const exportCsvBtn = document.getElementById('export-csv-btn');
        if (exportCsvBtn) {
            exportCsvBtn.addEventListener('click', () => {
                this.exportData('csv');
            });
        }
        
        const exportJsonBtn = document.getElementById('export-json-btn');
        if (exportJsonBtn) {
            exportJsonBtn.addEventListener('click', () => {
                this.exportData('json');
            });
        }
        
        // 表格排序
        const sortableHeaders = document.querySelectorAll('.sortable');
        sortableHeaders.forEach(header => {
            header.addEventListener('click', () => {
                const column = header.dataset.sort;
                this.sortTable(column);
            });
        });
    }

    updateDisplay() {
        this.updateCryptoTable(this.currentData);
    }

    switchView(viewType) {
        this.currentView = viewType;
        
        // 更新按钮状态
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (viewType === 'card') {
            document.getElementById('card-view-btn').classList.add('active');
            this.cryptoGrid.style.display = 'grid';
            this.tableContainer.style.display = 'none';
        } else {
            document.getElementById('table-view-btn').classList.add('active');
            this.cryptoGrid.style.display = 'none';
            this.tableContainer.style.display = 'block';
        }
    }

    async loadInitialData() {
        try {
            const response = await fetch('/api/cryptos?limit=100');
            const data = await response.json();
            
            if (data.success && data.data) {
                this.currentData = data.data;
                this.updateDisplay();
                this.updateChart(data.data);
            } else {
                throw new Error(data.error || '获取数据失败');
            }
        } catch (error) {
            console.error('加载初始数据失败:', error);
            this.showError('加载数据失败，请检查网络连接');
        }
    }

    updateDisplay() {
        if (this.currentView === 'card') {
            this.updateCryptoCards(this.currentData);
        } else {
            this.updateCryptoTable(this.currentData);
        }
    }

    updateCryptoCards(cryptoData) {
        if (!this.cryptoGrid) return;

        this.cryptoGrid.innerHTML = '';
        
        cryptoData.forEach(crypto => {
            const card = this.createCryptoCard(crypto);
            this.cryptoGrid.appendChild(card);
        });
    }

    updateCryptoTable(cryptoData) {
        if (!this.tableBody) return;

        this.tableBody.innerHTML = '';
        
        cryptoData.forEach(crypto => {
            const row = this.createTableRow(crypto);
            this.tableBody.appendChild(row);
        });
    }

    createTableRow(crypto) {
        const row = document.createElement('tr');
        
        const changeClass = crypto.price_change_percentage_24h >= 0 ? 'positive' : 'negative';
        const changeSymbol = crypto.price_change_percentage_24h >= 0 ? '+' : '';
        
        row.innerHTML = `
            <td><span class="rank-badge">#${crypto.rank || 'N/A'}</span></td>
            <td>
                <span class="crypto-name">${crypto.name}</span>
                <span class="crypto-symbol">${crypto.symbol}</span>
            </td>
            <td><strong>${crypto.symbol}</strong></td>
            <td><strong>$${this.formatPrice(crypto.price_usd)}</strong></td>
            <td>
                <span class="price-change ${changeClass}">
                    ${changeSymbol}${crypto.price_change_percentage_24h?.toFixed(2) || '0.00'}%
                </span>
            </td>
            <td>${this.formatMarketCap(crypto.market_cap)}</td>
            <td>${this.formatMarketCap(crypto.volume_24h)}</td>
            <td>${this.formatNumber(crypto.circulating_supply)}</td>
            <td><span style="text-transform: capitalize;">${crypto.source}</span></td>
            <td>${this.formatTimestamp(crypto.timestamp)}</td>
        `;
        
        return row;
    }

    createCryptoCard(crypto) {
        const card = document.createElement('div');
        card.className = 'crypto-card';
        card.setAttribute('data-symbol', crypto.symbol);

        const changeClass = crypto.price_change_percentage_24h >= 0 ? 'positive' : 'negative';
        const changeSymbol = crypto.price_change_percentage_24h >= 0 ? '+' : '';

        card.innerHTML = `
            <div class="crypto-header">
                <div class="crypto-icon">
                    ${crypto.symbol.substring(0, 2)}
                </div>
                <div class="crypto-info">
                    <h3>${crypto.name}</h3>
                    <span class="crypto-symbol">${crypto.symbol}</span>
                </div>
            </div>
            <div class="crypto-price">
                $${this.formatPrice(crypto.price_usd)}
            </div>
            <div class="crypto-change ${changeClass}">
                ${changeSymbol}${crypto.price_change_percentage_24h?.toFixed(2) || '0.00'}%
                <span style="margin-left: 8px; font-size: 0.8em; color: #666;">
                    ${changeSymbol}$${this.formatPrice(crypto.price_change_24h || 0)}
                </span>
            </div>
            <div class="crypto-details">
                <div class="detail-item">
                    <span class="detail-label">市值:</span>
                    <span>${this.formatMarketCap(crypto.market_cap)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">24h交易量:</span>
                    <span>${this.formatMarketCap(crypto.volume_24h)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">排名:</span>
                    <span>#${crypto.rank || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">数据源:</span>
                    <span>${crypto.source}</span>
                </div>
            </div>
        `;

        return card;
    }

    sortTable(column) {
        // 更新排序状态
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }
        
        // 更新表头样式
        document.querySelectorAll('.sortable').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
        });
        
        const currentTh = document.querySelector(`[data-sort="${column}"]`);
        currentTh.classList.add(`sort-${this.sortDirection}`);
        
        // 排序数据
        this.currentData.sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];
            
            // 处理数值类型
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return this.sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
            }
            
            // 处理字符串类型
            if (typeof aVal === 'string' && typeof bVal === 'string') {
                return this.sortDirection === 'asc' 
                    ? aVal.localeCompare(bVal) 
                    : bVal.localeCompare(aVal);
            }
            
            // 处理null/undefined
            if (aVal == null && bVal == null) return 0;
            if (aVal == null) return this.sortDirection === 'asc' ? 1 : -1;
            if (bVal == null) return this.sortDirection === 'asc' ? -1 : 1;
            
            return 0;
        });
        
        // 更新表格显示
        this.updateCryptoTable(this.currentData);
    }

    exportData(format) {
        if (!this.currentData || this.currentData.length === 0) {
            alert('没有可导出的数据');
            return;
        }
        
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        const filename = `crypto_data_${timestamp}`;
        
        if (format === 'csv') {
            this.exportToCSV(filename);
        } else if (format === 'json') {
            this.exportToJSON(filename);
        }
    }

    exportToCSV(filename) {
        const headers = [
            '排名', '名称', '符号', '价格(USD)', '24h变化(%)', '24h变化(USD)', 
            '市值', '24h交易量', '流通量', '总供应量', '最大供应量', 
            '历史最高', '历史最低', '数据源', '更新时间'
        ];
        
        const csvContent = [
            headers.join(','),
            ...this.currentData.map(crypto => [
                crypto.rank || '',
                `"${crypto.name}"`,
                crypto.symbol,
                crypto.price_usd || 0,
                crypto.price_change_percentage_24h || 0,
                crypto.price_change_24h || 0,
                crypto.market_cap || 0,
                crypto.volume_24h || 0,
                crypto.circulating_supply || 0,
                crypto.total_supply || 0,
                crypto.max_supply || 0,
                crypto.ath || 0,
                crypto.atl || 0,
                crypto.source,
                crypto.timestamp
            ].join(','))
        ].join('\n');
        
        this.downloadFile(csvContent, `${filename}.csv`, 'text/csv');
    }

    exportToJSON(filename) {
        const jsonContent = JSON.stringify(this.currentData, null, 2);
        this.downloadFile(jsonContent, `${filename}.json`, 'application/json');
    }

    downloadFile(content, filename, contentType) {
        const blob = new Blob([content], { type: contentType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }

    formatPrice(price) {
        if (price == null) return '0.00';
        
        if (price < 0.01) {
            return price.toFixed(6);
        } else if (price < 1) {
            return price.toFixed(4);
        } else {
            return price.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
    }

    formatMarketCap(value) {
        if (value == null) return 'N/A';
        
        if (value >= 1e12) {
            return '$' + (value / 1e12).toFixed(2) + 'T';
        } else if (value >= 1e9) {
            return '$' + (value / 1e9).toFixed(2) + 'B';
        } else if (value >= 1e6) {
            return '$' + (value / 1e6).toFixed(2) + 'M';
        } else if (value >= 1e3) {
            return '$' + (value / 1e3).toFixed(2) + 'K';
        } else {
            return '$' + value.toFixed(2);
        }
    }

    formatNumber(value) {
        if (value == null) return 'N/A';
        
        if (value >= 1e12) {
            return (value / 1e12).toFixed(2) + 'T';
        } else if (value >= 1e9) {
            return (value / 1e9).toFixed(2) + 'B';
        } else if (value >= 1e6) {
            return (value / 1e6).toFixed(2) + 'M';
        } else if (value >= 1e3) {
            return (value / 1e3).toFixed(2) + 'K';
        } else {
            return value.toLocaleString();
        }
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        
        const date = new Date(timestamp);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    initChart() {
        const ctx = document.getElementById('price-chart').getContext('2d');
        this.priceChart = new Chart(ctx, {
            type: 'line',
            data: this.chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '加密货币价格趋势',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        display: true
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    updateChart(cryptoData) {
        if (!this.priceChart || !cryptoData.length) return;
        
        // 取前10个加密货币的数据
        const topCryptos = cryptoData.slice(0, 10);
        
        this.chartData.labels = topCryptos.map(crypto => crypto.symbol);
        this.chartData.datasets = [{
            label: '当前价格 (USD)',
            data: topCryptos.map(crypto => crypto.price_usd),
            borderColor: 'rgb(102, 126, 234)',
            backgroundColor: 'rgba(102, 126, 234, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4
        }];
        
        this.priceChart.update();
    }

    setupAutoRefresh() {
        setInterval(() => {
            this.loadInitialData();
        }, 30000); // 每30秒刷新一次
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        const container = document.querySelector('.container');
        container.insertBefore(errorDiv, container.firstChild);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    async checkScraperStatus(showMessage = true) {
        try {
            const response = await fetch('/api/scraper/status');
            const result = await response.json();
            
            if (result.success) {
                this.scraperStatus = result;
                this.updateScraperStatusDisplay();
                
                if (showMessage) {
                    const statusText = result.is_running ? '爬虫正在运行' : '爬虫已停止';
                    this.showMessage(statusText, result.is_running ? 'success' : 'info');
                }
            } else {
                if (showMessage) {
                    this.showMessage('获取爬虫状态失败: ' + result.error, 'error');
                }
            }
        } catch (error) {
            if (showMessage) {
                this.showMessage('检查爬虫状态时发生错误: ' + error.message, 'error');
            }
        }
    }

    async startScraper() {
        try {
            const response = await fetch('/api/scraper/start', {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.showMessage(result.message, 'success');
                setTimeout(() => this.checkScraperStatus(false), 2000);
            } else {
                this.showMessage(result.message || result.error, 'error');
            }
        } catch (error) {
            this.showMessage('启动爬虫时发生错误: ' + error.message, 'error');
        }
    }

    async stopScraper() {
        try {
            const response = await fetch('/api/scraper/stop', {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.showMessage(result.message, 'success');
                setTimeout(() => this.checkScraperStatus(false), 1000);
            } else {
                this.showMessage(result.message || result.error, 'error');
            }
        } catch (error) {
            this.showMessage('停止爬虫时发生错误: ' + error.message, 'error');
        }
    }

    async runScraperOnce() {
        try {
            const response = await fetch('/api/scraper/run-once', {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.showMessage(result.message, 'success');
            } else {
                this.showMessage(result.error, 'error');
            }
        } catch (error) {
            this.showMessage('手动爬取时发生错误: ' + error.message, 'error');
        }
    }

    updateScraperStatusDisplay() {
        const statusElement = document.getElementById('scraper-status');
        const statusTextElement = document.getElementById('scraper-status-text');
        const nextRunElement = document.getElementById('next-run-time');
        
        if (this.scraperStatus) {
            statusElement.style.display = 'block';
            
            if (this.scraperStatus.is_running) {
                statusTextElement.textContent = `🟢 爬虫运行中 (${this.scraperStatus.active_jobs} 个任务)`;
                statusTextElement.className = 'status-running';
                
                if (this.scraperStatus.next_run) {
                    const nextRun = new Date(this.scraperStatus.next_run);
                    nextRunElement.textContent = `下次运行: ${nextRun.toLocaleString()}`;
                } else {
                    nextRunElement.textContent = '';
                }
            } else {
                statusTextElement.textContent = '🔴 爬虫已停止';
                statusTextElement.className = 'status-stopped';
                nextRunElement.textContent = '';
            }
        }
    }

    showMessage(message, type = 'info') {
        // 创建消息提示
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;
        
        // 添加到页面
        document.body.appendChild(messageDiv);
        
        // 3秒后自动移除
        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }
}

// WebSocket更新处理函数
function updateCryptoCards(cryptoData) {
    if (window.cryptoApp) {
        window.cryptoApp.currentData = cryptoData;
        window.cryptoApp.updateDisplay();
    }
}

function updatePriceChart(cryptoData) {
    if (window.cryptoApp) {
        window.cryptoApp.updateChart(cryptoData);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.cryptoApp = new CryptoApp();
});