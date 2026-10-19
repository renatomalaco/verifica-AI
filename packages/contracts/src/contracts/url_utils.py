import urllib.parse

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "msclkid",
}


def normalize_url(raw_url: str) -> str:
    """
    Normalizes the URL for canonical comparison in threat lists, Bloom filter and cache:
    1. Forces a lowercase http/https scheme
    2. Converts internationalized hostnames (IDN / Cyrillic / homoglyphs) to punycode
    3. Removes default ports (:80 for http, :443 for https)
    4. Removes fragments (#anchor)
    5. Removes marketing tracking parameters (utm_*, fbclid, etc.)
    6. Sorts the remaining query parameters for deterministic hashing
    """
    cleaned = raw_url.strip()
    if not cleaned.lower().startswith(("http://", "https://")):
        cleaned = "http://" + cleaned

    parsed = urllib.parse.urlsplit(cleaned)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Split host and port
    if "@" in netloc:
        userinfo, hostport = netloc.split("@", 1)
        userinfo = userinfo + "@"
    else:
        userinfo, hostport = "", netloc

    if ":" in hostport:
        host, port = hostport.split(":", 1)
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            hostport = host
    else:
        host = hostport

    # Convert IDN to punycode to mitigate homograph attacks and guarantee a deterministic key
    try:
        host_encoded = host.encode("idna").decode("ascii")
    except UnicodeError:
        host_encoded = host

    netloc_final = userinfo + (host_encoded if ":" not in hostport else f"{host_encoded}:{port}")

    # Remove tracking parameters and sort query params
    filtered_query = ""
    if parsed.query:
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        kept_pairs = [
            (k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS
        ]
        kept_pairs.sort()
        filtered_query = urllib.parse.urlencode(kept_pairs)

    path = parsed.path or "/"

    return urllib.parse.urlunsplit((scheme, netloc_final, path, filtered_query, ""))


def extract_domain(url: str) -> str:
    """Extracts the lowercase domain (hostname) from the URL."""
    cleaned = url.strip()
    if not cleaned.lower().startswith(("http://", "https://")):
        cleaned = "http://" + cleaned
    parsed = urllib.parse.urlsplit(cleaned)
    hostname = parsed.hostname or ""
    return hostname.lower()
