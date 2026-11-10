from dataclasses import dataclass


@dataclass(frozen=True)
class TokenPrice:
    input_usd_per_1m: float
    output_usd_per_1m: float

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.input_usd_per_1m + output_tokens * self.output_usd_per_1m) / 1_000_000
