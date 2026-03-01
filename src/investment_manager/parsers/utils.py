import re


def parse_dollar(value: str) -> float | None:
    """Parse '$1,234.56', '+$1,234.56', etc. → float rounded to 2dp."""
    cleaned = re.sub(r"[+$,]", "", value.strip())
    if not cleaned or cleaned in {"--", "-"}:
        return None
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def parse_float(value: str) -> float | None:
    """Parse a plain float string → float rounded to 2dp."""
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None
