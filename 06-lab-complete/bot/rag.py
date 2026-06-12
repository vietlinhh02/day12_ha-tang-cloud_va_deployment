from __future__ import annotations

import asyncio
import json
import logging
import pickle
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

from bot.config import Settings

log = logging.getLogger(__name__)

# RRF constant (standard value from Cormack et al.)
_RRF_K = 60
# Boost multiplier for instructor-authored chunks
_INSTRUCTOR_BOOST = 1.2
# Recency weight: higher = newer messages get more priority
_RECENCY_WEIGHT = 0.15
# Number of candidates to fetch from each retriever before RRF merge
_CANDIDATE_POOL = 20


@dataclass
class MessageChunk:
    content: str
    author: str
    author_id: str
    is_instructor: bool
    message_id: str
    channel_id: str
    guild_id: str
    timestamp: str
    reply_to_id: str | None = None


@dataclass
class RAGStore:
    chunks: list[MessageChunk] = field(default_factory=list)
    _embedder: TextEmbedding | None = None
    _embeddings: np.ndarray | None = None  # shape (n_chunks, dim)
    _bm25: BM25Okapi | None = None
    _tokenized_corpus: list[list[str]] = field(default_factory=list)
    last_timestamp: str = ""  # ISO timestamp of the most recent indexed message
    _pending: list[dict] = field(default_factory=list)  # unindexed messages
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # ── initialisation ──────────────────────────────────────────────────────

    def _ensure_embedder(self, model_name: str) -> TextEmbedding:
        if self._embedder is None:
            log.info("Loading embedding model: %s", model_name)
            self._embedder = TextEmbedding(model_name=model_name)
        return self._embedder

    # ── build ───────────────────────────────────────────────────────────────

    async def build(self, messages: list[dict], settings: Settings) -> None:
        """Full rebuild: chunk messages, build BM25 index, and compute embeddings."""
        async with self._lock:
            self.chunks = _build_chunks(messages, settings)
            if not self.chunks:
                log.warning("No chunks built — all messages were empty or from bots")
                return
            self.last_timestamp = _latest_ts(self.chunks)
            self._rebuild_index(settings)

    def append_message(self, msg_data: dict, settings: Settings) -> int:
        """Buffer a single message from a real-time listener. Flush before queries."""
        self._pending.append(msg_data)
        return len(self._pending)

    async def flush_pending(self, settings: Settings) -> int:
        """Index all buffered messages. Returns number of new chunks."""
        async with self._lock:
            if not self._pending:
                return 0
            # Snapshoot and clear to avoid race with on_message appends
            batch = self._pending
            self._pending = []
            count = self._extend_sync(batch, settings)
            return count

    async def extend(self, messages: list[dict], settings: Settings) -> int:
        """Add new messages to the existing index (incremental). Returns new chunk count."""
        async with self._lock:
            return self._extend_sync(messages, settings)

    def _extend_sync(self, messages: list[dict], settings: Settings) -> int:
        if not messages:
            return 0

        new_chunks = _build_chunks(messages, settings)
        if not new_chunks:
            return 0

        self.chunks.extend(new_chunks)
        self.last_timestamp = _latest_ts(self.chunks)

        self._rebuild_index(settings)
        return len(new_chunks)

    def _rebuild_index(self, settings: Settings) -> None:
        """Recompute embeddings + BM25 from current self.chunks."""
        texts = [c.content for c in self.chunks]
        self._tokenized_corpus = [_tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(self._tokenized_corpus)

        embedder = self._ensure_embedder(settings.embedding_model)
        embeds = list(embedder.embed(texts, batch_size=64))
        self._embeddings = np.stack(embeds)

        log.info(
            "RAG index rebuilt: %d chunks, embedding dim=%s",
            len(self.chunks),
            self._embeddings.shape[1],
        )

    # ── persistence ─────────────────────────────────────────────────────────

    def save_to_cache(self, channel_id: int, cache_dir: str = ".cache/rag") -> None:
        """Persist embeddings, BM25 index, and chunk metadata to disk."""
        base = Path(cache_dir) / str(channel_id)
        base.mkdir(parents=True, exist_ok=True)

        # 1. Embeddings as .npy
        if self._embeddings is not None:
            np.save(base / "embeddings.npy", self._embeddings)

        # 2. BM25 index + tokenized corpus as pickle
        if self._bm25 is not None:
            with open(base / "bm25.pkl", "wb") as f:
                pickle.dump({"bm25": self._bm25, "corpus": self._tokenized_corpus}, f)

        # 3. Chunks metadata as JSON
        chunks_data = [asdict(c) for c in self.chunks]
        with open(base / "chunks.json", "w") as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)

        # 4. Meta: last_timestamp
        meta = {"last_timestamp": self.last_timestamp}
        with open(base / "meta.json", "w") as f:
            json.dump(meta, f)

        log.info(
            "Cache saved: %d chunks, embeddings=%s, bm25=%s, last_ts=%s -> %s",
            len(self.chunks),
            (base / "embeddings.npy").exists(),
            (base / "bm25.pkl").exists(),
            self.last_timestamp,
            base,
        )

    def load_from_cache(
        self,
        channel_id: int,
        embedding_model: str,
        cache_dir: str = ".cache/rag",
    ) -> bool:
        """Load cached RAG data from disk. Returns True if successful."""
        base = Path(cache_dir) / str(channel_id)
        emb_path = base / "embeddings.npy"
        bm25_path = base / "bm25.pkl"
        chunks_path = base / "chunks.json"

        if not all(p.exists() for p in (emb_path, bm25_path, chunks_path)):
            log.info("No cache found for channel %s", channel_id)
            return False

        try:
            # 1. Chunks
            with open(chunks_path) as f:
                chunks_data = json.load(f)
            self.chunks = [MessageChunk(**c) for c in chunks_data]

            # 2. Embeddings
            self._embeddings = np.load(emb_path)

            # 3. BM25
            with open(bm25_path, "rb") as f:
                bm25_data = pickle.load(f)
            self._bm25 = bm25_data["bm25"]
            self._tokenized_corpus = bm25_data["corpus"]

            # 4. Meta (last_timestamp)
            meta_path = base / "meta.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                self.last_timestamp = meta.get("last_timestamp", "")
            else:
                self.last_timestamp = _latest_ts(self.chunks)

            # Ensure embedder is loaded (needed for search)
            self._ensure_embedder(embedding_model)

            log.info(
                "Cache loaded: %d chunks, embedding dim=%s, BM25 ready, last_ts=%s",
                len(self.chunks),
                self._embeddings.shape[1],
                self.last_timestamp,
            )
            return True

        except Exception:
            log.exception("Failed to load cache for channel %s — will rebuild", channel_id)
            self.chunks = []
            self._embeddings = None
            self._bm25 = None
            self._tokenized_corpus = []
            self.last_timestamp = ""
            return False

    # ── search ──────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[dict]:
        """Hybrid search: vector cosine + BM25, merged with RRF.

        Thread-safe via asyncio.Lock.
        """
        async with self._lock:
            return self._search_sync(query, top_k, threshold)

    def _search_sync(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[dict]:
        """Synchronous search logic (must be called under _lock)."""
        query = (query or "").strip()
        if not query or not self.chunks or self._embeddings is None or self._bm25 is None:
            return []

        # --- Vector retrieval ---
        embedder = self._ensure_embedder("")
        q_vec = np.array(list(embedder.embed([query])))[0]
        # Normalise for cosine similarity
        q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-10)
        e_norms = self._embeddings / (
            np.linalg.norm(self._embeddings, axis=1, keepdims=True) + 1e-10
        )
        cos_scores = e_norms @ q_norm
        # --- edge case 10: NaN guard (zero-vector chunks produce NaN after division) ---
        cos_scores = np.nan_to_num(cos_scores, nan=0.0)
        vec_top = np.argsort(-cos_scores)[:_CANDIDATE_POOL]
        vec_ranked = {int(idx): rank for rank, idx in enumerate(vec_top)}

        # --- BM25 retrieval ---
        tokenized_query = _tokenize(query)
        bm25_scores = self._bm25.get_scores(tokenized_query)
        bm25_top = np.argsort(-bm25_scores)[:_CANDIDATE_POOL]
        bm25_ranked = {int(idx): rank for rank, idx in enumerate(bm25_top)}

        # --- RRF merge ---
        all_indices = set(vec_ranked.keys()) | set(bm25_ranked.keys())
        rrf_scores: dict[int, float] = {}
        for idx in all_indices:
            score = 0.0
            if idx in vec_ranked:
                score += 1.0 / (_RRF_K + vec_ranked[idx])
            if idx in bm25_ranked:
                score += 1.0 / (_RRF_K + bm25_ranked[idx])
            # Instructor boost
            if self.chunks[idx].is_instructor:
                score *= _INSTRUCTOR_BOOST
            # Recency boost — newer messages rank higher
            ts = self.chunks[idx].timestamp
            if ts:
                try:
                    msg_dt = datetime.fromisoformat(ts)
                    days_ago = max(0, (datetime.now(timezone.utc) - msg_dt).days)
                    recency = 1.0 / (1.0 + _RECENCY_WEIGHT * days_ago)
                    score *= (1.0 + recency)
                except (ValueError, TypeError):
                    pass
            rrf_scores[idx] = score

        # Sort by RRF score descending
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        results: list[dict] = []
        for idx, score in sorted_items[:top_k]:
            if score < threshold:
                break
            chunk = self.chunks[idx]
            results.append({
                "content": chunk.content,
                "author": chunk.author,
                "author_id": chunk.author_id,
                "is_instructor": chunk.is_instructor,
                "message_id": chunk.message_id,
                "channel_id": chunk.channel_id,
                "guild_id": chunk.guild_id,
                "timestamp": chunk.timestamp,
                "reply_to_id": chunk.reply_to_id,
                "score": float(score),
                "vector_score": float(cos_scores[idx]) if idx < len(cos_scores) else 0.0,
                "bm25_score": float(bm25_scores[idx]) if idx < len(bm25_scores) else 0.0,
            })

        return results

    async def get_context_around(self, message_id: str, window: int = 3) -> list[dict]:
        """Return chunks surrounding a specific message ID."""
        async with self._lock:
            return self._get_context_around_sync(message_id, window)

    def _get_context_around_sync(self, message_id: str, window: int = 3) -> list[dict]:
        target_indices = [
            i for i, c in enumerate(self.chunks) if c.message_id == message_id
        ]
        if not target_indices:
            return []

        center = target_indices[0]
        start = max(0, center - window)
        end = min(len(self.chunks), center + window + 1)

        results: list[dict] = []
        for i in range(start, end):
            chunk = self.chunks[i]
            results.append({
                "content": chunk.content,
                "author": chunk.author,
                "is_instructor": chunk.is_instructor,
                "message_id": chunk.message_id,
                "channel_id": chunk.channel_id,
                "guild_id": chunk.guild_id,
                "timestamp": chunk.timestamp,
            })
        return results

    async def search_by_user(self, author_id: str, top_k: int = 10, sort_by_time: bool = True) -> list[dict]:
        """Return all chunks from a specific user, sorted by recency."""
        async with self._lock:
            return self._search_by_user_sync(author_id, top_k, sort_by_time)

    def _search_by_user_sync(self, author_id: str, top_k: int = 10, sort_by_time: bool = True) -> list[dict]:
        matches = [c for c in self.chunks if c.author_id == author_id]
        if sort_by_time:
            matches.sort(key=lambda c: c.timestamp, reverse=True)
        results: list[dict] = []
        for chunk in matches[:top_k]:
            results.append({
                "content": chunk.content,
                "author": chunk.author,
                "author_id": chunk.author_id,
                "is_instructor": chunk.is_instructor,
                "message_id": chunk.message_id,
                "channel_id": chunk.channel_id,
                "guild_id": chunk.guild_id,
                "timestamp": chunk.timestamp,
                "reply_to_id": chunk.reply_to_id,
                "score": 1.0,
            })
        return results


# ── helpers ─────────────────────────────────────────────────────────────────


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer for BM25."""
    return re.findall(r"\w+", text.lower())


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if len(text) <= chunk_size:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    parts: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 > chunk_size and current:
            parts.append(current.strip())
            overlap_text = current[-overlap:] if overlap else ""
            current = overlap_text + " " + sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence

    if current.strip():
        parts.append(current.strip())

    return parts


def _latest_ts(chunks: list[MessageChunk]) -> str:
    """Return the latest timestamp from all chunks."""
    timestamps = [c.timestamp for c in chunks if c.timestamp]
    return max(timestamps) if timestamps else ""


def _build_chunks(messages: list[dict], settings: Settings) -> list[MessageChunk]:
    """Convert raw messages into MessageChunks with turn merging and reply resolution."""
    instructor_set = set(settings.instructor_ids)
    msg_lookup: dict[int, dict] = {m["id"]: m for m in messages}
    chunks: list[MessageChunk] = []

    # ── Phase 1: Group conversation turns ──────────────────────────
    turns: list[dict] = []
    for msg in messages:
        content = msg.get("content", "").strip()
        if not content:
            continue
        if msg.get("author", {}).get("bot", False):
            continue

        author_id = str(msg.get("author_id", ""))
        reply_to_id = msg.get("reply_to_id")

        if reply_to_id:
            turns.append({**msg, "_merged_content": content})
            continue

        if turns:
            prev = turns[-1]
            same_author = str(prev.get("author_id", "")) == author_id
            if same_author and not prev.get("reply_to_id"):
                prev["_merged_content"] += "\n" + content
                prev["id"] = msg["id"]
                continue

        turns.append({**msg, "_merged_content": content})

    # ── Phase 2: Build chunks from turns ──────────────────────────
    for turn in turns:
        content = turn["_merged_content"].strip()
        if not content:
            continue

        author_id = str(turn.get("author_id", ""))
        is_instructor = author_id in instructor_set

        reply_to_id = turn.get("reply_to_id")
        prefix = ""
        if reply_to_id:
            parent_content = None
            parent_author = None
            if reply_to_id in msg_lookup:
                parent = msg_lookup[reply_to_id]
                parent_content = parent.get("content", "").strip()
                parent_author = (
                    parent.get("author", {}).get("display_name")
                    or parent.get("author", {}).get("username", "Unknown")
                )
            elif turn.get("reply_parent_content"):
                parent_content = turn["reply_parent_content"]
                parent_author = turn.get("reply_parent_author", "Unknown")

            if parent_content:
                prefix = f"[Reply to {parent_author}: {parent_content[:300]}]\n"

        full_content = prefix + content
        author_name = (
            turn["author"].get("display_name")
            or turn["author"].get("username", "Unknown")
        )

        parts = _split_text(full_content, settings.chunk_size, settings.chunk_overlap)

        for part in parts:
            chunk = MessageChunk(
                content=part,
                author=author_name,
                author_id=author_id,
                is_instructor=is_instructor,
                message_id=str(turn["id"]),
                channel_id=str(turn["channel_id"]),
                guild_id=str(turn.get("guild_id", "")),
                timestamp=turn.get("timestamp", ""),
                reply_to_id=str(reply_to_id) if reply_to_id else None,
            )
            chunks.append(chunk)

    return chunks
