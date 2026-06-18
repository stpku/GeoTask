"""Lightweight token estimator for GeoTask Encoding Benchmark.

No external dependencies (no tiktoken, no transformers).
Estimates are approximate and used only for relative comparison between encoding formats.

Token estimation rules:
  - ASCII words: count via regex on word boundaries and standalone symbols
  - CJK characters: each character ≈ 1 token
  - Mixed text: sum of ASCII word tokens + CJK char count
  - Whitespace/non-content: already accounted for in regex
"""

import re


def estimate_tokens(text: str) -> int:
    """Estimate approximate token count for a text string.

    This is NOT a real tokenizer. It provides a rough estimate for
    relative comparison between encoding formats.

    Args:
        text: Input text string.

    Returns:
        Positive integer estimate of token count.

    Note:
        Token counts are approximate and used only for relative comparison
        between encoding formats. They do not represent actual LLM API
        token billing.
    """
    if not text:
        return 1

    # Count CJK (Chinese/Japanese/Korean) characters — each ≈ 1 token
    cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")
    cjk_chars = len(cjk_pattern.findall(text))

    # For ASCII portion: count words and standalone symbols
    # Remove CJK chars to avoid double-counting
    ascii_text = cjk_pattern.sub(" ", text)

    # Count word-like tokens: sequences of word chars
    word_tokens = len(re.findall(r"\w+", ascii_text))

    # Count standalone non-word, non-whitespace symbols (like =, ->, |, etc.)
    symbol_tokens = len(re.findall(r"[^\w\s]", ascii_text))

    return cjk_chars + word_tokens + symbol_tokens


def estimate_tokens_file(filepath: str) -> int:
    """Estimate tokens for a text file.

    Args:
        filepath: Path to the text file.

    Returns:
        Estimated token count.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return estimate_tokens(content)
