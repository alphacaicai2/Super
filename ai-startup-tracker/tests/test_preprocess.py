"""Tests for preprocessing: funding signal and RSS adapter."""
import sys
from pathlib import Path

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.rss_article import RSSArticleAdapter
from pipeline.preprocess import has_funding_signal


def test_has_funding_signal_yes() -> None:
    assert has_funding_signal("某AI公司完成B轮融资", "产品发布") is True
    assert has_funding_signal("新品发布", "本轮由红杉领投，金额数亿元。") is True
    assert has_funding_signal("融资新闻", "估值超10亿美元") is True


def test_has_funding_signal_no() -> None:
    assert has_funding_signal("今日天气", "北京晴转多云。") is False
    assert has_funding_signal("产品更新", "我们发布了新功能。") is False


def test_rss_adapter_cleans_html() -> None:
    adapter = RSSArticleAdapter()
    html = """
    <html><head><script>x=1;</script></head>
    <body>
    <nav>菜单</nav>
    <p>正文第一段。某公司完成A轮融资。</p>
    <p>扫码关注我们</p>
    <p>推荐阅读：更多文章</p>
    <p>正文第二段。</p>
    </body></html>
    """
    out = adapter.preprocess(html, {})
    assert "正文第一段" in out.text
    assert "正文第二段" in out.text
    assert "某公司完成A轮融资" in out.text
    assert "扫码关注" not in out.text
    assert "推荐阅读" not in out.text
    assert out.language == "zh"


def test_rss_adapter_reliability() -> None:
    adapter = RSSArticleAdapter()
    assert adapter.default_reliability() == "medium"


if __name__ == "__main__":
    test_has_funding_signal_yes()
    test_has_funding_signal_no()
    test_rss_adapter_cleans_html()
    test_rss_adapter_reliability()
    print("All 4 tests passed.")
