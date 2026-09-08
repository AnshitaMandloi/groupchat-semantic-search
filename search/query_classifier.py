"""
Classifies a query into semantic / attributed / temporal, extracting the
sender name and/or date range as filters where relevant.

A query can carry more than one signal (e.g. "what did Priya say last month
about the budget" is attributed + temporal); we return all detected filters
and let the ranker apply them together.
"""
import re
from datetime import datetime, timedelta
from dateutil import parser as dateparser

PARTICIPANTS = ["Priya", "Rohan", "Aman", "Sneha", "Vikram", "Neha", "Karan", "Ishaan"]

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

ATTRIBUTION_PATTERNS = [
    r"what did (\w+) say",
    r"did (\w+) (?:say|mention|suggest|agree|promise|finalize|talk about)",
    r"(\w+)'s (?:message|opinion|view)",
    r"according to (\w+)",
]


def extract_sender(query):
    ql = query
    for pat in ATTRIBUTION_PATTERNS:
        m = re.search(pat, ql, re.IGNORECASE)
        if m:
            name = m.group(1).capitalize()
            if name in PARTICIPANTS:
                return name
    for p in PARTICIPANTS:
        if re.search(rf"\b{p}\b", query, re.IGNORECASE):
            return p
    return None


def extract_date_range(query, reference_date):
    """Returns (start, end) datetimes or None."""
    ql = query.lower()

    if "last month" in ql:
        first_of_this_month = reference_date.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return (last_month_start, last_month_end + timedelta(days=1))

    if "this month" in ql:
        start = reference_date.replace(day=1)
        return (start, reference_date)

    m = re.search(r"in (january|february|march|april|may|june|july|august"
                  r"|september|october|november|december)", ql)
    if m:
        month = MONTHS[m.group(1)]
        year = reference_date.year
        start = datetime(year, month, 1)
        end_month = month + 1 if month < 12 else 1
        end_year = year if month < 12 else year + 1
        end = datetime(end_year, end_month, 1)
        return (start, end)

    m = re.search(r"last week", ql)
    if m:
        start = reference_date - timedelta(days=reference_date.weekday() + 7)
        end = start + timedelta(days=7)
        return (start, end)

    m = re.search(r"(\d{4}-\d{2}-\d{2})", ql)
    if m:
        d = dateparser.parse(m.group(1))
        return (d, d + timedelta(days=1))

    return None


TEMPORAL_HINTS = ["last month", "this month", "last week", "in january", "in february",
                   "in march", "in april", "in may", "in june", "in july", "in august",
                   "in september", "in october", "in november", "in december",
                   "week", "month", "before", "after", "around the time", "the day"]


def classify(query, reference_date):
    """
    Returns dict: {
      'type': 'semantic' | 'attributed' | 'temporal',   # primary label
      'sender': str or None,
      'date_range': (start, end) or None,
    }
    Primary type is chosen for display/reporting; filters (sender/date_range)
    are applied regardless of primary type if detected.
    """
    sender = extract_sender(query)
    date_range = extract_date_range(query, reference_date)

    is_attributed = sender is not None and re.search(
        r"\b(say|said|says|mention|suggest|agree|promise|finalize|talk)\b",
        query, re.IGNORECASE)
    is_temporal = date_range is not None

    if is_temporal and not is_attributed:
        primary = "temporal"
    elif is_attributed:
        primary = "attributed"
    else:
        primary = "semantic"

    return {
        "type": primary,
        "sender": sender if is_attributed else None,
        "date_range": date_range,
    }
