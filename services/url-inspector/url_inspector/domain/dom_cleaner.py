import re
from bs4 import BeautifulSoup

# Zero must be the whole value: "font-size: 0.9em" or "opacity: 0.5" are visible text.
_HIDDEN_STYLE_REGEX = re.compile(
    r"(display\s*:\s*none|visibility\s*:\s*hidden"
    r"|font-size\s*:\s*0(?:\.0+)?(?:px|em|rem|pt|%)?\s*(?:;|$|!)"
    r"|opacity\s*:\s*0(?:\.0+)?\s*(?:;|$|!))",
    re.IGNORECASE,
)
_REMOVE_TAGS = ("script", "style", "noscript", "template", "iframe", "svg")


def _is_hidden_element(tag) -> bool:
    if tag.has_attr("hidden"):
        return True
    style = tag.get("style", "")
    return bool(_HIDDEN_STYLE_REGEX.search(style))


def clean_dom_text(html: str) -> str:
    """Extracts visible text from the DOM, dropping script, style and hidden nodes."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for tag_name in _REMOVE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    for tag in soup.find_all(True):
        if _is_hidden_element(tag):
            tag.decompose()

    raw_text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", raw_text).strip()
