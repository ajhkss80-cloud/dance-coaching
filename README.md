# Dance Coaching Platform

AI 아바타 댄스 튜토리얼 영상 생성 + 댄스 코칭 시스템

![Node.js](https://img.shields.io/badge/Node.js-20%2B-339933?logo=nodedotjs&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## 주요 기능

- **두 가지 생성 백엔드**: Cloud (Kling API) 또는 Local GPU (MimicMotion) 선택 가능
- **댄스 모션 트랜스퍼**: 아바타 이미지가 참조 영상의 안무를 수행하는 튜토리얼 영상 생성
- **댄스 코칭**: 사용자 영상과 원본 영상을 비교 분석 (MediaPipe 포즈 추출 + DTW 정렬)
- **비트 감지 기반 영상 분할**: librosa를 활용해 음악의 비트에 맞춰 영상 세그먼트 분할
- **RIFE 프레임 보간**: 세그먼트 경계를 부드럽게 이어붙이는 프레임 인터폴레이션
- **클린 아키텍처**: Domain -> Application -> Infrastructure 계층 분리
- **BullMQ 비동기 작업 큐**: Redis 기반 비동기 작업 처리 및 실시간 진행률 WebSocket 전송

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                               │
│            (REST API / WebSocket 실시간 진행률)              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Server (Node.js / Fastify)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Interface     │  │ Application  │  │ Infrastructure   │  │
│  │ (Routes, WS)  │  │ (Use Cases)  │  │ (BullMQ, Redis)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ BullMQ Job Queue (Redis)
┌────────────────────────▼────────────────────────────────────┐
│                    Worker (Python)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Domain        │  │ Application  │  │ Infrastructure   │  │
│  │ (Entities,    │  │ (Use Cases,  │  │ (Kling, MimicM., │  │
│  │  Value Obj.)  │  │  Orchestr.)  │  │  MediaPipe,      │  │
│  │               │  │              │  │  librosa, RIFE,   │  │
│  │               │  │              │  │  FFmpeg)          │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**영상 생성 파이프라인 흐름:**

```
아바타 이미지 + 참조 영상
        │
        ▼
  오디오 추출 (FFmpeg)
        │
        ▼
  비트 감지 (librosa)
        │
        ▼
  세그먼트 분할 (beat-aligned)
        │
        ▼
  세그먼트별 영상 생성 (Kling API / MimicMotion)
        │
        ▼
  RIFE 프레임 보간 (경계 스무딩)
        │
        ▼
  FFmpeg 연결 + 오디오 합성
        │
        ▼
  최종 튜토리얼 영상
```

---

## 빠른 시작

### 사전 요구사항

| 소프트웨어 | 버전 | 비고 |
|-----------|------|------|
| Node.js   | 20+  | API Server |
| Python    | 3.10+ | Worker |
| Redis     | 7+   | Job Queue |
| FFmpeg    | 6+   | 영상 처리 |

### 설치

```bash
# 저장소 복제
git clone https://github.com/your-org/dance-coaching.git
cd dance-coaching

# 자동 설치 (의존성 + 가상환경)
./scripts/setup.sh        # Linux / macOS
.\scripts\setup.ps1       # Windows
```

### 실행 (Cloud 모드 - Kling API)

```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일에서 KLING_API_KEY=your_key 설정

# Docker Compose (권장)
docker compose up --build

# 또는 수동 실행:
# Terminal 1: API Server
cd server && npm run dev

# Terminal 2: Worker
cd worker && python -m src.main
```

### 실행 (Local GPU 모드 - MimicMotion)

```bash
# MimicMotion 모델 다운로드 (~15GB)
./scripts/setup-mimicmotion.sh

# .env 파일에서 GENERATION_BACKEND=local 설정

# Docker Compose (GPU 지원)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

---

## API Reference

### POST /api/generate

튜토리얼 영상 생성 작업을 생성합니다.

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `avatarImage` | file | O | 아바타 이미지 (PNG/JPG) |
| `referenceVideo` | file | O | 참조 댄스 영상 (MP4) |
| `backend` | string | X | `cloud` 또는 `local` (기본값: 서버 설정) |
| `maxDuration` | number | X | 최대 영상 길이(초), 1-300 |
| `segmentLength` | number | X | 세그먼트 최대 길이(초), 3-30 |

```bash
curl -X POST http://localhost:3000/api/generate \
  -F "avatarImage=@avatar.png" \
  -F "referenceVideo=@dance.mp4" \
  -F "backend=cloud"
```

**Response (201):**
```json
{
  "jobId": "abc123",
  "message": "Generation job created"
}
```

### GET /api/generate/:jobId

생성 작업의 상태를 조회합니다.

```bash
curl http://localhost:3000/api/generate/abc123
```

**Response (200):**
```json
{
  "jobId": "abc123",
  "status": "completed",
  "progress": 100,
  "result": {
    "outputUrl": "/storage/outputs/abc123.mp4",
    "duration": 30.5,
    "segmentCount": 3,
    "backend": "cloud"
  }
}
```

### POST /api/coach

댄스 코칭 분석 작업을 생성합니다.

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `userVideo` | file | O | 사용자 댄스 영상 (MP4) |
| `referenceVideo` | file | O | 참조 댄스 영상 (MP4) |

```bash
curl -X POST http://localhost:3000/api/coach \
  -F "userVideo=@my_dance.mp4" \
  -F "referenceVideo=@reference.mp4"
```

**Response (201):**
```json
{
  "jobId": "def456",
  "message": "Coaching job created"
}
```

### GET /api/coach/:jobId

코칭 분석 결과를 조회합니다.

```bash
curl http://localhost:3000/api/coach/def456
```

**Response (200):**
```json
{
  "jobId": "def456",
  "status": "completed",
  "overall_score": 74.5,
  "joint_scores": {
    "left_arm": 72.0,
    "right_arm": 75.0,
    "left_leg": 68.0,
    "right_leg": 70.0,
    "torso": 80.0,
    "head": 85.0
  },
  "feedback": [
    "Good effort! Some areas need improvement.",
    "Left leg needs improvement (score: 68.0%). Focus on matching the reference movement more closely."
  ]
}
```

### GET /api/config

현재 서버 설정을 조회합니다.

```bash
curl http://localhost:3000/api/config
```

**Response (200):**
```json
{
  "generationBackend": "cloud",
  "maxVideoDurationSec": 180,
  "segmentMaxLengthSec": 10
}
```

### WebSocket /api/ws/jobs/:jobId

작업 진행률을 실시간으로 수신합니다.

```javascript
const ws = new WebSocket("ws://localhost:3000/api/ws/jobs/abc123");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type: "progress" | "completed" | "failed"
  // data.progress: 0-100
  // data.result: 완료 시 결과 객체
  // data.error: 실패 시 에러 메시지
};
```

---

## 환경 변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `SERVER_PORT` | `3000` | API 서버 포트 |
| `REDIS_URL` | `redis://localhost:6379` | Redis 연결 URL |
| `GENERATION_BACKEND` | `cloud` | 생성 백엔드 (`cloud` / `local`) |
| `KLING_API_KEY` | (필수: cloud) | Kling API 인증 키 |
| `KLING_API_BASE_URL` | `https://api.klingai.com/v1` | Kling API 베이스 URL |
| `MIMICMOTION_MODEL_DIR` | `./models/mimicmotion` | MimicMotion 모델 경로 |
| `MIMICMOTION_REPO_DIR` | `./vendor/MimicMotion` | MimicMotion 리포지토리 경로 |
| `MAX_VIDEO_DURATION_SEC` | `180` | 최대 입력 영상 길이(초) |
| `SEGMENT_MAX_LENGTH_SEC` | `10` | 세그먼트 최대 길이(초) |
| `RIFE_MODEL_DIR` | `./models/rife` | RIFE 인터폴레이션 모델 경로 |
| `RIFE_INTERPOLATION_FRAMES` | `2` | 경계당 보간 프레임 수 |
| `STORAGE_DIR` | `./storage` | 파일 저장 디렉토리 |
| `WORKER_CONCURRENCY` | `1` | Worker 동시 처리 수 |

---

## 테스트

```bash
# 전체 테스트 (Server + Worker)
./scripts/test.sh

# Server 테스트 (Vitest)
cd server && npm test

# Worker 테스트 (pytest)
cd worker && pytest tests/ -v

# Worker 커버리지 포함
cd worker && pytest tests/ -v --cov=src --cov-report=term-missing

# GPU 테스트 포함 (CUDA 필요)
CUDA_VISIBLE_DEVICES=0 pytest tests/ -v -m "not api"

# API 테스트 포함 (Kling API 키 필요)
KLING_API_KEY=your_key pytest tests/ -v -m "not gpu"
```

---

## 프로젝트 구조

```
dance-coaching/
├── server/                         # Node.js API Server
│   ├── src/
│   │   ├── domain/                 # 도메인 엔티티, Value Object, 에러
│   │   │   ├── entities/
│   │   │   ├── value-objects/
│   │   │   └── errors/
│   │   ├── application/            # Use Case, Port (인터페이스)
│   │   │   ├── dto/
│   │   │   ├── ports/
│   │   │   └── use-cases/
│   │   ├── infrastructure/         # Redis, BullMQ, Storage 구현체
│   │   │   ├── config/
│   │   │   ├── queue/
│   │   │   ├── redis/
│   │   │   └── storage/
│   │   ├── interface/              # HTTP 라우트, WebSocket
│   │   │   ├── http/routes/
│   │   │   ├── http/schemas/
│   │   │   └── ws/
│   │   └── di/                     # 의존성 주입 컨테이너
│   └── test/                       # Server 테스트
├── worker/                         # Python Worker
│   ├── src/
│   │   ├── domain/                 # 도메인 엔티티, Value Object, 에러
│   │   ├── application/            # Use Case, Orchestrator, Port
│   │   │   ├── ports/              # 추상 인터페이스
│   │   │   └── use_cases/          # 비즈니스 로직 실행
│   │   ├── infrastructure/         # 구현체
│   │   │   ├── audio/              # librosa 비트 감지
│   │   │   ├── backends/           # Kling API, MimicMotion
│   │   │   ├── pose/               # MediaPipe 포즈 추출
│   │   │   ├── queue/              # BullMQ Worker
│   │   │   └── stitch/             # FFmpeg, RIFE 보간
│   │   └── di/                     # 의존성 주입 컨테이너
│   └── tests/                      # Worker 테스트
│       ├── harness/                # Fake 구현체 (테스트 더블)
│       ├── unit/
│       ├── integration/
│       └── e2e/
├── shared/                         # Server-Worker 공유 스키마
│   └── schemas/
├── storage/                        # 파일 저장소
│   ├── uploads/
│   ├── outputs/
│   └── temp/
├── docker/                         # Dockerfile 모음
├── scripts/                        # 설치/실행/테스트 스크립트
├── docker-compose.yml              # Cloud 모드
├── docker-compose.gpu.yml          # GPU 모드 오버라이드
└── .env.example                    # 환경 변수 템플릿
```

---

## 기술 스택

### Server

| 기술 | 용도 |
|------|------|
| Fastify 5 | HTTP / WebSocket 서버 |
| TypeScript 5 | 타입 안전 서버 코드 |
| BullMQ 5 | Redis 기반 작업 큐 |
| Zod 3 | 요청 유효성 검증 |
| ioredis 5 | Redis 클라이언트 |
| Vitest 2 | 테스트 프레임워크 |

### Worker

| 기술 | 용도 |
|------|------|
| MediaPipe 0.10+ | 포즈 추출 (33 관절 랜드마크) |
| librosa 0.10+ | 오디오 비트 감지 |
| httpx 0.27+ | Kling API 비동기 HTTP 클라이언트 |
| OpenCV 4.9+ | 이미지/영상 처리 |
| PyTorch | MimicMotion 로컬 GPU 추론 |
| pydantic 2 | 설정 유효성 검증 |
| pytest 8 | 테스트 프레임워크 |

### Infrastructure

| 기술 | 용도 |
|------|------|
| Redis 7 | 작업 큐 브로커, 상태 저장 |
| Docker Compose | 멀티 서비스 컨테이너 오케스트레이션 |
| FFmpeg 6 | 영상 분할, 연결, 오디오 합성 |
| RIFE | 프레임 인터폴레이션 (경계 스무딩) |

---

## 라이선스

MIT License
