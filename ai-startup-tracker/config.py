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
TABLE_PIPELINE_STATE = "PipelineState"

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

# --- 预处理：筛选方式（谁送 LLM）---
# keyword = 标题+正文前 2000 字命中 FUNDING_KEYWORDS 任一才送 LLM（省 token，可能漏）
# minimal = 只用少数宽泛词（融资/投资/轮/亿/收购/估值/IPO），漏得少、误送多一些
# none = 不预筛，全部送 LLM，由模型判断是否有融资（不漏，token 消耗大）
FUNDING_PREFILTER = _env("FUNDING_PREFILTER", "keyword").strip().lower() or "keyword"
if FUNDING_PREFILTER not in ("keyword", "minimal", "none"):
    FUNDING_PREFILTER = "keyword"

# 关键词（keyword 模式用）：标题+正文前段命中任一即召回。含「产品发布」类以便正文精判再分类。
# 参考：标题党多（「他又出手了」「这一夜行业变了」），正文前几段比标题更可靠，召回宁可多捞。
FUNDING_KEYWORDS = [
    "融资", "领投", "跟投", "注资", "获投", "完成融资", "宣布融资", "新一轮融资", "融资金额", "总融资", "融资额", "融资规模",
    "投资", "投资方", "投资机构", "投资人", "募资", "风险投资",
    "估值", "收购", "上市", "IPO",
    "天使轮", "种子轮", "Pre-A", "A轮", "B轮", "C轮", "D轮", "E+", "战略投资", "战略融资", "轮次", "轮融",
    "亿元", "亿美元", "万美元", "亿元人民币", "千万", "百万",
    "上线", "发布", "开售", "beta", "版本", "Agent", "平台", "完成",  # 产品/动态类，召回后由正文精判区分
]
# minimal：只保留强信号，尽量少漏
FUNDING_KEYWORDS_MINIMAL = ["融资", "投资", "轮", "亿", "收购", "估值", "IPO", "领投", "跟投", "美元", "元", "上线", "发布"]

# --- Miniflux（仅读取，不修改 Miniflux 内任何数据）---
MINIFLUX_URL = _env("MINIFLUX_URL")
MINIFLUX_API_KEY = _env("MINIFLUX_API_KEY")
# 只拉取发表日期在此天数内的文章（0=不限制，避免大量 2015 等陈年未读被处理）
PUBLISHED_AFTER_DAYS = int(_env("PUBLISHED_AFTER_DAYS", "0") or "0")
# 首次 run（无 last_fetch_at）时只拉取最近 N 天的未读，避免拉一整批 2018 等陈年未读（0=不限制）
FIRST_RUN_PUBLISHED_AFTER_DAYS = int(_env("FIRST_RUN_PUBLISHED_AFTER_DAYS", "365") or "365")

# --- LLM（运行时用：从文章正文抽取融资事件，非开发时用）---
# litellm 按 model 前缀选 API Key：anthropic/ → ANTHROPIC_API_KEY，openai/ → OPENAI_API_KEY 等
LLM_MODEL = _env("LLM_MODEL") or "anthropic/claude-sonnet-4-20250514"
# 是否开启「正文精判」层：召回后先用 LLM 判正文是否含可抽取事实，再决定是否做结构化抽取（true=分层流水线）
BODY_CLASSIFY = _env("BODY_CLASSIFY", "true").strip().lower() in ("1", "true", "yes")

# --- 通知（Phase 2）---
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")

# --- 存储后端（迁移时只改此处）---
STORAGE_BACKEND = _env("STORAGE_BACKEND", "airtable")
