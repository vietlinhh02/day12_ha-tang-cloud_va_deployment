# Track Decision Memo – Định hướng chuyên sâu Phase 2

## Thông tin chung

- **Học viên:** Nguyễn Viết Linh
- **Mã số sinh viên:** 2A202600719
- **Chương trình:** AI20K - Cohort 2
- **Buổi:** Day 15 – Retrospective & Định hướng chuyên sâu
- **Track đề xuất:** AI Engineer
- **Ngách ưu tiên:** AI Agent / LLM Application / AI Product

---

## B1. Research thị trường tương lai

### 1. Các nghề và kỹ năng đang tăng

Qua quá trình research thị trường và đối chiếu với nội dung AI20K, mình nhận thấy các nhóm nghề và kỹ năng đang tăng mạnh gồm:

- AI Engineer
- LLM Engineer
- Agentic AI Engineer
- Data Engineer
- MLOps / LLMOps Engineer
- Cybersecurity Engineer
- AI Product Engineer
- Backend Engineer có khả năng tích hợp AI

Thị trường hiện tại không chỉ cần người biết sử dụng AI, mà cần người có khả năng **xây dựng hệ thống AI chạy thật trong sản phẩm**. Các kỹ năng được nhắc nhiều trong JD gồm:

- Python
- Backend API
- FastAPI / REST API
- Docker
- Cloud deployment
- LLM application
- RAG pipeline
- Agent / tool calling
- Vector database
- Evaluation
- Monitoring
- Security và privacy

Điểm quan trọng là vai trò AI Engineer ngày càng gần với Software Engineer. Người làm AI không chỉ train model trong notebook, mà cần biết đưa model hoặc LLM vào hệ thống thật — có API, logging, test, monitoring và cơ chế đánh giá chất lượng.

---

### 2. Các nghề và kỹ năng đang khan

Nhóm kỹ năng đang khan là nhóm nằm giữa **AI, backend, data và production**. Nhiều người có thể làm demo AI nhanh, nhưng ít người có thể biến demo thành hệ thống ổn định, dễ bảo trì và chạy được trong production.

Các năng lực đang thiếu gồm:

- Xây dựng RAG system có đánh giá chất lượng
- Thiết kế agent có tool calling và kiểm soát lỗi
- Triển khai LLM application lên production
- Monitoring chất lượng output AI
- Tối ưu latency và chi phí gọi model
- Bảo vệ hệ thống trước prompt injection và data leak
- Kết hợp AI với security/log analysis

Đặc biệt, hướng **AI Agent / LLM Application** có tiềm năng vì doanh nghiệp cần tự động hóa quy trình phức tạp, tạo chatbot thông minh, và xây dựng reasoning engine có thể giải thích được.

---

### 3. Các kỹ năng dễ bị định giá lại

Một số kỹ năng có nguy cơ bị "định giá lại" nếu chỉ dừng ở mức cơ bản:

- Code CRUD đơn giản
- Viết prompt cơ bản
- Làm notebook ML theo tutorial
- Training model nhưng không biết deploy
- Làm frontend/backend đơn giản nhưng không hiểu sản phẩm
- Copy code bằng AI mà không biết review, test và debug

AI có thể hỗ trợ rất mạnh các phần việc lặp lại, nên lợi thế không còn nằm ở việc chỉ biết code theo yêu cầu. Lợi thế mới nằm ở khả năng **hiểu bài toán, thiết kế hệ thống, kiểm chứng kết quả và đưa sản phẩm vào thực tế**.

---

### 4. Kết luận B1

Track phù hợp nhất với mình là:

> **AI Engineer thiên về AI Agent, LLM Application và AI Product.**

Hướng này vừa có nhu cầu thị trường, vừa khớp với những gì mình đã làm trên GitHub.

---

## B2. Research role hai chiều

## Role chọn

**AI Engineer**

### 1. Bên ngoài: Role này đòi hỏi gì?

Qua các JD AI Engineer / LLM Engineer / Agentic AI Engineer, role này thường yêu cầu:

#### Technical skills

- Thành thạo Python, biết TypeScript/Go là plus
- Viết code sạch, có test, maintain được
- Backend/API: FastAPI, REST, database design
- Docker, cloud deployment (AWS/GCP)
- LLM: prompt engineering, tool calling, function calling
- RAG: chunking, embedding, retrieval, reranking
- Agent: tool use, planning, memory, multi-agent
- Evaluation: RAGAS, LLM-as-judge, offline metrics
- Monitoring: latency, cost, quality tracking
- Guardrails: prompt injection, PII detection, output validation

#### Product skills

- Hiểu bài toán người dùng
- Biết biến demo thành sản phẩm
- Biết trade-off giữa accuracy, latency và cost
- Biết giải thích output AI theo cách dễ hiểu
- Biết viết tài liệu kỹ thuật, README, PRD
- Biết phối hợp với frontend, backend và data

#### Human skills

- Tự học nhanh
- Debug tốt
- Giao tiếp rõ ràng
- Biết nhận feedback
- Biết chia task và làm việc nhóm
- Có trách nhiệm với chất lượng sản phẩm

---

### 2. Bên trong: Mình đang có gì?

#### Điểm đã có

Trên GitHub (vietlinhh02) mình có nhiều project AI thực tế:

- **vietnamese-fact-checking** – Platform kiểm tra fact tiếng Việt dùng ReAct framework và agent-based architecture
- **atrips.com** – AI-powered travel planning platform (trip itinerary với conversational AI)
- **itvx** – AI recruiting platform với JD analysis, CV screening và LiveKit + Gemini interviews
- **meeting-bot** – AI meeting bot tương tự Recall AI (record, transcribe, summarize)
- **interviewx** – Interview platform với Docling service và workflow orchestration (Go)

Về kỹ năng kỹ thuật:

- Thành thạo Python, TypeScript, có kinh nghiệm Go
- Đã build AI agent với tool calling, multi-agent system (MCP/A2A)
- Biết RAG, embedding, retrieval
- Hiểu AI evaluation/benchmarking
- Có kinh nghiệm cloud deployment và CI/CD
- Biết dùng AI coding tools (Claude Code, Cursor, Copilot, Codex) để hỗ trợ workflow
- Đã học qua observability, logging, monitoring trong AI20K

#### Điểm còn thiếu

- Cần deep hơn về RAG evaluation và agent evaluation
- Cần học thêm về guardrails, prompt injection, data leak prevention
- Cần build system có monitoring, alerting, và reliability tốt hơn
- Cần hoàn thiện portfolio với README chỉn chu, test coverage cao hơn, và demo có thể deploy được
- Cần kinh nghiệm production deployment và scaling thực tế

#### Phần thích làm

- Xây AI agent với tool calling và multi-agent orchestration
- Tích hợp LLM vào sản phẩm thật (chatbot, automation, reasoning)
- Xây pipeline từ data → embedding → retrieval → generation
- Build sản phẩm có thể demo được, không chỉ là notebook
- Dùng AI coding tools để tăng tốc development workflow
- Deployment vào cloud (AWS/GCP) với monitoring

Không thích: chỉ train model trong notebook mà không deploy, hoặc làm frontend/backend đơn giản mà không gắn với AI.

---

## B3. Track Decision Memo

### 1. Track chọn

> **AI Engineer**

Ngách ưu tiên:

> **AI Agent / LLM Application / AI Product**

---

### 2. Lý do chọn track này

**Về thị trường:** Các công ty đang cần người có khả năng xây dựng ứng dụng AI chạy thật — đặc biệt các hệ thống dùng LLM, RAG, agent, backend và cloud. Đây là nhóm kỹ năng có nhu cầu cao vì AI đang được đưa vào sản phẩm thật, không chỉ dừng ở demo.

**Về bản thân:** Mình đã có portfolio với nhiều project AI thực tế trên GitHub – từ Vietnamese fact-checking (ReAct agent), travel planning, recruiting platform, meeting bot đến interview platform. Đặc biệt mình đã làm multi-agent system với MCP/A2A, hiểu cách build AI evaluation pipeline, và quen với việc dùng AI coding tools để boost productivity.

Hướng AI Engineer này giúp mình tận dụng được những gì đã làm, đồng thời bù thêm những phần còn thiếu để có thể ship AI product thực sự.

---

### 3. Lợi thế hiện tại

- Đã có portfolio AI thực tế trên GitHub – không phải demo mà là product-grade
- Có kinh nghiệm với multi-agent system (MCP/A2A) và tool calling
- Biết cách đánh giá AI system (evaluation benchmarking)
- Thành thạo Python, TypeScript, biết Go
- Có kinh nghiệm cloud deployment và CI/CD
- Biết dùng AI coding tools (Claude Code, Cursor, Copilot) để tăng tốc
- Có tư duy build product, không chỉ làm POC

Những điểm này giúp mình không phải bắt đầu từ con số 0 trong việc xây sản phẩm AI.

---

### 4. Khoảng trống cần bù

- Deep hơn về RAG evaluation và agent evaluation (nhiều hơn baseline metrics)
- Guardrails, prompt injection prevention, data leak protection
- Production-grade monitoring, alerting, và reliability engineering
- Portfolio hoàn thiện hơn: README chỉn chu, test coverage cao, demo deploy được
- Scaling AI system để handle real traffic

---

### 5. Kế hoạch học tiếp

Trong Phase 2, tập trung vào:

#### Nhóm 1: Deep AI Engineering

- Nâng cao RAG pipeline: chunking strategy, embedding optimization, hybrid retrieval, reranking
- Deep dive agent architecture: memory, planning, self-correction, multi-agent collaboration
- Fine-tuning và evaluation: RAGAS, LLM-as-judge, offline evaluation

#### Nhóm 2: Production Readiness

- Guardrails: prompt injection prevention, output validation, PII detection
- Monitoring: latency, cost, quality metrics, alerting
- Scaling: load balancing, caching, async processing

#### Nhóm 3: Portfolio Enhancement

Hoàn thiện các project hiện có hoặc tạo project mới:

- Viết README chỉn chu với architecture diagram
- Thêm test coverage, CI/CD pipeline
- Demo deploy lên cloud (AWS/GCP)
- Quay video demo ngắn

Mục tiêu: có portfolio mà khi nhìn vào, recruiter thấy mình có thể ship AI product thật.

---

### 6. Quyết định cuối

**Track chính:** AI Engineer

**Ngách ưu tiên:** AI Agent / LLM Application / AI Product

**Mục tiêu:** Hoàn thiện portfolio để có thể ứng tuyển vị trí AI Engineer. Điều mình cần chứng minh: mình có thể build và ship AI product thật, không chỉ là demo.

---

## Tóm tắt ngắn gọn

Mình chọn hướng **AI Engineer**, tập trung vào **AI Agent, LLM Application và AI Product**.

Lý do: Thị trường cần người có thể xây và ship AI product thật. Mình đã có portfolio với nhiều project AI trên GitHub (fact-checking agent, travel AI, recruiting platform, meeting bot...), đã làm multi-agent system, hiểu evaluation và quen với AI coding workflow. Điều cần làm trong Phase 2 là deep hơn về production readiness, guardrails, monitoring và hoàn thiện portfolio để có thể apply AI Engineer một cách tự tin.
