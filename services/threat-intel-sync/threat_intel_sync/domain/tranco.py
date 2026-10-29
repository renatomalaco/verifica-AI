"""Tranco top list (rank,domain per line): popularity evidence for stage 1."""


def parse_tranco_csv(text: str, top: int) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for line in text.splitlines():
        rank, _, domain = line.strip().partition(",")
        if not (rank.isdigit() and domain):
            continue  # one bad line must not drop the whole list
        if int(rank) > top:
            break
        ranks[domain.lower()] = int(rank)
    return ranks
