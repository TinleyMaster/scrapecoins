# 加密货币爬虫监控系统

一个实时爬取和监控多个加密货币价格的 Python Web 应用。

## 功能特性

- 🔄 **多源数据爬取**: 支持从 CoinGecko、CoinMarketCap 等多个数据源爬取
- 📊 **实时数据展示**: 通过 WebSocket 实现价格实时更新
- 💾 **数据持久化**: 使用 SQLAlchemy 存储历史数据
- 📈 **数据可视化**: 图表展示价格趋势
- 🎯 **RESTful API**: 提供完整的 API 接口
- ⚡ **高性能**: 异步爬取，定时任务调度

## 技术栈

### 后端
- **Flask**: Web 框架
- **SQLAlchemy**: ORM 数据库操作
- **Flask-SocketIO**: WebSocket 实时通信
- **APScheduler**: 定时任务调度
- **Requests + BeautifulSoup**: 网页爬取

### 前端
- **HTML5 + CSS3**: 响应式界面
- **JavaScript ES6+**: 前端逻辑
- **Chart.js**: 数据可视化
- **Socket.IO**: 实时数据接收

### 数据库
- **SQLite**: 开发环境（默认）
- **PostgreSQL**: 生产环境（可选）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env` 文件并根据需要修改配置。

### 3. 运行应用

```bash
python run.py
```

### 4. 访问应用

打开浏览器访问: http://localhost:5000

## API 接口

- `GET /api/cryptos` - 获取所有加密货币数据
- `GET /api/cryptos/<symbol>` - 获取特定货币数据
- `GET /api/cryptos/<symbol>/history` - 获取历史价格数据

## 项目结构

详见上方的项目架构说明。

## 开发计划

- [x] 基础项目架构
- [ ] CoinGecko 爬虫实现
- [ ] CoinMarketCap 爬虫实现
- [ ] WebSocket 实时推送
- [ ] 前端界面完善
- [ ] 数据可视化图表
- [ ] 错误处理和日志
- [ ] 单元测试
- [ ] Docker 部署

## 许可证

MIT License