# DEPLOYMENT.md

##  Hướng dẫn Deploy Production AI Agent

### 1. Deploy lên Railway

#### Cách 1: Railway CLI (nhanh nhất)

```bash
# Cài Railway CLI
npm i -g @railway/cli

# Login
railway login

# Init project (trong thư mục 06-lab-complete)
cd 06-lab-complete
railway init

# Set environment variables
railway variables set ENVIRONMENT=production
railway variables set AGENT_API_KEY=your-secret-key-here
railway variables set JWT_SECRET=your-jwt-secret-here
railway variables set DAILY_BUDGET_USD=5.0
railway variables set RATE_LIMIT_PER_MINUTE=20

# Deploy
railway up

# Lấy public URL
railway domain
# → https://your-app.up.railway.app
```

#### Cách 2: GitHub + Railway Dashboard

1. Push code lên GitHub
2. Railway Dashboard → New Project → Deploy from GitHub repo
3. Chọn branch → Auto deploy

### 2. Deploy lên Render

1. Push code lên GitHub
2. Vào [render.com](https://render.com) → Sign up
3. New Blueprint → Connect GitHub repo
4. Render tự động đọc `render.yaml`:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
5. Set secrets trong Dashboard:
   - `AGENT_API_KEY` → `generateValue: true` (tự sinh)
   - `JWT_SECRET` → `generateValue: true`
   - `OPENAI_API_KEY` → nhập key thật (nếu dùng)
6. Deploy!

### 3. Kiểm tra sau deploy

```bash
# Health check
curl https://your-app.up.railway.app/health

# Readiness
curl https://your-app.up.railway.app/ready

# Test agent (có API key)
curl -X POST https://your-app.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{"question": "What is Docker?"}'

# Test không key → phải trả 401
curl -X POST https://your-app.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "hello"}' \
  -w "\nHTTP: %{http_code}"
```

### 4. Public URL

Sau deploy, public URL sẽ có dạng:
- Railway: `https://your-app.up.railway.app`
- Render: `https://ai-agent.onrender.com`
