"""
Extract funding events from article text using the LLM.
Loads system prompt from prompts/system_prompt.txt, calls litellm, validates with ExtractionResult.
"""
import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import config
from litellm import completion
from pydantic import ValidationError

from models import ExtractionResult

# System prompt loaded once at module load
_SYSTEM_PROMPT_PATH = config.PROJECT_ROOT / "prompts" / "system_prompt.txt"
_SYSTEM_PROMPT = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

MAX_ATTEMPTS = 3  # initial + up to 2 retries
RETRY_SLEEP_SEC = 2


def extract_funding(
    text: str,
    title: str,
    published_at: str,
    source_channel: str,
) -> tuple[ExtractionResult, dict]:
    """
    Extract funding rounds from article text via LLM.

    Args:
        text: Cleaned article body (cleaned_text).
        title: Article title.
        published_at: Publication date string.
        source_channel: Source channel (e.g. miniflux, manual).

    Returns:
        (ExtractionResult, usage_dict) where usage_dict has "input_tokens" and "output_tokens"
        (0 if not provided by the API).
    """
    user_message = (
        "请从以下文章中提取融资事件信息。\n\n"
        f"文章标题：{title}\n"
        f"发表日期：{published_at}\n"
        f"来源：{source_channel}\n\n"
        "---\n\n"
        f"{text}"
    )
    usage = {"input_tokens": 0, "output_tokens": 0}
    last_error: Exception | None = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = completion(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            raw_content = (response.choices[0].message.content or "").strip()
            # Strip optional markdown code block
            if raw_content.startswith("```"):
                lines = raw_content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_content = "\n".join(lines)
            if getattr(response, "usage", None) is not None:
                u = response.usage
                usage["input_tokens"] = getattr(u, "prompt_tokens", 0) or getattr(u, "input_tokens", 0)
                usage["output_tokens"] = getattr(u, "completion_tokens", 0) or getattr(u, "output_tokens", 0)
            result = ExtractionResult.model_validate_json(raw_content)
            return (result, usage)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(RETRY_SLEEP_SEC)
            continue

    raise last_error  # type: ignore[misc]
