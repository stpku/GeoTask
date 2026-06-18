"""Token counter v2 — approximate + optional tiktoken."""
import re

def estimate_tokens(text: str) -> int:
    if not text: return 1
    cjk = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")
    cjk_n = len(cjk.findall(text))
    ascii_text = cjk.sub(" ", text)
    words = len(re.findall(r"\w+", ascii_text))
    syms = len(re.findall(r"[^\w\s]", ascii_text))
    return cjk_n + words + syms

def estimate_tokens_tiktoken(text: str, model: str = "gpt-4o-mini") -> int | None:
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except ImportError:
        return None
    except Exception:
        return None
