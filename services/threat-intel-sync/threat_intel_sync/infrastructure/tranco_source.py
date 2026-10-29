import io
import zipfile

import httpx

from threat_intel_sync.domain.tranco import parse_tranco_csv

TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"


class TrancoSource:
    def __init__(self, top: int = 100_000, url: str = TRANCO_URL, timeout_seconds: float = 60.0) -> None:
        self._top = top
        self._url = url
        self._timeout = timeout_seconds

    async def fetch_ranks(self) -> dict[str, int]:
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            response = await client.get(self._url)
            response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            text = archive.read(archive.namelist()[0]).decode("utf-8")
        return parse_tranco_csv(text, top=self._top)
