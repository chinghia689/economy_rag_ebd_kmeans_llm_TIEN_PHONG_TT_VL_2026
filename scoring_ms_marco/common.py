import ast
import json
import math


def parse_list(value):
    """Convert mixed Excel/JSON cell values to a Python list safely."""
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, (tuple, set)):
        return list(value)

    if isinstance(value, float) and math.isnan(value):
        return []

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return []

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, (tuple, set)):
                return list(parsed)
            if isinstance(parsed, dict):
                return list(parsed.values())
            if parsed is None:
                return []
            return [parsed]
        except Exception:
            pass

    if "||" in text:
        return [item.strip() for item in text.split("||") if item.strip()]

    return [text]