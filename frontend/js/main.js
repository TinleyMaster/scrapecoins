// 主要的前端逻辑
class CryptoApp {
    constructor() {
        this.tableContainer = document.getElementById('table-container');
        this.logContainer = document.getElementById('log-container');
        this.logContent = document.getElementById('log-content');
        this.tableBody = document.getElementById('crypto-table-body');
        this.currentView = 'log';
        this.currentData = [];
        this.sortColumn = 'rank';
        this.sortDirection = 'asc';
        this.scraperStatus = {};
        this.maxLogMessages = 1000;
        this.init();
    }

    async init() {
        try {
            this.setupEventListeners();
            this.switchView('log');
            await this.loadInitialData();
            await this.checkAllScrapersStatus();
            this.setupAutoRefresh();
        } catch (error) {
            console.error('应用初始化失败:', error);
            this.showError('应用初始化失败，请刷新页面重试');
        }
    }

    setupEventListeners() {
        // 视图切换按钮
        const tableViewBtn = document.getElementById('table-view-btn');
        if (tableViewBtn) {
            tableViewBtn.addEventListener('click', () => {
                this.switchView('table');
            });
        }
        
        const logViewBtn = document.getElementById('log-view-btn');
        if (logViewBtn) {
            logViewBtn.addEventListener('click', () => {
                this.switchView('log');
            });
        }
        
        // 清空日志按钮
        const clearLogsBtn = document.getElementById('clear-logs-btn');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => {
                this.clearLogs();
            });
        }
        
        // 全局爬虫控制按钮
        const scraperStatusBtn = document.getElementById('scraper-status-btn');
        if (scraperStatusBtn) {
            scraperStatusBtn.addEventListener('click', () => {
                this.checkAllScrapersStatus();
            });
        }
        
        const startAllScrapersBtn = document.getElementById('start-all-scrapers-btn');
        if (startAllScrapersBtn) {
            startAllScrapersBtn.addEventListener('click', () => {
                this.startAllScrapers();
            });
        }
        
        const stopAllScrapersBtn = document.getElementById('stop-all-scrapers-btn');
        if (stopAllScrapersBtn) {
            stopAllScrapersBtn.addEventListener('click', () => {
                this.stopAllScrapers();
            });
        }
        
        // 独立爬虫开关
        const coingeckoToggle = document.getElementById('coingecko-toggle');
        if (coingeckoToggle) {
            coingeckoToggle.addEventListener('change', (e) => {
                this.toggleScraper('coingecko', e.target.checked);
            });
        }
        
        const dropstabToggle = document.getElementById('dropstab-toggle');
        if (dropstabToggle) {
            dropstabToggle.addEventListener('change', (e) => {
                this.toggleScraper('dropstab', e.target.checked);
            });
        }
        
        // 新增：Tokenomist 开关
        const tokenomistToggle = document.getElementById('tokenomist-toggle');
        if (tokenomistToggle) {
            tokenomistToggle.addEventListener('change', (e) => {
                this.toggleScraper('tokenomist', e.target.checked);
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
                this.sortTable(header.dataset.sort);
            });
        });
    }

    // 独立爬虫控制方法
    async toggleScraper(scraperType, enabled) {
        try {
            const action = enabled ? 'start' : 'stop';
            const response = await fetch(`/api/scraper/${scraperType}/${action}`, { 
                method: 'POST' 
            });
            const data = await response.json();
            
            if (data.success) {
                this.showMessage(`${scraperType} 爬虫${enabled ? '启动' : '停止'}成功`, 'success');
                setTimeout(() => this.checkScraperStatus(scraperType), 1000);
            } else {
                this.showError(data.error || `${scraperType} 爬虫${enabled ? '启动' : '停止'}失败`);
                // 恢复开关状态
                const toggle = document.getElementById(`${scraperType}-toggle`);
                if (toggle) toggle.checked = !enabled;
            }
        } catch (error) {
            console.error(`${scraperType} 爬虫控制失败:`, error);
            this.showError(`${scraperType} 爬虫控制失败`);
            // 恢复开关状态
            const toggle = document.getElementById(`${scraperType}-toggle`);
            if (toggle) toggle.checked = !enabled;
        }
    }

    async checkScraperStatus(scraperType) {
        try {
            const response = await fetch(`/api/scraper/${scraperType}/status`);
            const data = await response.json();
            
            if (data.success) {
                this.scraperStatus[scraperType] = data.data;
                this.updateScraperStatusDisplay(scraperType);
            }
        } catch (error) {
            console.error(`检查${scraperType}爬虫状态失败:`, error);
        }
    }

    async checkAllScrapersStatus() {
        await Promise.all([
            this.checkScraperStatus('coingecko'),
            this.checkScraperStatus('dropstab'),
            this.checkScraperStatus('tokenomist') // 新增
        ]);
        this.updateGlobalScraperStatus();
    }

    updateScraperStatusDisplay(scraperType) {
        const status = this.scraperStatus[scraperType];
        const toggle = document.getElementById(`${scraperType}-toggle`);
        const statusSpan = document.getElementById(`${scraperType}-status`);
        
        if (toggle && status) {
            toggle.checked = status.running;
        }
        
        if (statusSpan && status) {
            statusSpan.textContent = status.running ? '运行中' : '已停止';
            statusSpan.className = `scraper-status ${status.running ? 'running' : 'stopped'}`;
        }
    }

    updateGlobalScraperStatus() {
        const statusText = document.getElementById('scraper-status-text');
        if (statusText) {
            const runningScrapers = Object.values(this.scraperStatus).filter(s => s && s.running).length;
            const totalScrapers = Object.keys(this.scraperStatus).length;
            
            if (runningScrapers === 0) {
                statusText.innerHTML = `爬虫状态: <span class="status-stopped">全部停止</span>`;
            } else if (runningScrapers === totalScrapers) {
                statusText.innerHTML = `爬虫状态: <span class="status-running">全部运行中</span>`;
            } else {
                statusText.innerHTML = `爬虫状态: <span class="status-partial">部分运行中 (${runningScrapers}/${totalScrapers})</span>`;
            }
        }
    }

    async startAllScrapers() {
        const toggles = ['coingecko-toggle', 'dropstab-toggle', 'tokenomist-toggle']; // 新增 tokenomist
        for (const toggleId of toggles) {
            const toggle = document.getElementById(toggleId);
            if (toggle && !toggle.checked) {
                toggle.checked = true;
                await this.toggleScraper(toggle.dataset.scraper, true);
            }
        }
    }

    async stopAllScrapers() {
        const toggles = ['coingecko-toggle', 'dropstab-toggle', 'tokenomist-toggle']; // 新增 tokenomist
        for (const toggleId of toggles) {
            const toggle = document.getElementById(toggleId);
            if (toggle && toggle.checked) {
                toggle.checked = false;
                await this.toggleScraper(toggle.dataset.scraper, false);
            }
        }
    }

    switchView(viewType) {
        this.currentView = viewType;
        
        // 更新按钮状态
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (viewType === 'log') {
            document.getElementById('log-view-btn').classList.add('active');
            this.tableContainer.style.display = 'none';
            this.logContainer.style.display = 'block';
        } else {
            document.getElementById('table-view-btn').classList.add('active');
            this.tableContainer.style.display = 'block';
            this.logContainer.style.display = 'none';
        }
    }

    async loadInitialData() {
        try {
            const response = await fetch('/api/cryptos?limit=100');
            const data = await response.json();
            
            if (data.success && data.data) {
                this.currentData = data.data;
                this.updateDisplay();
            } else {
                throw new Error(data.error || '获取数据失败');
            }
        } catch (error) {
            console.error('加载初始数据失败:', error);
            this.showError('加载数据失败，请检查网络连接');
        }
    }

    updateDisplay() {
        this.updateCryptoTable(this.currentData);
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

    showMessage(message, type = 'info') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    // 日志相关方法
    addLogMessage(message, type = 'info', timestamp = null) {
        const logContent = this.logContent;
        if (!logContent) return;
        
        const logMessage = document.createElement('div');
        logMessage.className = `log-message ${type}`;
        
        const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        
        logMessage.innerHTML = `
            <span class="timestamp">[${timeStr}]</span>
            <span class="message">${message}</span>
        `;
        
        logContent.appendChild(logMessage);
        
        // 限制日志条数
        const messages = logContent.querySelectorAll('.log-message');
        if (messages.length > this.maxLogMessages) {
            messages[0].remove();
        }
        
        // 自动滚动到底部
        const autoScroll = document.getElementById('auto-scroll');
        if (autoScroll && autoScroll.checked) {
            logContent.scrollTop = logContent.scrollHeight;
        }
    }

    clearLogs() {
        if (this.logContent) {
            this.logContent.innerHTML = `
                <div class="log-message info">
                    <span class="timestamp">[系统]</span>
                    <span class="message">日志已清空</span>
                </div>
            `;
        }
    }

    // 添加缺失的 setupAutoRefresh 方法
    setupAutoRefresh() {
        // 每30秒刷新一次数据
        setInterval(() => {
            this.loadInitialData();
        }, 30000);

        // 每10秒检查一次爬虫状态
        setInterval(() => {
            this.checkAllScrapersStatus();
        }, 10000);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.cryptoApp = new CryptoApp();
});

// 删除这两个有问题的 setInterval 调用
// setInterval(() => {
//     this.loadInitialData();
// }, 30000);

// setInterval(() => {
//     this.checkAllScrapersStatus();
// }, 10000);


