# LLM API Orchestration Portfolio

이 프로젝트는 OpenAI API와 로컬 Ollama 모델을 하나의 FastAPI 서비스로 통합한 LLM API 서버입니다. 단순히 모델을 띄우는 데서 끝내지 않고, 서로 다른 성격의 모델을 목적별로 분리해 사용하면서도 외부에서는 일관된 API처럼 호출할 수 있도록 설계했습니다.

핵심은 `llm-api` 컨테이너 하나가 모든 API 라우트를 담당하고, 실제 로컬 inference는 공용 `ollama` 컨테이너 하나로 위임하는 구조입니다. GPT 기반 정형 분석, 텍스트 LLM 기반 MRV 문구 생성, VLM 기반 이미지 key 추출을 한 서비스 안에서 다룰 수 있게 구성했습니다.

## 핵심 어필 포인트

- OpenAI API와 로컬 LLM을 하나의 FastAPI gateway로 통합했습니다.
- 모델별 컨테이너를 여러 개 띄우던 구조를 `llm-api + ollama` 2개 컨테이너 구조로 단순화했습니다.
- GPT, text LLM, VLM을 역할별로 분리해 비용, 속도, 배포 복잡도를 조절할 수 있게 만들었습니다.
- 기존 포트와 API path를 유지하면서 내부 구조만 통합해 서비스 전환 리스크를 줄였습니다.
- Docker Compose, healthcheck, shared volume, model routing을 정리해 재현 가능한 로컬 inference 환경을 만들었습니다.
- OCR 후보 생성, key-value 매칭, MRV 보고서 문구 생성처럼 실제 업무 흐름에 가까운 LLM API를 구현했습니다.

## Architecture

```text
client
  -> llm-api container
      -> OpenAI GPT API routes
      -> Qwen2.5 7B text API routes
      -> Qwen2.5-VL 3B vision API routes
          -> ollama container
              -> qwen2.5:7b
              -> qwen2.5vl:3b
```

현재 실행 컨테이너는 두 개입니다.

```text
llm-api   FastAPI 통합 API 서버
ollama    로컬 LLM/VLM inference 서버
```

`llm-api`는 외부 요청을 받고, 라우트별 목적에 맞는 모델 호출부로 요청을 전달합니다. `ollama`는 실제 로컬 모델 추론을 담당합니다. 이렇게 분리하면 API 레이어는 가볍게 유지하면서 모델은 하나의 공용 런타임에서 관리할 수 있습니다.

## 사용 모델

### OpenAI GPT

- 모델: `gpt-5-mini`
- 사용 영역:
  - viewer 분석
  - brain MRI 해석 라우트
  - resume 분석/계획/리포트 생성
  - 정형 JSON 응답 생성

GPT API는 OpenAI API를 직접 호출합니다. 로컬 Ollama로 대체하지 않고, 구조화된 응답과 복잡한 reasoning이 필요한 영역에 유지했습니다.

### Qwen2.5 7B

- 모델: `qwen2.5:7b`
- 실행 위치: Ollama
- 사용 영역:
  - MRV 보고서 문구 생성
  - key-value 후보 검증 및 매칭
  - 문서 기반 텍스트 추론

기존에는 `llama.cpp` 서버 컨테이너와 별도 API 컨테이너가 필요했지만, 지금은 `llm-api` 안의 얇은 API 호출부가 Ollama `/api/chat`을 호출합니다.

### Qwen2.5-VL 3B

- 모델: `qwen2.5vl:3b`
- 실행 위치: Ollama
- 사용 영역:
  - 이미지 기반 key 후보 추출
  - OCR 전처리 결과와 함께 쓸 수 있는 VLM key detection

이미지 파일을 multipart로 받아 base64로 변환한 뒤 Ollama chat API에 전달합니다. VLM 응답은 JSON 형태로 파싱하고, 깨진 JSON이나 부분 응답도 최대한 복구하도록 후처리합니다.

## API 구성

### Health Check

```bash
curl http://127.0.0.1:8008/health
```

응답 예시:

```json
{
  "service": "llm-api",
  "status": "ok",
  "providers": {
    "openai": {
      "model": "gpt-5-mini"
    },
    "ollama": {
      "base_url": "http://ollama:11434",
      "models": {
        "text": "qwen2.5:7b",
        "vlm": "qwen2.5vl:3b"
      }
    }
  }
}
```

### GPT API Routes

```text
/viewer/analyze
/brain-mri/segmentation/interpret
/resume/classify
/resume/chat
/resume/plan
/resume/overall
/resume/report
/resume/report/generate
/archive
/archive/preview
/archive/file
/archive/download
```

이 라우트들은 OpenAI API 기반입니다. 특히 resume 계열 라우트는 이력서/프로젝트 문서를 읽고, 평가 계획과 리포트를 생성하는 포트폴리오 분석 API로 구성되어 있습니다.

### VLM Key Extraction

```text
POST /api/vlm/keyvalue/extract
```

이미지에서 key 후보를 추출합니다.

```bash
curl -X POST http://127.0.0.1:8008/api/vlm/keyvalue/extract \
  -F "image=@sample.png" \
  -F "include_raw=false"
```

### Text LLM Key-Value Matching

```text
POST /api/keyvalue/extract
```

OCR 또는 VLM 단계에서 만들어진 후보를 받아 key-value pair로 정리합니다.

```bash
curl -X POST http://127.0.0.1:8008/api/keyvalue/extract \
  -H "Content-Type: application/json" \
  -d '{
    "candidates": [
      {
        "id": "pair-1",
        "key_text": "사용량",
        "value_text": "100 kWh",
        "relation": "nearby"
      }
    ]
  }'
```

### MRV Solution Generation

```text
POST /api/mrv-solution/llm
```

MRV 보고서의 특정 필드에 들어갈 문구를 생성합니다.

```bash
curl -X POST http://127.0.0.1:8008/api/mrv-solution/llm \
  -H "Content-Type: application/json" \
  -d '{
    "tag": "{{llm:qc_note_calc}}",
    "db_context": {
      "mrv_report.report_id": "TEST-001",
      "mrv_calculation_result.formula": "activity * emission_factor",
      "mrv_activity_data.usage": "100",
      "mrv_activity_data.usage_unit": "kWh",
      "mrv_emission_factor_ref.emission_factor": "0.5",
      "mrv_calculation_result.emission": "50"
    }
  }'
```

## 실행 방법

```bash
cd /home/nami/repo/llmAPI
docker compose up -d --build
```

모델 확인:

```bash
docker exec ollama ollama list
```

필요 모델:

```text
qwen2.5:7b
qwen2.5vl:3b
```

포트:

```text
127.0.0.1:8008  통합 API 기본 포트
127.0.0.1:8003  기존 GPT API 호환 포트
127.0.0.1:8006  기존 MRV API 호환 포트
127.0.0.1:8007  기존 key-value API 호환 포트
127.0.0.1:11434 Ollama API
```

## 구현 포인트

### 단일 API Gateway

`app.py`는 프로젝트 루트의 메인 FastAPI 엔트리입니다. GPT API 라우트와 로컬 모델 라우트를 하나의 앱에 붙여 외부 호출부를 단순화했습니다.

### 얇은 모델 호출부

`qwen2x5_7b`와 `qwen2x5-vl-3b` 폴더는 모델 서버가 아니라 얇은 API 호출부입니다. 실제 inference는 Ollama가 담당하고, 각 폴더의 API는 prompt 구성, 요청 정규화, 응답 파싱, 예외 처리를 담당합니다.

### 공용 Ollama Client

`qwen2x5_7b/ollama_client.py`에서 텍스트 모델 호출 로직을 공유합니다. 이를 통해 MRV API와 key-value API가 같은 방식으로 Ollama `/api/chat`을 호출합니다.

### JSON 응답 안정화

LLM 응답은 항상 완벽한 JSON으로 오지 않을 수 있습니다. 그래서 code block 제거, JSON object slicing, partial key recovery 같은 후처리를 넣어 API 사용자가 안정적인 응답을 받을 수 있게 했습니다.

### 운영 가능한 Docker 구조

루트 `docker-compose.yml` 하나로 실행 기준을 통합했습니다. 컨테이너 이름과 이미지 이름은 하이픈 기반으로 정리했고, local API 포트는 `127.0.0.1`에 바인딩했습니다.

## 이 프로젝트가 보여주는 역량

이 프로젝트는 단순한 LLM 데모가 아니라, 실제 서비스형 AI API를 만들 때 필요한 구조를 직접 설계하고 정리한 결과물입니다.

- 모델 선택 기준을 API 목적에 맞춰 나눌 수 있습니다.
- OpenAI API와 로컬 오픈 모델을 한 서비스에서 함께 운영할 수 있습니다.
- Docker 리소스를 정리하고, 컨테이너 수를 줄이고, 실행 기준을 통합할 수 있습니다.
- LLM 응답의 불안정성을 API 레이어에서 보정할 수 있습니다.
- 기존 API path와 포트를 유지하면서 내부 inference 구조를 교체할 수 있습니다.
- 문서 이미지 처리, OCR 후보 후처리, MRV 보고서 생성처럼 도메인 흐름에 맞는 LLM pipeline을 설계할 수 있습니다.

제가 이 프로젝트에서 가장 강조하고 싶은 부분은 "모델을 호출할 줄 안다"가 아니라 "모델을 서비스 구조 안에 배치하고, 유지보수 가능한 API로 감싸고, 실제 업무 흐름에 맞게 안정화할 수 있다"는 점입니다.
