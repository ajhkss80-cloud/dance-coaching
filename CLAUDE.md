# Dance Coaching Platform - LLM Setup & Development Guide

이 문서는 LLM(Claude, ChatGPT 등)이 이 프로젝트를 클론한 후 자동으로 환경을 구성하고 테스트를 실행할 수 있도록 작성되었습니다.

---

## 1. 프로젝트 개요

AI 아바타가 참조 댄스 영상의 안무를 수행하는 튜토리얼 영상을 생성하고, 사용자의 댄스 영상을 원본과 비교 분석하여 코칭 피드백을 제공하는 플랫폼입니다.

**아키텍처**: Clean Architecture (Domain → Application → Infrastructure → Interface)
**런타임**: Node.js (Fastify + TypeScript) API Server + Python AI Worker
**통신**: Redis / BullMQ 기반 비동기 작업 큐
**백엔드 선택**: Cloud (Kling API) 또는 Local GPU (MimicMotion)

---

## 2. 즉시 설치 및 실행 (자동화 명령어)

### Windows (PowerShell)

```powershell
# 1. 의존성 설치
cd server; npm install; cd ..
cd worker; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt; cd ..

# 2. 환경 설정
Copy-Item .env.example .env

# 3. .env 수정 (GENERATION_BACKEND=cloud 기본값, Kling API 키 필요시 설정)

# 4. Redis 필요 (Docker로 실행 가능)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 5. 서버 실행 (터미널 2개 필요)
# 터미널 1:
cd server; npm run dev
# 터미널 2:
cd worker; .venv\Scripts\python -m src.main
```

### Linux / macOS / WSL

```bash
# 1. 의존성 설치
cd server && npm install && cd ..
cd worker && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..

# 2. 환경 설정
cp .env.example .env

# 3. Redis 실행
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 4. 서버 실행
cd server && npm run dev &
cd worker && .venv/bin/python -m src.main &
```

### Docker Compose (가장 간편)

```bash
cp .env.example .env
# .env 편집 후:
docker-compose up --build
```

### GPU 모드 (MimicMotion, RTX 5080/4090/5090)

```bash
# 모델 다운로드 (~15GB)
./scripts/setup-mimicmotion.sh    # Linux/Mac
.\scripts\setup-mimicmotion.ps1   # Windows

# .env에서 GENERATION_BACKEND=local 설정
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

---

## 3. 테스트 실행

### 전체 테스트 (GPU/API 없이 실행 가능)

```bash
# Server (Node.js) - 68 tests
cd server && npx vitest run

# Worker (Python) - 122 tests (16 skipped = FFmpeg/MediaPipe 통합 테스트)
cd worker && .venv/Scripts/python -m pytest tests/ -v          # Windows
cd worker && .venv/bin/python -m pytest tests/ -v              # Linux/Mac
```

### 조건부 테스트

```bash
# Kling API 실제 테스트 (API 키 필요)
KLING_API_KEY=your_key pytest tests/integration/test_kling_backend.py

# GPU 실제 테스트 (CUDA 필요)
CUDA_VISIBLE_DEVICES=0 pytest tests/integration/test_mimicmotion.py

# FFmpeg 통합 테스트 (FFmpeg 설치 필요)
pytest tests/integration/test_ffmpeg.py -v

# MediaPipe 통합 테스트 (mediapipe 설치 필요)
pytest tests/integration/test_mediapipe.py -v
```

### 예상 결과

```
Server: 68 passed, 0 failed
Worker: 122 passed, 16 skipped, 0 failed
Total: 190 passed
```

---

## 4. 디렉토리 구조

```
dance-coaching/
├── server/                          # Node.js API Server (Fastify + TypeScript)
│   ├── src/
│   │   ├── domain/                  # 비즈니스 규칙 (의존성 없음)
│   │   │   ├── entities/            # Job, GenerateRequest, CoachResult
│   │   │   ├── value-objects/       # JobId, BackendType, Score
│   │   │   └── errors/             # DomainError, ValidationError
│   │   ├── application/             # 유스케이스 + 포트(인터페이스)
│   │   │   ├── use-cases/          # StartGeneration, GetJobStatus, StartCoaching, GetCoachResult
│   │   │   ├── ports/              # IJobQueue, IStorage, IJobRepository
│   │   │   └── dto/               # GenerateDTO, CoachDTO
│   │   ├── infrastructure/          # 포트 구현체
│   │   │   ├── queue/             # BullMQAdapter (IJobQueue 구현)
│   │   │   ├── storage/           # LocalStorageAdapter (IStorage 구현)
│   │   │   ├── redis/             # RedisConnection
│   │   │   └── config/            # Zod 환경설정
│   │   ├── interface/               # HTTP 라우트 + WebSocket
│   │   │   ├── http/routes/       # generate, coach, config, files
│   │   │   ├── http/schemas/      # Zod 스키마
│   │   │   └── ws/                # job-progress WebSocket
│   │   └── di/                     # 의존성 주입 컨테이너
│   └── test/                       # 테스트
│       ├── unit/domain/            # 엔티티/VO 단위 테스트
│       ├── unit/application/       # 유스케이스 단위 테스트
│       ├── integration/            # API 통합 테스트
│       └── harness/                # TestJobQueue, TestStorage (테스트 더블)
│
├── worker/                          # Python AI Worker
│   ├── src/
│   │   ├── domain/                  # entities, value_objects, errors (순수 stdlib)
│   │   ├── application/
│   │   │   ├── ports/              # GenerationBackend ABC, PoseExtractor ABC, AudioProcessor ABC
│   │   │   │                       # VideoStitcher ABC, FrameInterpolator ABC
│   │   │   │                       # DanceAligner ABC, DanceScorerPort ABC
│   │   │   ├── use_cases/         # GenerateTutorialUseCase, CoachDanceUseCase
│   │   │   └── orchestrator.py    # 10단계 영상 생성 파이프라인
│   │   ├── infrastructure/
│   │   │   ├── backends/          # KlingBackend (Cloud), MimicMotionBackend (Local GPU)
│   │   │   ├── audio/             # LibrosaProcessor (비트 감지)
│   │   │   ├── pose/              # MediaPipeExtractor (33 키포인트)
│   │   │   ├── stitch/            # FFmpegStitcher, RIFEInterpolator, VideoSplitter
│   │   │   ├── coaching/          # DTWAligner, DanceScorer
│   │   │   └── queue/             # BullMQ Python Worker
│   │   └── di/                    # DI 컨테이너
│   └── tests/
│       ├── unit/                  # 엔티티, 오케스트레이터, DTW, 스코어러, Kling 백엔드
│       ├── integration/           # FFmpeg, MediaPipe, 파이프라인 통합
│       ├── e2e/                   # 전체 파이프라인 E2E
│       └── harness/               # FakeBackend, FakePoseExtractor, FakeStitcher 등
│
├── shared/schemas/                 # JSON Schema (Node/Python 공유)
├── scripts/                        # 셋업/테스트 스크립트 (bash + PowerShell)
├── docker/                         # Dockerfile (server, worker CPU, worker GPU)
├── .env.example                    # 환경변수 템플릿
├── docker-compose.yml              # Cloud 모드
└── docker-compose.gpu.yml          # GPU 모드
```

---

## 5. API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/generate` | 아바타 영상 생성 시작 (multipart: avatarImage + referenceVideo) |
| GET | `/api/generate/:jobId` | 생성 작업 상태/진행률 조회 |
| POST | `/api/coach` | 댄스 코칭 분석 시작 (multipart: userVideo + referenceVideo) |
| GET | `/api/coach/:jobId` | 코칭 결과 조회 |
| GET | `/api/config` | 현재 백엔드 설정 조회 |
| WS | `/api/ws/jobs/:jobId` | 실시간 진행률 WebSocket |
| GET | `/api/files/:filename` | 생성된 영상 파일 다운로드 |

### 사용 예시

```bash
# 영상 생성
curl -X POST http://localhost:3000/api/generate \
  -F "avatarImage=@avatar.png" \
  -F "referenceVideo=@dance.mp4" \
  -F "backend=cloud"

# 응답: {"jobId": "abc123", "status": "queued"}

# 상태 확인
curl http://localhost:3000/api/generate/abc123
# 응답: {"jobId": "abc123", "status": "active", "progress": 45, "progressMessage": "Generating segment 8/18..."}

# 완료 후
# 응답: {"jobId": "abc123", "status": "completed", "result": {"outputUrl": "/api/files/abc123_final.mp4", ...}}

# 코칭
curl -X POST http://localhost:3000/api/coach \
  -F "userVideo=@my_dance.mp4" \
  -F "referenceVideo=@original_dance.mp4"
```

---

## 6. 환경 변수 (.env)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SERVER_PORT` | 3000 | API 서버 포트 |
| `REDIS_URL` | redis://localhost:6379 | Redis 연결 URL |
| `GENERATION_BACKEND` | cloud | `cloud` (Kling API) 또는 `local` (MimicMotion GPU) |
| `KLING_API_KEY` | (필수 for cloud) | Kling API 키 |
| `KLING_API_BASE_URL` | https://api.klingai.com/v1 | Kling API 베이스 URL |
| `MIMICMOTION_MODEL_DIR` | ./models/mimicmotion | MimicMotion 모델 경로 |
| `MIMICMOTION_REPO_DIR` | ./vendor/MimicMotion | MimicMotion 레포 경로 |
| `STORAGE_DIR` | ./storage | 파일 저장 경로 |
| `MAX_VIDEO_DURATION_SEC` | 180 | 최대 영상 길이 (초) |
| `SEGMENT_MAX_LENGTH_SEC` | 10 | 세그먼트 최대 길이 (초) |
| `RIFE_MODEL_DIR` | ./models/rife | RIFE 모델 경로 |
| `RIFE_INTERPOLATION_FRAMES` | 2 | 경계 보간 프레임 수 |
| `WORKER_CONCURRENCY` | 1 | 동시 작업 수 |

---

## 7. 클린 아키텍처 의존성 규칙

```
Interface (HTTP/WS) → Application (UseCase) → Domain (Entity/VO) ← Infrastructure (Kling/MimicMotion/Redis)

- Domain: 외부 의존성 없음 (순수 비즈니스 로직)
- Application: Domain만 import, 포트(인터페이스/ABC)를 정의
- Infrastructure: Application의 포트를 구현
- Interface: Application의 UseCase만 호출
- DI Container: 모든 의존성 조립 (테스트 시 하네스로 교체 가능)
```

---

## 8. 영상 생성 파이프라인 (10단계)

```
1. [5%]   입력 검증 (아바타 이미지 + 참조 영상)
2. [10%]  오디오 추출 (FFmpeg)
3. [20%]  비트 감지 (librosa)
4. [25%]  세그먼트 경계 계산 (비트 기반, 최대 10초)
5. [30%]  참조 영상 분할 (FFmpeg)
6. [30-85%] 세그먼트별 생성 (Kling API 또는 MimicMotion)
7. [90%]  RIFE 프레임 보간 (경계 부드럽게)
8. [95%]  FFmpeg 이어붙이기
9. [98%]  오디오 재결합
10. [100%] 정리 + 결과 반환
```

---

## 9. 댄스 코칭 파이프라인

```
1. 사용자 영상 → MediaPipe BlazePose (33 키포인트, 3D)
2. 원본 영상 → MediaPipe BlazePose
3. DTW (Dynamic Time Warping) 정렬 (속도 차이 보정)
4. 관절별 점수 계산 (0-100):
   - left_arm, right_arm (각 15%)
   - left_leg, right_leg (각 20%)
   - torso (20%), head (10%)
5. 종합 점수 + 자연어 피드백 생성
```

---

## 10. 테스트 하네스

테스트 시 GPU/API 없이 전체 파이프라인을 검증하기 위한 테스트 더블:

| 하네스 | 대체 대상 | 위치 |
|--------|----------|------|
| `FakeBackend` | KlingBackend / MimicMotionBackend | worker/tests/harness/fake_backend.py |
| `FakeAudioProcessor` | LibrosaProcessor | worker/tests/harness/fake_audio_processor.py |
| `FakePoseExtractor` | MediaPipeExtractor | worker/tests/harness/fake_pose_extractor.py |
| `FakeStitcher` | FFmpegStitcher | worker/tests/harness/fake_stitcher.py |
| `FakeInterpolator` | RIFEInterpolator | worker/tests/harness/fake_stitcher.py |
| `TestJobQueue` | BullMQAdapter | server/test/harness/TestJobQueue.ts |
| `TestStorage` | LocalStorageAdapter | server/test/harness/TestStorage.ts |

---

## 11. 주요 기술 스택

| 영역 | 기술 |
|------|------|
| Server | Fastify 5, TypeScript, BullMQ, Zod, ioredis |
| Worker | Python 3.12, MediaPipe, librosa, httpx, numpy, scipy |
| GPU | PyTorch, MimicMotion, DWPose, RIFE |
| Infra | Redis 7, Docker, FFmpeg 6+, NVIDIA CUDA 12.4 |
| Test | Vitest (Node), Pytest (Python) |

---

## 12. 트러블슈팅

| 문제 | 해결 |
|------|------|
| `Redis connection refused` | `docker run -d -p 6379:6379 redis:7-alpine` |
| `KLING_API_KEY required` | .env에 키 설정 또는 `GENERATION_BACKEND=local` |
| `No module named 'cv2'` | `pip install opencv-python-headless` |
| `CUDA not available` | NVIDIA 드라이버 + CUDA Toolkit 설치 확인 |
| `OOM (Out of Memory)` | SEGMENT_MAX_LENGTH_SEC 줄이기 또는 해상도 낮추기 |
| `FFmpeg not found` | FFmpeg 설치: `apt install ffmpeg` 또는 `choco install ffmpeg` |
