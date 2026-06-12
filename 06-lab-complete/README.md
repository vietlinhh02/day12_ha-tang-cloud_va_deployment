# Discord Class Bot — Trợ lý AI tra cứu lịch sử lớp học

<table>
<tr><td><strong>Track</strong></td><td>A — Learning OS (Vin AI Thực Chiến)</td></tr>
<tr><td><strong>Nhóm</strong></td><td>A4</td></tr>
</table>

## Thành viên

| Họ tên | Vai trò |
|---|---|
| **Nguyễn Viết Linh** | Prototype (Discord bot + RAG pipeline) |
| Mai Ngọc Duy | Research / Evidence |
| Hoàng Trung Quân | SPEC |
| Đặng Minh Chức | Test / Failure path |
| Bùi Hoàng Linh | Demo script / Repo |

## Bài toán

Học viên lớp Discord gặp khó khăn khi tra cứu lại nội dung đã trao đổi vì chat volume cao (200-500 tin/buổi), tin nhắn phân mảnh, reply chain phức tạp — dẫn đến bỏ lỡ bài tập, deadline, hoặc kiến thức quan trọng.

**Giải pháp:** Bot AI đọc toàn bộ message history → RAG retrieval → trả lời câu hỏi bằng tiếng Việt, kèm link message gốc để người dùng tự kiểm chứng.

## Tính năng

- `/ask <câu hỏi>` — Hỏi bất kỳ nội dung nào đã trao đổi trong lớp
- `/summary <chủ đề>` — Tóm tắt một chủ đề từ lịch sử chat
- `/correct` — Gửi correction khi bot trả lời sai
- `/reload` — Tải lại toàn bộ lịch sử chat
- Tự động trả lời khi được @mention
- Tự động index tin nhắn mới theo thời gian thực
- Auto-delete cặp hỏi-đáp sau khoảng thời gian cấu hình
- Tìm kiếm theo người dùng cụ thể (search_messages_by_user)
- Hiển thị citation kèm link Discord message gốc
- Phân biệt nguồn: giảng viên (độ tin cậy cao) vs học viên
- Fallback thông minh khi không tìm thấy thông tin

## Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Bot framework | discord.py 2.x |
| LLM | DeepSeek V4 Flash |
| API endpoint | `https://opencode.ai/zen/go/v1/chat/completions` |
| Embedding | fastembed (all-MiniLM-L6-v2) |
| Retrieval | Hybrid: BM25 (rank-bm25) + vector cosine similarity |
| Rerank | Reciprocal Rank Fusion (RRF) |
| HTTP client | httpx (async) |
| Runtime | Python 3.11+ |

## Cài đặt

```bash
cd codebase

# Tạo virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Cài dependencies
pip install -e .
```

## Cấu hình

```bash
cp .env.example .env
```

Các biến môi trường cần thiết:

| Biến | Mô tả |
|---|---|
| `DISCORD_TOKEN` | Token của Discord bot |
| `DEEPSEEK_API_KEY` | API key cho DeepSeek |
| `TARGET_CHANNEL_IDS` | ID các kênh cần index (phân cách bằng dấu phẩy) |
| `INSTRUCTOR_IDS` | ID Discord của giảng viên (phân cách bằng dấu phẩy) |
| `AUTO_DELETE_SECONDS` | Thời gian tự động xoá cặp hỏi-đáp (mặc định 60s, 0 = không xoá) |
| `HISTORY_LIMIT` | Số lượng tin nhắn tối đa fetch từ Discord (mặc định 5000) |

### Lấy Discord Bot Token

1. Vào https://discord.com/developers/applications
2. Tạo application → Bot → Copy token
3. Bot cần quyền: `Send Messages`, `Read Message History`, `Use Slash Commands`, `Mention Everyone`
4. Invite bot với scope `bot` + `applications.commands`

## Chạy

```bash
python -m bot.main
```

## Cấu trúc

```
codebase/
 pyproject.toml
 .env.example
 bot/
     __init__.py
     main.py           ← Entry point, Discord client lifecycle
     config.py         ← Settings từ biến môi trường
     llm.py            ← DeepSeek V4 Flash integration (async)
     rag.py            ← Hybrid search: BM25 + vector cosine + RRF
     agent.py          ← Tool-calling agent loop với 5 tools
     cog_qa.py         ← Slash commands + on_message handler
     corrections.py    ← Lưu trữ & tra cứu user corrections
```

## Luồng hoạt động

1. Bot khởi động → sync slash commands
2. User gõ `/ask "tối qua có bài tập gì không?"` hoặc @mention bot
3. Bot fetch message history từ Discord (incremental nếu đã có cache)
4. Chunk → embedding → hybrid search (BM25 + cosine → RRF merge)
5. Agent loop: gọi tool search_history → đọc kết quả → quyết định trả lời hoặc gọi thêm tool
6. Trả về embed kèm citation link message gốc, confidence indicator
7. Auto-delete cặp hỏi-đáp sau `AUTO_DELETE_SECONDS` giây (nếu bật)
