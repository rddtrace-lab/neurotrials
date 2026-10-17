"""Small helpers shared by the page and dashboard generators."""
import html, datetime as dt
from html import escape
import pandas as pd


def e(x):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else escape(str(x))


def clean(x):
    """Registry text sometimes arrives with HTML entities already encoded; decode once before escaping."""
    return html.unescape(x) if isinstance(x, str) else x


def pdate(s):
    """YYYY-MM or YYYY-MM-DD. Month precision maps to the last day of the month, so a trial due "2026-10" is not overdue in October."""
    if not isinstance(s, str) or not s:
        return None
    try:
        if len(s) == 10:
            return dt.date.fromisoformat(s)
        first = dt.date.fromisoformat(s + "-01")
        return (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    except ValueError:
        return None


def show_date(s):
    if not isinstance(s, str) or not s:
        return ""
    if len(s) == 7:
        try:
            return "~" + dt.date.fromisoformat(s + "-01").strftime("%b %Y")
        except ValueError:
            return s
    return s


def months_between(a, b):
    da, db = pdate(a), pdate(b)
    return None if not da or not db else (db.year - da.year) * 12 + (db.month - da.month)


def num(x):
    return "" if x is None or pd.isna(x) else f"{int(x):,}"


def truthy(v):
    return str(v) in ("True", "true", "1", "1.0")


def short_title(t, n=70):
    t = clean(t) or ""
    if len(t) <= n:
        return t
    return t[:n].rsplit(" ", 1)[0].rstrip(",;:-–(") + "…"
