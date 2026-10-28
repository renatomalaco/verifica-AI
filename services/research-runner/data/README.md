# Benchmark dataset

`benchmark_dataset.json` is a list of samples. Every number in the thesis comes from the **test split**, and only `origin: "real"` samples can ever be tested. Synthetic samples are training data only.

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique and stable (e.g. `txt-real-0042`). Never reuse an id: the split is derived from it. |
| `channel` | yes | `texto`, `url` or `imagem`. |
| `content` | yes | The message or URL, **anonymized** (see below). |
| `label` | yes | `GOLPE` or `SEGURO`. |
| `origin` | yes | `real` (collected) or `synthetic` (written or generated). |
| `source` | yes | Where it came from: `coleta-familia`, `alerta-febraban`, `noticia-g1`, `urlhaus`, `tranco`… |
| `collected_on` | for real | `YYYY-MM-DD` when it was received or captured. |
| `adversarial` | no | `true` for injection attempts (invisible characters, "ignore the rules…"). |
| `category` | no | `coercao_afetiva`, `ameaca_financeira`, `urgencia`… |

## Anonymization (LGPD)

Before adding a real message, replace every personal data item with a neutral placeholder that keeps the shape of the scam: names → `[NOME]`, phone numbers → `[TELEFONE]`, CPF → `[CPF]`, bank accounts and Pix keys → `[CHAVE_PIX]`, addresses → `[ENDERECO]`. Keep the scammer's link or domain as it is: it is the evidence.

## Split

The split is fixed by a seed (`--seed`, default 42) and stratified by channel and label, with 30% of the real samples held out (`--test-ratio`). Adding a sample moves at most one other sample between train and test.

## Running the study

```bash
uv run python -m research_runner --threshold-f1 0.92
```

It writes `reports/latest.json` and one reliability diagram per mode, and exits with code 2 while the test split is empty.

## Feed snapshot and leakage

Stage 0 can load a feed snapshot with `--feed-snapshot feed.txt` (one URL per line). A URL that is both in the snapshot and in the test split is detected for free. Take test URLs from a later date or from a different source than the snapshot, and record both in the thesis.
