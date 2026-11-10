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

Language models are only called when configured (same variables as `ai-gateway`, see `.env.example`):

- **Mode 2** (the model alone) runs when `GEMINI_API_KEY`, `GEMINI_PRICE_INPUT_USD_PER_1M`, `GEMINI_PRICE_OUTPUT_USD_PER_1M` and `GEMINI_PRICE_DATE` are set. Each sample goes through the gateway's PII masking and untrusted-content envelope, never raw.
- **Mode 3** (the cascade) uses the real triage when `AI_PROVIDER=gemini` (the Gemini variables above) or `AI_PROVIDER=jev` (`JEV_API_KEY`, `JEV_PRICE_USD_PER_1K_CALLS`, `JEV_PRICE_DATE`). Otherwise it uses the local TF-IDF classifier, and the report says so.
- Cost comes from the token usage each call reports times the declared prices; the model name and price date go into `meta.llm`. A timeout, rate limit or malformed answer counts as INCONCLUSIVO (never SEGURO) and is listed in `meta.warnings`.
- On a free tier, set `RESEARCH_LLM_PAUSE_SECONDS` (e.g. `7` for 10 requests per minute). The pause is not counted as latency.

## Feed snapshot and leakage

Stage 0 can load a feed snapshot with `--feed-snapshot feed.txt` (one URL per line). A URL that is both in the snapshot and in the test split is detected for free. Take test URLs from a later date or from a different source than the snapshot, and record both in the thesis.
