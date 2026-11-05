"""Evidence-linked analysis for small financial report PDFs and text files.

The summary is extractive (TF-IDF sentence ranking). Metric trends use simple,
visible rules. The project deliberately does not generate investment advice.
"""

from __future__ import annotations

import re
from typing import Any

import pymupdf
from sklearn.feature_extraction.text import TfidfVectorizer


METRIC_PATTERNS = {
    "Revenue": re.compile(r"\b(?:total\s+net\s+sales|net\s+sales|total\s+revenue|revenue)\b", re.I),
    "Net income": re.compile(r"\b(?:net\s+income|net\s+profit|net\s+earnings|profit\s+for\s+the\s+(?:year|period))\b", re.I),
    "Operating income": re.compile(r"\b(?:operating\s+income|income\s+from\s+operations|operating\s+profit)\b", re.I),
    "Operating cash flow": re.compile(r"\b(?:net\s+cash\s+(?:provided\s+by|from)\s+operating\s+activities|cash\s+flow\s+from\s+operations|operating\s+cash\s+flow)\b", re.I),
    "Total debt": re.compile(r"\b(?:total\s+debt|total\s+borrowings|long[- ]term\s+debt)\b", re.I),
    "Cash and equivalents": re.compile(r"\b(?:cash\s+and\s+cash\s+equivalents|cash\s+equivalents|cash\s+balance)\b", re.I),
}

YEAR_PATTERN = re.compile(r"\b(?:FY\s*)?(20\d{2})\b", re.I)
AMOUNT_PATTERN = re.compile(
    r"(?P<currency>[$€£₹])?\s*(?P<number>\(?-?\d[\d,]*(?:\.\d+)?\)?)"
    r"\s*(?P<unit>billion|million|thousand|bn|mn|m|k|b)?\b",
    re.I,
)
UNIT_MULTIPLIER = {
    "thousand": 1_000, "k": 1_000,
    "million": 1_000_000, "mn": 1_000_000, "m": 1_000_000,
    "billion": 1_000_000_000, "bn": 1_000_000_000, "b": 1_000_000_000,
}

RISK_TERMS = [
    "going concern", "material weakness", "litigation", "regulatory investigation",
    "cybersecurity incident", "supply chain disruption", "customer concentration",
    "impairment", "restructuring", "liquidity risk",
]
OPPORTUNITY_TERMS = [
    "market expansion", "new product", "capacity expansion", "backlog growth",
    "cost savings", "productivity improvement", "strong demand", "record backlog",
    "new contract", "automation investment",
]


def extract_pages(filename: str, content: bytes) -> list[dict[str, Any]]:
    """Return page-numbered text from a PDF or UTF-8 text file."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "pdf":
        try:
            with pymupdf.open(stream=content, filetype="pdf") as pdf:
                pages = [
                    {"page": page_number, "text": page.get_text("text").strip()}
                    for page_number, page in enumerate(pdf, start=1)
                ]
        except Exception as exc:
            raise ValueError(f"Could not read this PDF: {exc}") from exc
    elif suffix in {"txt", "text"}:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding.") from exc
        pages = [{"page": 1, "text": text.strip()}]
    else:
        raise ValueError("Please upload a PDF or UTF-8 .txt file.")

    if not any(page["text"] for page in pages):
        raise ValueError(
            "No selectable text was found. This may be a scanned PDF; OCR is not included in this simple version."
        )
    return pages


def _sentences(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sentences: list[dict[str, Any]] = []
    for page in pages:
        for line in page["text"].splitlines():
            line = re.sub(r"\s+", " ", line).strip(" •\t")
            if not line:
                continue
            pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9$])", line)
            for piece in pieces:
                sentence = piece.strip()
                if len(sentence) >= 35 and len(sentence.split()) >= 5:
                    sentences.append({"text": sentence, "page": page["page"]})
    return sentences


def extractive_summary(pages: list[dict[str, Any]], sentence_count: int = 5) -> list[dict[str, Any]]:
    """Rank report sentences by TF-IDF content and return them in source order."""
    sentences = _sentences(pages)
    if not sentences:
        return []
    if len(sentences) <= sentence_count:
        return sentences

    corpus = [item["text"] for item in sentences]
    try:
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(corpus)
    except ValueError:
        return sentences[:sentence_count]
    word_counts = [max(1, len(text.split())) for text in corpus]
    scores = matrix.sum(axis=1).A1 / [count ** 0.5 for count in word_counts]
    selected = sorted(range(len(sentences)), key=lambda idx: scores[idx], reverse=True)[:sentence_count]
    return [sentences[idx] for idx in sorted(selected)]


def _amounts_from_line(line: str) -> tuple[list[dict[str, Any]], list[str]]:
    years = YEAR_PATTERN.findall(line)
    without_years = YEAR_PATTERN.sub(" ", line)
    amounts: list[dict[str, Any]] = []
    for match in AMOUNT_PATTERN.finditer(without_years):
        raw_number = match.group("number")
        if not raw_number:
            continue
        # Avoid treating small numbered list markers as financial amounts.
        if not match.group("currency") and not re.search(r"\b(?:million|billion|thousand|bn|mn|m|k|b)\b", match.group(0), re.I):
            start, end = match.span()
            if (start > 0 and without_years[start - 1].isalnum()) or (end < len(without_years) and without_years[end].isalnum()):
                continue
        negative = raw_number.startswith("(") or raw_number.startswith("-")
        numeric = float(raw_number.strip("()- ").replace(",", ""))
        if negative:
            numeric = -numeric
        unit = (match.group("unit") or "").lower()
        amounts.append({
            "value": numeric * UNIT_MULTIPLIER.get(unit, 1),
            "raw": match.group(0).strip(),
            "currency": match.group("currency") or "",
            "unit": unit,
        })
    return amounts, years


def extract_metrics(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find simple same-line metric rows and retain their evidence and page."""
    found: dict[str, dict[str, Any]] = {}
    for page in pages:
        for line in page["text"].splitlines():
            clean_line = re.sub(r"\s+", " ", line).strip()
            if not clean_line:
                continue
            metric_name = next(
                (name for name, pattern in METRIC_PATTERNS.items() if pattern.search(clean_line)),
                None,
            )
            if not metric_name:
                continue
            amounts, years = _amounts_from_line(clean_line)
            if not amounts:
                continue

            current = amounts[0]
            previous = amounts[1] if len(amounts) > 1 else None
            current_period = f"FY{years[0]}" if years else "First value shown"
            previous_period = f"FY{years[1]}" if len(years) > 1 else ("Second value shown" if previous else "Not found")
            change_pct = None
            comparable = bool(previous)
            if previous and current["unit"] != previous["unit"]:
                comparable = False
            if previous and previous["value"] != 0 and comparable:
                change_pct = (current["value"] - previous["value"]) / abs(previous["value"]) * 100

            item = {
                "metric": metric_name,
                "current_value": current["value"],
                "current_as_reported": current["raw"],
                "current_period": current_period,
                "previous_value": previous["value"] if previous else None,
                "previous_as_reported": previous["raw"] if previous else None,
                "previous_period": previous_period,
                "change_pct": change_pct,
                "currency": current["currency"],
                "unit": current["unit"],
                "page": page["page"],
                "evidence": clean_line[:500],
                "comparable": comparable,
            }
            existing = found.get(metric_name)
            if existing is None or (item["previous_value"] is not None and existing["previous_value"] is None):
                found[metric_name] = item
    return list(found.values())


def metric_signals(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply plain, inspectable rules to year-over-year metric changes."""
    signals: list[dict[str, Any]] = []
    for item in metrics:
        change = item["change_pct"]
        metric = item["metric"]
        if change is None:
            if metric == "Operating cash flow" and item["current_value"] < 0:
                signals.append({
                    "type": "risk", "title": "Negative operating cash flow",
                    "detail": "Operating cash flow is below zero in the latest value found. Review working capital and cash conversion.",
                    "page": item["page"], "evidence": item["evidence"],
                })
            continue

        if metric == "Revenue" and change <= -5:
            kind, title, detail = "risk", "Revenue declined", f"Revenue is down {abs(change):.1f}% versus the prior value found. Review volume, pricing, and segment drivers in the report."
        elif metric in {"Net income", "Operating income"} and change <= -10:
            kind, title, detail = "risk", f"{metric} declined", f"{metric} is down {abs(change):.1f}%. Review the report for margin, cost, or one-time item explanations."
        elif metric == "Operating cash flow" and change <= -10:
            kind, title, detail = "risk", "Operating cash flow weakened", f"Operating cash flow is down {abs(change):.1f}%. Review cash conversion and working capital."
        elif metric == "Total debt" and change >= 10:
            kind, title, detail = "risk", "Debt increased", f"Total debt is up {change:.1f}%. Review leverage, maturity schedule, and interest cost."
        elif metric == "Cash and equivalents" and change <= -10:
            kind, title, detail = "risk", "Cash balance declined", f"Cash and equivalents are down {abs(change):.1f}%. Review liquidity and planned cash uses."
        elif metric in {"Revenue", "Net income", "Operating income", "Operating cash flow", "Cash and equivalents"} and change >= 10:
            kind, title, detail = "opportunity", f"{metric} improved", f"{metric} is up {change:.1f}%. Review the report for the drivers and whether this appears sustainable."
        else:
            continue
        signals.append({"type": kind, "title": title, "detail": detail, "page": item["page"], "evidence": item["evidence"]})
    return signals


def disclosure_cues(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Surface selected report phrases for human review; presence is not a verdict."""
    cues = []
    terms = [(term, "risk") for term in RISK_TERMS] + [(term, "opportunity") for term in OPPORTUNITY_TERMS]
    for sentence in _sentences(pages):
        lower = sentence["text"].lower()
        for term, kind in terms:
            if term in lower:
                cues.append({
                    "type": kind,
                    "term": term,
                    "page": sentence["page"],
                    "evidence": sentence["text"][:500],
                })
    return cues


def analyze_report(filename: str, content: bytes, sentence_count: int = 5) -> dict[str, Any]:
    pages = extract_pages(filename, content)
    full_text = "\n".join(page["text"] for page in pages)
    metrics = extract_metrics(pages)
    return {
        "filename": filename,
        "page_count": len(pages),
        "character_count": len(full_text),
        "summary": extractive_summary(pages, sentence_count),
        "metrics": metrics,
        "metric_signals": metric_signals(metrics),
        "disclosure_cues": disclosure_cues(pages),
    }
