from dataclasses import dataclass


@dataclass(frozen=True)
class RiskScore:
    """
    Value Object that keeps the risk probability normalized
    within the continuous range 0.0 to 1.0.
    """

    value: float

    def __post_init__(self):
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(
                f"Invariante violada: RiskScore deve estar normalizado entre 0.0 e 1.0. Valor recebido: {self.value}"
            )
