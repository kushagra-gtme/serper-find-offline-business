"""Shared utilities: batching, validation, logging setup."""

import re
import sys
import logging
from typing import List, Any, Iterator, Optional


def setup_logging(level=logging.INFO) -> logging.Logger:
    """Configure logger writing to stderr."""
    logger = logging.getLogger("serper")
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(handler)
    return logger


def batch_list(items: List[Any], batch_size: int) -> Iterator[List[Any]]:
    """Yield successive batches from a list."""
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def progress_msg(current: int, total: int, prefix: str = "Progress") -> str:
    pct = (current / total) * 100 if total else 0
    return f"{prefix}: {current}/{total} ({pct:.1f}%)"


def validate_search_inputs(
    states: List[str],
    search_terms: List[str],
    pages_per_query: int,
) -> Optional[str]:
    """Return error message if invalid, None if valid."""
    if not states or not isinstance(states, list):
        return "States must be a non-empty list"
    if not search_terms or not isinstance(search_terms, list):
        return "Search terms must be a non-empty list"
    if len(states) > 50:
        return "Maximum 50 states allowed"
    if len(search_terms) > 100:
        return "Maximum 100 search terms allowed"
    for term in search_terms:
        if not isinstance(term, str) or len(term) == 0:
            return "All search terms must be non-empty strings"
        if len(term) > 200:
            return f"Search term too long: '{term[:50]}...'"
    for state in states:
        if not isinstance(state, str) or len(state) == 0:
            return "All states must be non-empty strings"
    if not isinstance(pages_per_query, int) or pages_per_query < 1 or pages_per_query > 10:
        return "pages_per_query must be between 1 and 10"
    return None


def validate_webhook_url(url: str) -> Optional[str]:
    """Return error message if invalid, None if valid."""
    if not url or not isinstance(url, str):
        return "Webhook URL must be a non-empty string"
    from urllib.parse import urlparse
    try:
        result = urlparse(url.strip())
        if not all([result.scheme, result.netloc]):
            return "Invalid webhook URL format"
        if result.scheme not in ("http", "https"):
            return "Webhook URL must be http or https"
        return None
    except Exception as e:
        return f"Invalid webhook URL: {e}"


def sanitize_run_id(run_id: str) -> Optional[str]:
    """Return error message if invalid, None if valid."""
    if not run_id or not isinstance(run_id, str):
        return "run_id must be a non-empty string"
    if not re.match(r"^[\w\-\.]+$", run_id):
        return "Invalid run_id format"
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        return "Invalid run_id: path traversal"
    if len(run_id) > 150:
        return "run_id too long (max 150 characters)"
    return None
