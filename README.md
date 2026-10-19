# Verifica AI

Plataforma Multimodal em Cascata para Detecção de Phishing e Engenharia Social com Usabilidade Acessível voltada para usuários seniores e defesa acadêmica em TCC.

## Arquitetura de Microsserviços

O projeto é organizado como um workspace **uv** com microsserviços desacoplados:
- `packages/contracts`: Modelos de dados e contratos compartilhados Pydantic.
- `services/scan-orchestrator`: Ponto de entrada da API pública, detecção de canal e orquestração em cascata.
- `services/ai-gateway`: Sanitização de dados pessoais (LGPD), envelope de isolamento de prompt e clientes de IA (Jev, Gemini VLM, Embeddings).
- `services/url-inspector`: Navegação headless isolada via Playwright com mitigação de SSRF (DNS Pinning e proxy de egress).
- `services/image-extractor`: OCR (Tesseract / Florence-2), leitura de QR Code e deduplicação perceptual (pHash).
- `services/threat-intel-sync`: Worker cron para ingestão de feeds abertos de phishing (OpenPhish, URLhaus) no Redis Bloom.
- `services/research-runner`: Suíte de avaliação científica, estudo de ablação e gate CI de F1-Score.
- `web`: Frontend acessível PWA (Vite + React + Motion).

## Requisitos
- Python 3.12+
- `uv` (gerenciador de pacotes ultra-rápido)
- Docker Desktop (para testes de integração com Postgres e Redis)

## Como executar os testes

```bash
# Sincronizar o workspace
uv sync

# Executar testes unitários de todos os pacotes e serviços
uv run pytest -m "not integration"
```
