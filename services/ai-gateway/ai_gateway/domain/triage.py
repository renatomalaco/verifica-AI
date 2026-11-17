from typing import Protocol

from contracts import TriageResult


class TriageClient(Protocol):
    """Classifies the guarded text (masked PII inside the untrusted-data envelope)."""

    async def classify(self, envelope: str) -> TriageResult: ...
