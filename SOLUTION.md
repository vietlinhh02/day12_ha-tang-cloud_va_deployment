# SOLUTION.md — Đáp án Code Lab Day 12

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns trong basic code

| # | Van de | Code | Giai thich |
|---|--------|------|------------|
| 1 | Hardcode secrets | `OPENAI_API_KEY = "sk-hardcoded-fake-key"` | Push len GitHub key bi lo ngay |
| 2 | Port co dinh | `port=8000` | Cloud (Railway/Render) inject PORT env var, hardcode se crash |
| 3 | Debug mode bat cung | `reload=True` | Reload server lien tuc, leak debug info |
| 4 | Khong health check | thieu `/health` | Platform khong biet agent song/chet de restart |
| 5 | Print thay logging | `print(f"[DEBUG] ...")` | Log ca secret, khong parse duoc trong production |
| 6 | Shutdown dot ngot | khong SIGTERM handler | Mat request dang xu ly |

### Exercise 1.2: Basic version da chay
```
POST /ask?question=Hello
=> {"answer": "Toi la AI agent duoc deploy len cloud."}
```

### Exercise 1.3: So sanh Basic vs Advanced

| Feature | Basic | Advanced | Tai sao quan trong |
|---------|-------|----------|-------------------|
| Config | Hardcode trong code | `config.py` doc tu env vars | Doi config khong can sua code |
| Secrets | `api_key = "sk-abc123"` | `os.getenv("OPENAI_API_KEY")` | Khong lo secret len GitHub |
| Port | Co dinh `8000` | Tu `PORT` env var | Chay duoc tren cloud platform |
| Health check | Khong co | `GET /health` | Platform tu dong restart neu agent die |
| Readiness | Khong | `GET /ready` | Load balancer biet instance nao san sang |
| Logging | `print()` | JSON structured logging | Search, parse, tich hop voi Datadog/Loki |
| Shutdown | Dot ngot | Graceful: SIGTERM -> finish -> die | Khong mat du lieu khi deploy |
| CORS | Khong | CORS middleware | Bao ve frontend |

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile co ban

```dockerfile
FROM python:3.11          # Base image ~1GB
WORKDIR /app              # Working directory
COPY requirements.txt .   # Copy truoc de dung layer cache
RUN pip install ...       # Cai dependencies
COPY app.py .             # Copy code
COPY utils/ ./utils/      # Copy utils
EXPOSE 8000               # Port
CMD ["python", "app.py"]  # Command
```

**Cau hoi:**
1. Base image: `python:3.11`
2. Working dir: `/app`
3. COPY requirements.txt truoc: Docker cache tung layer, chi re-install khi requirements thay doi
4. CMD vs ENTRYPOINT: CMD co the override, ENTRYPOINT bat buoc

### Exercise 2.2: Build va run

```bash
docker build -f 02-docker/develop/Dockerfile -t agent-develop .
# Size: 1.66 GB (RAT lon!)
docker run -d -p 8000:8000 agent-develop
```

### Exercise 2.3: Multi-stage build

```bash
docker build -f 02-docker/production/Dockerfile -t agent-production .
# Size: 236 MB (tiet kiem 86%!)
```

**Tai sao nho hon?**
- Stage 1 (builder): `python:3.11-slim` + pip install + build tools
- Stage 2 (runtime): `python:3.11-slim` sach, chi copy site-packages
- Ket qua: khong co pip, gcc, libpq-dev trong final image

### Exercise 2.4: Docker Compose stack

4 services:
| Service | Image | Port | Trang thai |
|---------|-------|------|-----------|
| agent | Build (multi-stage) | Internal | Healthy |
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
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn app:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"
```

**Cac buoc deploy:**
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
        generateValue: true
```

**So sanh:**

| Tieu chi | Railway | Render |
|----------|---------|--------|
| Config | `railway.toml` | `render.yaml` |
| Deploy | `railway up` | Push GitHub -> Auto deploy |
| Auto generate key | Khong | Co (`generateValue: true`) |
| Redis add-on | Khong tu chay | Co (`type: redis`) |

### Exercise 3.3: GCP Cloud Run

CI/CD pipeline 4 buoc: `Test -> Build Docker -> Push Registry -> Deploy Cloud Run`

Cloud Run config (`service.yaml`):
- `minScale: 1` (tranh cold start)
- `maxScale: 10` (gioi han chi phi)
- `livenessProbe: GET /health`
- `startupProbe: GET /ready`

---

## Part 4: API Security

### Exercise 4.1: API Key Authentication

**Flow:**
```
Request -> Header X-API-Key -> So sanh voi AGENT_API_KEY -> 401/403/200
```

| Test | Status | Response |
|------|--------|----------|
| Khong co key | `401` | `Missing API key` |
| Sai key | `403` | `Invalid API key` |
| Dung key | `200` | `{"answer": "..."}` |

**Code:**
```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != API_KEY:
        raise HTTPException(401, "Invalid or missing API key")
    return api_key

# Su dung:
@app.post("/ask")
async def ask_agent(..., _key: str = Depends(verify_api_key)):
    ...
```

### Exercise 4.2: JWT Authentication

**Flow:**
```
POST /auth/token {username, password}
 -> Verify credentials
 -> Tao JWT: {sub, role, iat, exp: 60ph}
 -> Tra ve access_token

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
        while window and window[0] < now - self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            raise HTTPException(429, "Rate limit exceeded")
        window.append(now)
        return {"remaining": self.max_requests - len(window)}
```

| Role | Limit | Result |
|------|-------|--------|
| User (student) | 10 req/phut | Request 10+ -> `429` |
| Admin (teacher) | 100 req/phut | Khong bi chan |

### Exercise 4.4: Cost Guard

```python
PRICE_PER_1K_INPUT_TOKENS = 0.00015    # GPT-4o-mini
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

**Ket qua:**
- Budget: $1/ngay per user, $10/ngay global
- `/me/usage`: `requests: 10, cost_usd: 0.0002, budget_remaining: 0.9998`
- Vuot budget: `402 Payment Required`

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

**Ket qua:**
- `GET /health` -> `{"status": "ok", "uptime_seconds": 4.0}`
- `GET /ready` -> `{"ready": true, "in_flight_requests": 1}`

### Exercise 5.2: Graceful Shutdown

```
t=0.0s  Request 1 & 2 gui den server -> in_flight = 2
t=0.5s  SIGTERM -> _is_ready = False (tu choi request moi)
        -> cho in_flight_requests ve 0
t=~3s   Ca 2 request hoan thanh -> 200 OK
        -> server tat an toan, khong mat data
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

### Exercise 5.3-5.5: Stateless + Load Balancing

**Van de khi scale stateful:**
```
Instance 1: User A -> request 1 -> luu session trong memory
Instance 2: User A -> request 2 -> KHONG thay session -> Bug!
```

**Giai phap: Stateless + Redis**
```
Instance 1: User A -> request 1 -> luu session vao Redis
Instance 2: User A -> request 2 -> doc session tu Redis OK!
```

**Kien truc:**
```
Client -> Nginx (8080) -> Round-robin -> Agent 1, Agent 2, Agent 3
                                               |
                                             Redis
```

**Ket qua 5 turns:**

| Turn | Question | Served By | Ghi chu |
|------|----------|-----------|---------|
| 1 | What is Docker? | instance-9a6c24 | Tao session |
| 2 | Why containers? | instance-d64f9d | Instance khac! |
| 3 | What is Kubernetes? | instance-8c5448 | Instance khac! |
| 4 | Load balancing? | instance-9a6c24 | Tro ve instance 1 |
| 5 | Redis? | instance-d64f9d | Instance khac |

=> **10 messages duoc bao toan xuyen suot nho Redis!**
