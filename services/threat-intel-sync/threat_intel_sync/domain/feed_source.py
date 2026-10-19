import csv
from typing import Protocol


class FeedSource(Protocol):
    async def fetch_urls(self) -> list[str]:
        ...


def _content_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]


def parse_openphish_content(text: str) -> list[str]:
    """Extracts URLs from the OpenPhish feed (one per line, skipping lines commented with #)."""
    return _content_lines(text)


def parse_urlhaus_content(text: str) -> list[str]:
    """Extracts URLs from the public URLhaus database (skipping lines commented with #)."""
    # URLhaus format: id, dateadded, url, url_status, threat
    candidates = (row[2].strip() for row in csv.reader(_content_lines(text)) if len(row) >= 3)
    return [url for url in candidates if url.startswith(("http://", "https://"))]
