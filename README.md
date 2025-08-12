# 加密货币数据爬取项目

这是一个用于爬取和展示加密货币数据的Web应用程序。

## 功能特性

- 从CoinGecko API爬取加密货币数据
- 实时数据展示和更新
- 数据存储到MongoDB
- Web界面展示
- 定时任务调度

## 技术栈

- **后端**: Python Flask
- **数据库**: MongoDB
- **前端**: HTML, CSS, JavaScript
- **爬虫**: CoinGecko API
- **任务调度**: APScheduler

## 安装和运行

1. 克隆仓库
```bash
git clone https://github.com/你的用户名/scrapecoins.git
cd scrapecoins
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，配置MongoDB连接等
```

5. 运行应用
```bash
python run.py
```

## 项目结构