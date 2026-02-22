"""
正文精判：用 LLM 对「标题+正文」做二分类，判断是否含有可抽取的投融资/产品发布等事实。
只做 YES/NO，不做结构化抽取，用于在「召回」之后、「结构化抽取」之前过滤无关文章，提高精度、省 token。
"""
from dotenv import load_dotenv

load_dotenv()

import config
from litellm import completion

# 正文截断长度，精判阶段不必送全文
BODY_EXCERPT_LEN = 4000

_CLASSIFY_SYSTEM = """你是一个判断助手。只根据文章标题和正文内容，回答一个问题。

问题：这篇文章里是否包含「至少一处」可被结构化抽取的事实？包括但不限于：
- 具体融资轮次（公司名、轮次、金额、投资方、时间等）
- 明确的产品/业务发布（公司、产品名、发布时间等）

仅当正文中明确写了上述某一类事实（而不是泛泛谈趋势、观点、标题党）时回答 YES，否则回答 NO。
只输出一个词：YES 或 NO。"""


def body_worth_extracting(title: str, body: str) -> tuple[bool, dict]:
    """
    正文精判：正文是否含有可抽取的投融资/产品发布等事实。

    Args:
        title: 文章标题。
        body: 清洗后的正文（可传全文，函数内会截断）。

    Returns:
        (是否值得做结构化抽取, usage_dict)。
    """
    excerpt = (body or "")[:BODY_EXCERPT_LEN]
    user_message = f"标题：{title}\n\n正文：\n{excerpt}"

    usage = {"input_tokens": 0, "output_tokens": 0}
    try:
        response = completion(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": user_message},
            ],
        )
        raw = (response.choices[0].message.content or "").strip().upper()
        if getattr(response, "usage", None) is not None:
            u = response.usage
            usage["input_tokens"] = getattr(u, "prompt_tokens", 0) or getattr(u, "input_tokens", 0)
            usage["output_tokens"] = getattr(u, "completion_tokens", 0) or getattr(u, "output_tokens", 0)
        return ("YES" in raw or raw == "Y", usage)
    except Exception:
        return (True, usage)  # 精判失败时放过，交给抽取层
