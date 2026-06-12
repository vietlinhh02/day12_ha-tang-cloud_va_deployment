from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.errors import NotFound
from discord.ext import commands

from bot.agent import AgentResponse, run_agent
from bot.config import Settings
from bot.corrections import Correction, CorrectionStore
from bot.rag import RAGStore

log = logging.getLogger(__name__)

# ── palette ────────────────────────────────────────────────────────────────

_CONFIDENCE_COLORS = {
    "high": 0x2ECC71,     # emerald green
    "medium": 0xF39C12,   # warm amber
    "low": 0xE74C3C,      # soft red
}
_CONFIDENCE_BADGE = {
    "high": "🔬 Cao",
    "medium": "🧐 Trung bình",
    "low": "🌫️ Thấp",
}
_SUMMARY_COLOR = 0x9B59B6   # purple
_CORRECT_COLOR = 0x2ECC71   # green


def _compact_sources(sources: list[dict]) -> list[str]:
    """Group sources by author, deduplicate links, show count + numbered links."""
    groups: dict[tuple[str, bool], list[str]] = defaultdict(list)
    seen: set[tuple[str, bool, str]] = set()

    for src in sources:
        key = (src.get("author", "?"), src.get("is_instructor", False))
        link = src.get("link", "")
        dedup_key = (*key, link)
        if dedup_key not in seen:
            seen.add(dedup_key)
            groups[key].append(link)

    lines: list[str] = []
    for (author, is_instructor), links in groups.items():
        badge = "👨‍🏫" if is_instructor else "🧑‍🎓"
        count_suffix = f" — {len(links)} msg" if len(links) > 1 else ""
        link_parts = []
        for i, link in enumerate(links):
            link_parts.append(f"[[{i + 1}]]({link})")
        lines.append(f"{badge} **{author}**{count_suffix} {' '.join(link_parts)}")

    return lines


# ── embed builders ─────────────────────────────────────────────────────────


def _build_answer_embed(
    response: AgentResponse,
    question: str,
    user: discord.User | discord.Member,
    bot_user: discord.ClientUser | None,
) -> discord.Embed:
    """Build a polished embed for an agent answer."""
    color = _CONFIDENCE_COLORS.get(response.confidence, 0x3498DB)
    badge = _CONFIDENCE_BADGE.get(response.confidence, "🧐 Trung bình")

    embed = discord.Embed(
        description=response.answer,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )

    # Author line — bot identity
    if bot_user:
        embed.set_author(
            name="VinUni Assistant",
            icon_url=bot_user.display_avatar.url,
        )

    # Thumbnail — bot avatar
    if bot_user:
        embed.set_thumbnail(url=bot_user.display_avatar.url)

    # Question field
    truncated_q = question[:256] + ("…" if len(question) > 256 else "")
    embed.add_field(
        name=f"💭 Câu hỏi từ {user.display_name}",
        value=truncated_q,
        inline=False,
    )

    # Source citations — grouped by author, compact
    if response.sources:
        source_lines: list[str] = _compact_sources(response.sources[:5])
        embed.add_field(
            name="📖 Nguồn tham khảo",
            value="\n".join(source_lines),
            inline=False,
        )

    # Footer — confidence + disclaimer
    embed.set_footer(
        text=f"Độ tin cậy: {badge}  •  AI có thể sai — kiểm tra bằng link bên trên",
    )

    return embed


def _build_summary_embed(
    response: AgentResponse,
    topic: str,
    bot_user: discord.ClientUser | None,
) -> discord.Embed:
    """Build a polished embed for a summary."""
    embed = discord.Embed(
        description=response.answer,
        color=_SUMMARY_COLOR,
        timestamp=datetime.now(timezone.utc),
    )

    if bot_user:
        embed.set_author(
            name="VinUni Assistant — Tóm tắt",
            icon_url=bot_user.display_avatar.url,
        )
        embed.set_thumbnail(url=bot_user.display_avatar.url)

    embed.add_field(
        name="🏷️ Chủ đề",
        value=topic[:256],
        inline=False,
    )

    if response.sources:
        source_lines: list[str] = _compact_sources(response.sources[:8])
        embed.add_field(
            name="📖 Nguồn tham khảo",
            value="\n".join(source_lines),
            inline=False,
        )

    embed.set_footer(text="Tóm tắt tự động từ AI — kiểm tra lại bằng link bên trên")

    return embed


def _build_correction_embed(
    original: str,
    correction: str,
    user: discord.User | discord.Member,
    bot_user: discord.ClientUser | None,
) -> discord.Embed:
    """Build embed confirming a correction was recorded."""
    embed = discord.Embed(color=_CORRECT_COLOR, timestamp=datetime.now(timezone.utc))
    if bot_user:
        embed.set_author(
            name="VinUni Assistant — Sửa lỗi",
            icon_url=bot_user.display_avatar.url,
        )
    embed.add_field(name="⚠️ Thông tin sai", value=original[:1024], inline=False)
    embed.add_field(name="💡 Thông tin đúng", value=correction[:1024], inline=False)
    embed.set_footer(text=f"Được sửa bởi {user.display_name}")
    return embed


# ── helpers ────────────────────────────────────────────────────────────────


def _safe_followup(interaction: discord.Interaction):
    """Followup sender that swallows expired-interaction errors."""

    async def send(*args, **kwargs):
        try:
            await interaction.followup.send(*args, **kwargs)
        except NotFound:
            log.warning("Interaction expired — could not send followup")

    return send


async def _msg_to_dict(msg: discord.Message) -> dict:
    """Convert a discord.Message to our normalized dict format."""
    reply_to_id = None
    reply_parent_content = None
    reply_parent_author = None
    if msg.reference:
        reply_to_id = msg.reference.message_id
        resolved = msg.reference.resolved
        if resolved and isinstance(resolved, discord.Message):
            reply_parent_content = resolved.content
            reply_parent_author = (
                resolved.author.display_name
                if resolved.author else None
            )

    ts = getattr(msg, "created_at", None)
    return {
        "id": msg.id,
        "channel_id": msg.channel.id,
        "guild_id": msg.guild.id if msg.guild else 0,
        "content": msg.content,
        "author": {
            "username": msg.author.name,
            "display_name": msg.author.display_name,
            "bot": msg.author.bot,
        },
        "author_id": str(msg.author.id),
        "timestamp": ts.isoformat() if ts else "",
        "reply_to_id": reply_to_id,
        "reply_parent_content": reply_parent_content,
        "reply_parent_author": reply_parent_author,
    }


async def _fetch_messages(
    channel: discord.TextChannel,
    *,
    limit: int | None = None,
    after: datetime | None = None,
) -> list[dict]:
    """Fetch messages from a Discord channel and return normalized dicts."""
    messages: list[dict] = []

    kwargs: dict = {"oldest_first": True}
    if limit is not None:
        kwargs["limit"] = limit
    else:
        kwargs["limit"] = None
    if after is not None:
        kwargs["after"] = after

    async for msg in channel.history(**kwargs):
        messages.append(await _msg_to_dict(msg))

    return messages


# ── cog ────────────────────────────────────────────────────────────────────


class QACog(commands.Cog):
    """Agentic class bot — mention or slash commands."""

    def __init__(self, bot: commands.Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings
        self._rags: dict[int, RAGStore] = {}  # channel_id -> RAGStore
        self._history_locks: dict[int, asyncio.Lock] = {}  # channel_id -> lock
        self.corrections = CorrectionStore()
        self.corrections.load_from_file(settings.corrections_file)

    async def cog_load(self) -> None:
        """Pre-load configured target channels on startup."""
        for channel_id in self.settings.target_channel_ids:
            if channel_id:
                rag = self._rags.get(channel_id) or RAGStore()
                self._rags[channel_id] = rag
                if rag.load_from_cache(channel_id, self.settings.embedding_model):
                    log.info("Loaded channel %s from cache (%d chunks, last_ts=%s)",
                             channel_id, len(rag.chunks), rag.last_timestamp)
                    await self._load_history(channel_id)
                else:
                    log.info("Pre-loading history for channel %s …", channel_id)
                    await self._load_history(channel_id)

    # ── message listener (real-time indexing + mention replies) ─────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if not message.guild:
            return

        # ── Real-time indexing: only index messages in target channels ──
        if message.channel.id in self.settings.target_channel_ids:
            rag = self._get_rag(message.channel.id)
            if rag.chunks:  # only index if channel was already loaded
                msg_data = await _msg_to_dict(message)
                pending_count = rag.append_message(msg_data, self.settings)
                if pending_count >= 20:
                    new_chunks = await rag.flush_pending(self.settings)
                    if new_chunks:
                        rag.save_to_cache(message.channel.id)
                        log.info("Auto-flushed %d new chunks for channel %s", new_chunks, message.channel.id)

        # ── Mention reply ──
        if self.bot.user not in message.mentions:
            return

        question = message.content
        mentioned_users = [m for m in message.mentions if m.id != self.bot.user.id]
        for mention in message.mentions:
            question = question.replace(mention.mention, "").strip()

        if not question:
            await message.reply(
                "👋 Chào bạn! Hãy hỏi tôi bằng cách mention + câu hỏi.\n"
                "Ví dụ: `@VinUni có bài tập gì không?`"
            )
            return

        _greetings = {"hi", "hello", "hí", "chào", "hey", "hế lô", "hí ae", "alo"}
        if question.lower().strip().rstrip("!？?!.") in _greetings:
            await message.reply(
                "👋 Chào bạn! Mình là VinUni Assistant, hỏi mình gì về lớp học đi nè 😄"
            )
            return

        # Resolve which channel to query against
        source_channel_id = self._resolve_source_channel(message.channel.id)
        rag = self._get_rag(source_channel_id)

        if not rag.chunks:
            status_msg = await message.reply("🔄 Đang tải lịch sử chat... (lần đầu)")
            await self._load_history(source_channel_id)
            try:
                await status_msg.delete()
            except discord.HTTPException:
                pass
        else:
            await self._load_history(source_channel_id)

        # Flush any real-time buffered messages before query
        await rag.flush_pending(self.settings)

        async with message.channel.typing():
            guild_id = str(message.guild.id)
            log.info("Processing question from %s: %s", message.author.display_name, question[:200])

            # Inject current user + mentioned users context
            user_ctx = f"Người đang hỏi: ID={message.author.id} (tên={message.author.display_name})"
            enriched_question = f"[Context: {user_ctx}] {question}"
            if mentioned_users:
                user_tags = ", ".join(
                    f"ID={u.id} (tên={u.display_name})" for u in mentioned_users
                )
                enriched_question = f"[Context: {user_ctx} | Người được nhắc đến: {user_tags}] {question}"
                log.info("Mentioned users: %s", user_tags)

            response: AgentResponse = await run_agent(
                self.settings,
                enriched_question,
                rag,
                self.corrections,
                guild_id,
                corrected_by=message.author.display_name,
            )
            log.info("Response ready — confidence=%s, sources=%d, answer_len=%d",
                     response.confidence, len(response.sources), len(response.answer))

        if response.correction_submitted:
            self.corrections.save_to_file(self.settings.corrections_file)

        embed = _build_answer_embed(
            response, question, message.author, self.bot.user,
        )
        bot_reply = await message.reply(embed=embed, mention_author=False)

        # Auto-delete both user question and bot reply after configured seconds
        if self.settings.auto_delete_seconds > 0:
            async def _auto_delete():
                await asyncio.sleep(self.settings.auto_delete_seconds)
                try:
                    await message.delete()
                except (discord.HTTPException, discord.NotFound):
                    pass
                try:
                    await bot_reply.delete()
                except (discord.HTTPException, discord.NotFound):
                    pass
            asyncio.create_task(_auto_delete())

    # ── /ask (kept for discoverability) ─────────────────────────────────────

    @app_commands.command(name="ask", description="Hỏi AI về nội dung đã trao đổi trong kênh chat")
    @app_commands.describe(question="Câu hỏi của bạn")
    async def ask_command(self, interaction: discord.Interaction, question: str) -> None:
        send = _safe_followup(interaction)

        try:
            await interaction.response.defer(thinking=True)
        except NotFound:
            log.warning("/ask interaction expired before defer")
            return

        channel_id = self._resolve_source_channel(interaction.channel_id)
        rag = self._get_rag(channel_id)
        if not rag.chunks:
            await send("🔄 Đang tải lịch sử chat... (lần đầu)")
            await self._load_history(channel_id)
        else:
            await self._load_history(channel_id)

        await rag.flush_pending(self.settings)

        guild_id = str(interaction.guild_id or "")
        response: AgentResponse = await run_agent(
            self.settings, question, rag, self.corrections, guild_id,
            corrected_by=interaction.user.display_name,
        )

        if response.correction_submitted:
            self.corrections.save_to_file(self.settings.corrections_file)

        embed = _build_answer_embed(
            response, question, interaction.user, self.bot.user,
        )
        await send(embed=embed, delete_after=self.settings.auto_delete_seconds)

    # ── /summary ────────────────────────────────────────────────────────────

    @app_commands.command(name="summary", description="Tóm tắt một chủ đề từ lịch sử chat")
    @app_commands.describe(topic="Chủ đề cần tóm tắt (VD: 'buổi học hôm qua', 'bài tập tuần 3')")
    async def summary_command(self, interaction: discord.Interaction, topic: str) -> None:
        send = _safe_followup(interaction)

        try:
            await interaction.response.defer(thinking=True)
        except NotFound:
            log.warning("/summary interaction expired before defer")
            return

        channel_id = self._resolve_source_channel(interaction.channel_id)
        rag = self._get_rag(channel_id)
        if not rag.chunks:
            await send("🔄 Đang tải lịch sử chat...")
            await self._load_history(channel_id)
        else:
            await self._load_history(channel_id)

        await rag.flush_pending(self.settings)

        summary_question = (
            f"Hãy tóm tắt chi tiết chủ đề sau từ lịch sử chat lớp học: '{topic}'. "
            "Dùng tool summarize_topic để lấy context, sau đó viết tóm tắt có cấu trúc."
        )

        guild_id = str(interaction.guild_id or "")
        response: AgentResponse = await run_agent(
            self.settings, summary_question, rag, self.corrections, guild_id,
        )

        embed = _build_summary_embed(response, topic, self.bot.user)
        await send(embed=embed)

    # ── /correct ────────────────────────────────────────────────────────────

    @app_commands.command(name="correct", description="Sửa lỗi thông tin AI đã trả lời")
    @app_commands.describe(
        original="Thông tin sai mà AI đã nói",
        correction="Thông tin đúng",
    )
    async def correct_command(
        self, interaction: discord.Interaction, original: str, correction: str,
    ) -> None:
        send = _safe_followup(interaction)

        try:
            await interaction.response.defer(thinking=True)
        except NotFound:
            log.warning("/correct interaction expired before defer")
            return

        c = Correction(
            original_claim=original,
            correct_info=correction,
            corrected_by=interaction.user.display_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.corrections.add(c)
        self.corrections.save_to_file(self.settings.corrections_file)

        embed = _build_correction_embed(
            original, correction, interaction.user, self.bot.user,
        )
        await send(embed=embed)

    # ── /reload ─────────────────────────────────────────────────────────────

    @app_commands.command(name="reload", description="Tải lại lịch sử chat từ kênh")
    async def reload_command(self, interaction: discord.Interaction) -> None:
        send = _safe_followup(interaction)

        try:
            await interaction.response.defer(thinking=True)
        except NotFound:
            log.warning("/reload interaction expired before defer")
            return

        channel_id = self._resolve_source_channel(interaction.channel_id)
        rag = self._get_rag(channel_id)
        rag.last_timestamp = ""  # force full rebuild
        await self._load_history(channel_id)

        await send(f"✨ Đã tải lại {len(rag.chunks)} chunks từ kênh.")

    # ── history loader (incremental) ────────────────────────────────────────

    async def _load_history(self, channel_id: int) -> None:
        """Fetch messages from Discord, incremental if already have cached data.

        Uses per-channel lock to prevent concurrent fetches (on_message + slash command race).
        """
        lock = self._history_locks.setdefault(channel_id, asyncio.Lock())
        async with lock:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                log.warning("Channel %s not found or not accessible", channel_id)
                return
            if not isinstance(channel, discord.TextChannel):
                log.warning(
                    "Channel %s is not a TextChannel (got %s)",
                    channel_id, type(channel).__name__,
                )
                return

            rag = self._get_rag(channel_id)

            # Determine fetch strategy: incremental vs full
            last_ts = rag.last_timestamp
            after_dt = None
            if last_ts:
                try:
                    after_dt = datetime.fromisoformat(last_ts)
                except ValueError:
                    pass

            if after_dt:
                log.info("Incremental fetch for channel %s — after %s", channel_id, last_ts)
                messages = await _fetch_messages(channel, limit=None, after=after_dt)
                if not messages:
                    log.info("No new messages since %s", last_ts)
                    return
                new_count = await rag.extend(messages, self.settings)
                log.info("Added %d new chunks from %d messages (incremental)",
                         new_count, len(messages))
            else:
                log.info("Full fetch for channel %s (limit=%d)", channel_id, self.settings.history_limit)
                messages = await _fetch_messages(channel, limit=self.settings.history_limit)
                await rag.build(messages, self.settings)
                log.info("Full build: %d messages -> %d chunks", len(messages), len(rag.chunks))

            rag.save_to_cache(channel_id)

    def _get_rag(self, channel_id: int) -> RAGStore:
        """Get or create RAGStore for a channel."""
        if channel_id not in self._rags:
            rag = RAGStore()
            # Try loading from cache first
            if not rag.load_from_cache(channel_id, self.settings.embedding_model):
                log.info("No cache for channel %s — will fetch on demand", channel_id)
            self._rags[channel_id] = rag
        return self._rags[channel_id]

    def _resolve_source_channel(self, current_channel_id: int) -> int:
        """Pick the best target channel to query against.
        
        If current channel is a target channel, use it directly.
        Otherwise fall back to the first configured target channel.
        """
        target_ids = self.settings.target_channel_ids
        if current_channel_id in target_ids:
            return current_channel_id
        if target_ids:
            return target_ids[0]
        return current_channel_id
