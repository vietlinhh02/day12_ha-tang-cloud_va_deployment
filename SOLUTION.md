# SOLUTION.md — Đáp Án Code Lab Day 12

> **Link deploy:** https://day12-ha-tang-cloud-va-deployment-8oes.onrender.com

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns trong basic code

| # | Vấn Đề | Code | Giải Thích |
|---|--------|------|------------|
| 1 | Hardcode secrets | `OPENAI_API_KEY = "sk-hardcoded-fake-key"` | Push lên GitHub key bị lộ ngay lập tức |
| 2 | Cố định port | `port=8000` | Cloud (Railway/Render) inject PORT qua env var, hardcode sẽ crash |
| 3 | Debug mode bật cứng | `reload=True` | Reload server liên tục, leak debug info ra ngoài |
| 4 | Không có health check | thiếu `/health` | Platform không biết agent sống/chết để restart |
| 5 | Print thay vì logging | `print(f"[DEBUG] ...")` | Log cả secret, không parse được trong production |
| 6 | Shutdown đột ngột | không có SIGTERM handler | Mất request đang xử lý dở dang |

### Exercise 1.2: Basic version đã chạy

```
POST /ask?question=Hello
=> {"answer": "Tôi là AI agent được deploy lên cloud."}
```

### Exercise 1.3: So sánh Basic vs Advanced

| Feature | Basic | Advanced | Tại Sao Quan Trọng |
|---------|-------|----------|-------------------|
| Config | Hardcode trong code | `config.py` đọc từ env vars | Đổi config không cần sửa code |
| Secrets | `api_key = "sk-abc123"` | `os.getenv("OPENAI_API_KEY")` | Không lộ secret lên GitHub |
| Port | Cố định `8000` | Từ `PORT` env var | Chạy được trên mọi cloud platform |
| Health check | Không có | `GET /health` | Platform tự động restart nếu agent die |
| Readiness | Không có | `GET /ready` | Load balancer biết instance nào sẵn sàng |
| Logging | `print()` | JSON structured logging | Dễ search, parse, tích hợp Datadog/Loki |
| Shutdown | Đột ngột | Graceful: SIGTERM -> finish -> die | Không mất dữ liệu khi deploy |
| CORS | Không có | CORS middleware | Bảo vệ frontend khỏi truy cập trái phép |

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile cơ bản

```dockerfile
FROM python:3.11          # Base image ~1GB
WORKDIR /app              # Thư mục làm việc
COPY requirements.txt .   # Copy trước để dùng layer cache
RUN pip install ...       # Cài dependencies
COPY app.py .             # Copy code
COPY utils/ ./utils/      # Copy utils
EXPOSE 8000               # Port
CMD ["python", "app.py"]  # Command khi chạy container
```

**Câu hỏi:**
1. Base image: `python:3.11` (full Python distribution ~1GB)
2. Working directory: `/app`
3. COPY requirements.txt trước: Docker cache từng layer, chỉ re-install khi requirements thay đổi
4. CMD vs ENTRYPOINT: CMD có thể override, ENTRYPOINT bắt buộc

### Exercise 2.2: Build và run

```bash
docker build -f 02-docker/develop/Dockerfile -t agent-develop .
# Size: 1.66 GB (RẤT LỚN!)
docker run -d -p 8000:8000 agent-develop
```

### Exercise 2.3: Multi-stage build

```bash
docker build -f 02-docker/production/Dockerfile -t agent-production .
# Size: 236 MB (tiết kiệm 86% so với single-stage!)
```

**Tại sao multi-stage nhỏ hơn?**
- Stage 1 (builder): `python:3.11-slim` + pip install + build tools (gcc, libpq-dev)
- Stage 2 (runtime): `python:3.11-slim` sạch, chỉ copy site-packages từ builder
- Kết quả: final image không chứa pip, gcc, libpq-dev -> nhỏ và an toàn hơn

### Exercise 2.4: Docker Compose stack

4 services:

| Service | Image | Port | Trạng Thái |
|---------|-------|------|------------|
| agent | Build từ Dockerfile (multi-stage) | Internal | Healthy |
| redis | `redis:7-alpine` | 6379 | Healthy |
| qdrant | `qdrant/qdrant:v1.9.0` | 6333 | Healthy |
| nginx | `nginx:alpine` | 80:80 | Running |

```bash
curl http://localhost/health    # OK
curl http://localhost/ask       # OK qua Nginx LB
```

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway (`railway.toml`)

```toml
[build]
builder = "NIXPACKS"           # Tự động detect Python

[deploy]
startCommand = "uvicorn app:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"
```

**Các bước deploy:**

```bash
npm i -g @railway/cli
railway login
railway init
railway variables set AGENT_API_KEY=my-secret-key
railway up
railway domain  # -> https://your-app.up.railway.app
```

### Exercise 3.2: Render (`render.yaml`)

```yaml
services:
  - type: web
    name: ai-agent
    runtime: python
    region: singapore
    plan: free
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: AGENT_API_KEY
        generateValue: true    # Render tự sinh key ngẫu nhiên
```

**So sánh Railway vs Render:**

| Tiêu Chí | Railway | Render |
|----------|---------|--------|
| Config | `railway.toml` | `render.yaml` |
| Deploy | `railway up` | Push GitHub -> Auto deploy |
| Auto generate key | Không | Có (`generateValue: true`) |
| Redis add-on | Không tự chạy | Có sẵn (`type: redis`) |

### Exercise 3.3: GCP Cloud Run

CI/CD pipeline 4 bước: `Test -> Build Docker -> Push Registry -> Deploy Cloud Run`

Cloud Run config (`service.yaml`):
- `minScale: 1` (giữ 1 instance để tránh cold start)
- `maxScale: 10` (giới hạn chi phí)
- `livenessProbe: GET /health`
- `startupProbe: GET /ready`
- Secrets quản lý qua Secret Manager

---

## Part 4: API Security

### Exercise 4.1: API Key Authentication

**Flow:**
```
Request -> Header X-API-Key -> So sánh với AGENT_API_KEY -> 401/403/200
```

| Test | Status | Response |
|------|--------|----------|
| Không có key | `401` | `Missing API key` |
| Sai key | `403` | `Invalid API key` |
| Đúng key | `200` | `{"answer": "..."}` |

**Code:**

```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != API_KEY:
        raise HTTPException(401, "Invalid or missing API key")
    return api_key

# Sử dụng:
@app.post("/ask")
async def ask_agent(..., _key: str = Depends(verify_api_key)):
    ...
```

### Exercise 4.2: JWT Authentication

**Flow:**

```
POST /auth/token {username, password}
 -> Verify credentials
 -> Tạo JWT: {sub, role, iat, exp: 60 phút}
 -> Trả về access_token

GET /ask Authorization: Bearer <token>
 -> Decode JWT, verify signature
 -> Extract username + role
 -> Process request
```

**Code:**

```python
import jwt

def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

### Exercise 4.3: Rate Limiting

**Algorithm:** Sliding Window Counter (in-memory deque)

```python
class RateLimiter:
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: dict[str, deque] = defaultdict(deque)

    def check(self, user_id: str) -> dict:
        now = time.time()
        window = self._windows[user_id]
        # Xoá các timestamp cũ ngoài window
        while window and window[0] < now - self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            raise HTTPException(429, "Rate limit exceeded")
        window.append(now)
        return {"remaining": self.max_requests - len(window)}
```

| Role | Limit | Kết Quả |
|------|-------|---------|
| User (student) | 10 req/phút | Request thứ 10+ -> `429` |
| Admin (teacher) | 100 req/phút | Không bị chặn |

### Exercise 4.4: Cost Guard

```python
# Giá OpenAI GPT-4o-mini
PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006

class CostGuard:
    def __init__(self, daily_budget_usd=1.0):
        self.daily_budget_usd = daily_budget_usd

    def check_budget(self, user_id: str):
        if record.total_cost_usd >= self.daily_budget_usd:
            raise HTTPException(402, "Daily budget exceeded")

    def record_usage(self, user_id, input_tokens, output_tokens):
        cost = (input_tokens/1000 * PRICE_PER_1K_INPUT_TOKENS +
                output_tokens/1000 * PRICE_PER_1K_OUTPUT_TOKENS)
        self._daily_cost += cost
```

**Kết quả:**
- Budget: $1/ngày per user, $10/ngày global
- `/me/usage`: `requests: 10, cost_usd: 0.0002, budget_remaining: 0.9998`
- Vượt budget: `402 Payment Required`
- Cảnh báo tại 80% usage

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health Checks

```python
@app.get("/health")   # Liveness probe
def health():
    return {"status": "ok", "uptime": uptime, "checks": checks}

@app.get("/ready")    # Readiness probe
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}
```

**Kết quả:**
- `GET /health` -> `{"status": "ok", "uptime_seconds": 4.0}`
- `GET /ready` -> `{"ready": true, "in_flight_requests": 1}`

### Exercise 5.2: Graceful Shutdown

```
t=0.0s  Request 1 & 2 gửi đến server -> in_flight = 2
t=0.5s  SIGTERM -> _is_ready = False (từ chối request mới)
        -> chờ in_flight_requests về 0
t=~3s   Cả 2 request hoàn thành -> 200 OK
        -> server tắt an toàn, không mất dữ liệu
```

**Code:**

```python
signal.signal(signal.SIGTERM, handle_sigterm)

@app.middleware("http")
async def track_requests(request, call_next):
    global _in_flight_requests
    _in_flight_requests += 1
    response = await call_next(request)
    _in_flight_requests -= 1
    return response
```

### Exercise 5.3: Stateless Design

**Vấn đề khi scale stateful:**

```
Instance 1: User A -> request 1 -> lưu session trong memory
Instance 2: User A -> request 2 -> KHÔNG thấy session -> Bug!
```

**Giải pháp: Stateless + Redis**

```
Instance 1: User A -> request 1 -> lưu session vào Redis
Instance 2: User A -> request 2 -> đọc session từ Redis -> OK!
```

### Exercise 5.4: Load Balancing

```
Client -> Nginx (8080) -> Round-robin -> Agent 1, Agent 2, Agent 3
                                               |
                                             Redis
```

### Exercise 5.5: Test Stateless

**Kết quả 5 turns với 3 instances:**

| Turn | Question | Served By | Ghi Chú |
|------|----------|-----------|---------|
| 1 | What is Docker? | instance-9a6c24 | Tạo session |
| 2 | Why containers? | instance-d64f9d | Instance khác! |
| 3 | What is Kubernetes? | instance-8c5448 | Instance khác! |
| 4 | Load balancing? | instance-9a6c24 | Trở về instance 1 |
| 5 | Redis? | instance-d64f9d | Instance khác |

=> **10 messages được bảo toàn xuyên suốt dù mỗi request đến instance khác nhau nhờ Redis!**

---

## Part 6: Deploy

**Project:** Discord Class Bot (RAG + DeepSeek V4 Flash)

| Platform | URL |
|----------|-----|
| Render | https://day12-ha-tang-cloud-va-deployment-8oes.onrender.com |
| GitHub | https://github.com/vietlinhh02/day12_ha-tang-cloud_va_deployment |

**Endpoint kiểm tra:**

```bash
# Health check
curl https://day12-ha-tang-cloud-va-deployment-8oes.onrender.com/health

# Home
curl https://day12-ha-tang-cloud-va-deployment-8oes.onrender.com/
```
