"""
配置中心：表名、枚举、环境变量。
各轨道（storage / adapters / pipeline）只读此模块，不互相依赖实现细节。
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# 环境变量（从 .env 加载，需在入口调用 load_dotenv）
def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

# --- Airtable ---
AIRTABLE_API_KEY = _env("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = _env("AIRTABLE_BASE_ID")

# 表名（与 Airtable 中创建的表名一致）
TABLE_SOURCES = "Sources"
TABLE_COMPANIES = "Companies"
TABLE_ORGS = "Orgs"
TABLE_FUNDING_ROUNDS = "FundingRounds"
TABLE_EXTRACTION_LOG = "ExtractionLog"

# --- Sources 表字段 / 枚举 ---
SOURCE_TYPE_RSS_ARTICLE = "rss_article"
SOURCE_TYPE_MANUAL_ARTICLE = "manual_article"
SOURCE_TYPE_MEETING_NOTE = "meeting_note"
SOURCE_TYPE_MEMO = "memo"
SOURCE_TYPE_WEBHOOK_ARTICLE = "webhook_article"
SOURCE_TYPE_VOICE_TRANSCRIPT = "voice_transcript"

SOURCE_CHANNEL_MINIFLUX = "miniflux"
SOURCE_CHANNEL_MANUAL = "manual"
SOURCE_CHANNEL_MEETING = "meeting"
SOURCE_CHANNEL_WECHAT = "wechat"

PROCESSING_STATUS_NEW = "new"
PROCESSING_STATUS_PROCESSING = "processing"
PROCESSING_STATUS_EXTRACTED = "extracted"
PROCESSING_STATUS_NEEDS_REVIEW = "needs_review"
PROCESSING_STATUS_DONE = "done"
PROCESSING_STATUS_SKIPPED = "skipped"

# --- FundingRounds 表枚举 ---
STAGES = (
    "Angel", "Pre-Seed", "Seed", "Pre-A", "A", "A+",
    "B", "B+", "C", "C+", "D", "E+", "Pre-IPO", "IPO",
    "Strategic", "Acquisition", "Undisclosed",
)

CURRENCIES = ("CNY", "USD", "EUR", "HKD")

VERIFICATION_STATUS_UNVERIFIED = "unverified"
VERIFICATION_STATUS_VERIFIED = "verified"
VERIFICATION_STATUS_DISPUTED = "disputed"

# --- ExtractionLog 表枚举 ---
LOG_STATUS_SUCCESS = "success"
LOG_STATUS_FAILED = "failed"
LOG_STATUS_PARTIAL = "partial"
LOG_STATUS_NO_FUNDING = "no_funding"

# --- 预处理：融资关键词（命中才走抽取）---
FUNDING_KEYWORDS = [
    "融资", "估值", "轮融", "领投", "跟投", "天使轮",
    "Pre-A", "A轮", "B轮", "C轮", "D轮", "IPO",
    "战略投资", "种子轮", "亿元", "亿美元", "万美元",
    "获投", "完成融资", "宣布融资",
]

# --- Miniflux ---
MINIFLUX_URL = _env("MINIFLUX_URL")
MINIFLUX_API_KEY = _env("MINIFLUX_API_KEY")

# --- LLM ---
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
# 默认模型，可通过环境变量覆盖
LLM_MODEL = _env("LLM_MODEL") or "anthropic/claude-sonnet-4-20250514"

# --- 通知（Phase 2）---
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")

# --- 存储后端（迁移时只改此处）---
STORAGE_BACKEND = _env("STORAGE_BACKEND", "airtable")
