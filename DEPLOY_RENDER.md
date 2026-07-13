# AI智能看盘系统 — Render 部署配置

## 部署到 Render

### 1. 准备 Git 仓库
```bash
cd "C:\Users\Administrator\.hermes\智能看盘"
git init
git add .
git commit -m "AI智能看盘系统 v0.1"
```

### 2. 推送到 GitHub/Gitee
```bash
git remote add origin https://github.com/YOUR_USERNAME/stock-trader.git
git push -u origin main
# 或使用 Gitee:
# git remote add origin https://gitee.com/YOUR_USERNAME/stock-trader.git
# git push -u origin main
```

### 3. 在 Render 上创建服务

1. 注册/登录 [render.com](https://render.com)
2. 点击 **New +** → **Public Web Service**
3. 连接你的 Git 仓库
4. 配置以下参数：

| 参数 | 值 |
|------|-----|
| Name | ai-stock-trader |
| Region | Singapore (新加坡，离中国近) |
| Branch | main |
| Root Directory | (留空) |
| Runtime | Python 3 |
| Build Command | `pip install -r render-requirements.txt` |
| Start Command | `python -m uvicorn web.api:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

5. 点击 **Create Web Service**

### 4. 环境变量（可选）
Render 会自动注入 `$PORT` 环境变量，无需手动设置。

### 5. 访问
部署完成后，Render 会给你一个公网地址：
```
https://ai-stock-trader.onrender.com
```

---

## 注意事项

### Render Free Tier 限制
- **休眠**: 90天无访问会自动休眠，首次访问需等待 ~30秒冷启动
- **带宽**: 每月 100GB
- **磁盘**: 临时磁盘，重启后数据丢失

### 缓存持久化
当前使用文件缓存，Render 重启后缓存会清空。如需持久化：
- 改用 Redis（Render 提供付费 Redis）
- 或接受每次启动重新拉取数据

### 替代方案
如果 Render Free Tier 不够用：
- **Railway**: 免费额度 $5/月，自动 HTTPS
- **Vercel**: 适合前端，后端需搭配 API Routes
- **阿里云/腾讯云**: 国内访问更快，但需备案

---

## 快速验证本地部署包

```bash
# 检查 requirements 是否完整
pip install -r render-requirements.txt --dry-run

# 模拟端口分配
echo "PORT=8000" > .env
python -m uvicorn web.api:app --host 0.0.0.0 --port 8000
```
