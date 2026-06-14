# Qwen2.5 1.5B Key Embedding API

FastAPI service for the key-embedding model trained in `documentAI/key_embedding`.

## Run

```bash
cd /home/nami/repo/llmAPI/qwen2x5_1x5_b
docker network create model-network 2>/dev/null || true
docker compose up -d --build
```

The FastAPI app is exposed directly on `192.168.0.21:8004`.
The model is not loaded at container startup. Each inference request loads the adapter/model and unloads it after the response so GPU memory is released while idle.

## Endpoints

- `GET /health`
- `POST /infer`
- `POST /key-embedding/infer`

Request:

```json
{
  "text": "보험계약대출 승계 동의서 ...",
  "include_raw": false
}
```

Response:

```json
{
  "subject": {"key": "보험계약대출", "signals": ["보험계약대출"]},
  "document_type": {"key": "동의서", "signals": ["동의서"]},
  "business_domain": {"key": "금융", "signals": ["보험"]},
  "modifier": {"key": "승계", "signals": ["승계"]},
  "raw_output": null,
  "warnings": []
}
```

## Curl

```bash
curl -X POST http://192.168.0.21:8004/infer \
  -H 'Content-Type: application/json' \
  -d '{"text":"보험계약대출 승계 동의서\nDB손해보험 주식회사 귀중"}'
```
