"""
RSS article adapter: clean HTML and normalize to ProcessedContent.
"""
from bs4 import BeautifulSoup

from adapters.base import ProcessedContent, SourceAdapter


# Lines containing these substrings are stripped (noise / boilerplate)
NOISE_PATTERNS = [
    "扫码关注",
    "长按识别",
    "点击阅读原文",
    "推荐阅读",
    "往期精选",
    "版权声明",
    "免责声明",
    "转载请注明",
    "广告",
]


class RSSArticleAdapter(SourceAdapter):
    """Adapter for RSS/HTML article content: strip scripts, styles, nav/footer/header, and noise lines."""

    def preprocess(self, raw_content: str, metadata: dict) -> ProcessedContent:
        soup = BeautifulSoup(raw_content or "", "html.parser")

        for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = text.splitlines()
        cleaned_lines = [
            line.strip()
            for line in lines
            if line.strip() and not any(p in line for p in NOISE_PATTERNS)
        ]
        cleaned_text = "\n".join(cleaned_lines)
        return ProcessedContent(text=cleaned_text, language="zh")

    def default_reliability(self) -> str:
        return "medium"
