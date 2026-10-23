"""Telegram bot front end. Same RAG engine as the web app, different interface.

Setup:
  1. On Telegram, message @BotFather, send /newbot, and copy the token.
  2. Put it in .env as TELEGRAM_BOT_TOKEN=...
  3. Build the index (python scripts/build_index.py), then run:
       python -m visarag.telegram_bot          (from the src/ folder)
     or  PYTHONPATH=src python -m visarag.telegram_bot

Commands:
  /start  welcome message (English + Korean)
  /help   how to use the bot
  /mode   switch retrieval mode: /mode hybrid | bm25 | vector

The bot uses long polling, so it runs on any machine with internet access;
no public URL or webhook setup is needed.
"""

import asyncio
import html
import logging
import re

from .assistant import Answer, VisaAssistant
from .config import TELEGRAM_BOT_TOKEN

log = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096          # Telegram's max message length
PASSAGE_PREVIEW = 300          # characters of each source shown in search-only mode

WELCOME = (
    "🛂 <b>Korea Visa Assistant · 체류자격 도우미</b>\n\n"
    "Ask me about Korean student and job-seeker visas (D-2, D-4, D-10, E-7) "
    "in English or Korean. Every answer cites official sources.\n\n"
    "D-2, D-4, D-10, E-7 비자에 대해 한국어나 영어로 질문해 주세요. "
    "모든 답변에 공식 출처가 표시됩니다.\n\n"
    "Try: <i>Can I work part-time on a D-2 student-visa?</i>\n\n"
    "⚠️ General information, not legal advice. Confirm with ☎ 1345."
)

HELP = (
    "<b>How to use</b>\n"
    "• Just send your question as a message.\n"
    "• /mode shows the current search method; /mode hybrid, /mode bm25 or /mode vector changes it.\n"
    "• Sources marked ✅ were cited in the answer.\n\n"
    "Questions outside D-2, D-4, D-10 and E-7 may not be covered yet."
)


# ---------- Formatting (pure functions, unit-tested) ----------

def format_answer_html(answer: Answer) -> str:
    """Render an Answer as Telegram HTML: escaped text, bold citations, linked sources."""
    body = html.escape(answer.text.strip())
    body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>",
                  body)        # **bold** from the LLM
    body = re.sub(r"\[(\d+)\]", r"<b>[\1]</b>",
                  body)           # citation markers

    lines = [body, "", "<b>Sources</b>"]
    for i, chunk in enumerate(answer.sources, start=1):
        mark = "✅" if i in answer.cited else "▫️"
        label = html.escape(chunk.citation())
        if chunk.source_url.startswith(("http://", "https://")):
            label = f'<a href="{html.escape(chunk.source_url, quote=True)}">{label}</a>'
        lines.append(f"{mark} [{i}] {label}")
        if answer.mode == "search-only":
            preview = chunk.text.replace("\n", " ")
            if len(preview) > PASSAGE_PREVIEW:
                preview = preview[:PASSAGE_PREVIEW].rstrip() + "…"
            lines.append(f"<i>{html.escape(preview)}</i>")
    lines.append("")
    lines.append(f"<i>{html.escape(answer.mode)} · {answer.latency_s}s</i>")
    return truncate("\n".join(lines))


def truncate(text: str, limit: int = TELEGRAM_LIMIT) -> str:
    """Keep messages under Telegram's limit without cutting inside an HTML tag."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 20]
    cut = cut[: cut.rfind("\n")] if "\n" in cut else cut
    return cut + "\n…(truncated)"


def parse_mode_arg(args: list[str], available: list[str]) -> str | None:
    if not args:
        return None
    mode = args[0].lower().strip()
    return mode if mode in available else None


# ---------- Bot ----------

def build_app(assistant: VisaAssistant):
    from telegram import Update
    from telegram.constants import ChatAction, ParseMode
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(WELCOME, parse_mode=ParseMode.HTML)

    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(HELP, parse_mode=ParseMode.HTML)

    async def mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        available = assistant.available_modes
        current = context.chat_data.get("mode", assistant.mode)
        if not context.args:
            await update.message.reply_text(
                f"Current mode: {current}\nAvailable: {', '.join(available)}\nExample: /mode bm25")
            return
        new = parse_mode_arg(context.args, available)
        if new is None:
            await update.message.reply_text(f"Unknown or unavailable mode. Choose: {', '.join(available)}")
            return
        context.chat_data["mode"] = new
        await update.message.reply_text(f"Retrieval mode set to {new}.")

    async def on_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        question = (update.message.text or "").strip()
        if len(question) < 2:
            return
        await update.message.chat.send_action(ChatAction.TYPING)
        mode = context.chat_data.get("mode", assistant.mode)
        try:
            # assistant.ask is blocking (API calls), so run it off the event loop.
            answer = await asyncio.to_thread(assistant.ask, question[:500], mode)
            text = format_answer_html(answer)
        except Exception:
            log.exception("Failed to answer %r", question)
            text = "Sorry, something went wrong. Please try again in a moment."
        await update.message.reply_text(text, parse_mode=ParseMode.HTML,
                                        disable_web_page_preview=True)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("mode", mode_cmd))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, on_question))
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit(
            "Set TELEGRAM_BOT_TOKEN in .env (get one from @BotFather).")
    assistant = VisaAssistant()
    log.info("Loaded %d chunks; LLM answers: %s",
             len(assistant.chunks), assistant.use_llm)
    build_app(assistant).run_polling()


if __name__ == "__main__":
    main()
