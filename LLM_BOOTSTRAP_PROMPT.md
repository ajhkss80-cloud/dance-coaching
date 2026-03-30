# LLM 부트스트랩 프롬프트

아래 프롬프트를 Claude나 다른 LLM에 그대로 복사해서 붙여넣으면,
자동으로 클론 → 설치 → 테스트까지 진행합니다.

---

## 프롬프트 (복사해서 사용)

```
이 GitHub 레포를 클론하고, 환경을 설치하고, 테스트를 실행해줘.

레포: https://github.com/ajhkss80-cloud/dance-coaching.git

작업 순서:
1. git clone https://github.com/ajhkss80-cloud/dance-coaching.git
2. cd dance-coaching
3. CLAUDE.md 파일을 읽어서 프로젝트 구조를 파악해
4. OS 환경을 감지해서 (Windows면 PowerShell, Linux/Mac이면 bash) 아래 설치를 진행해:
   - server/: npm install
   - worker/: python venv 생성 → pip install -r requirements.txt → pip install numpy scipy pydantic python-dotenv httpx Pillow opencv-python-headless
   - .env.example을 .env로 복사
5. 테스트 실행:
   - server: npx vitest run (68 tests 예상)
   - worker: pytest tests/ -v (122 passed, 16 skipped 예상)
6. 테스트 결과를 보고해
7. 만약 GPU가 있으면 (nvidia-smi로 확인):
   - scripts/setup-mimicmotion 스크립트 실행해서 모델 다운로드
   - .env에서 GENERATION_BACKEND=local로 변경
   - GPU 통합 테스트도 실행

프로젝트는 Clean Architecture 기반이고:
- server/ = Node.js (Fastify + TypeScript) API 서버
- worker/ = Python AI 워커 (영상 생성 + 댄스 코칭)
- 두 가지 백엔드: Cloud (Kling API) / Local GPU (MimicMotion)
- Redis/BullMQ로 서버↔워커 통신

핵심 파일 읽기 순서:
1. CLAUDE.md → 전체 가이드
2. .env.example → 환경변수
3. worker/src/application/orchestrator.py → 영상 생성 파이프라인
4. server/src/di/container.ts → 서버 DI
5. worker/src/di/container.py → 워커 DI
```

---

## 개발 작업 요청 시 프롬프트 예시

```
dance-coaching 프로젝트에서 작업해줘.

먼저 CLAUDE.md를 읽고 프로젝트 구조를 파악한 다음,
[여기에 구체적인 작업 내용을 적어]

작업 후 테스트를 돌려서 기존 190개 테스트가 깨지지 않았는지 확인해.
```

---

## 친구에게 보낼 메시지 (카톡용)

```
이거 클론해서 테스트해봐
https://github.com/ajhkss80-cloud/dance-coaching

1. git clone https://github.com/ajhkss80-cloud/dance-coaching.git
2. cd dance-coaching
3. Claude한테 이렇게 말해:
   "이 프로젝트 CLAUDE.md 읽고 설치하고 테스트 돌려줘"

끝. 나머지는 Claude가 알아서 해줌
GPU 테스트하려면: "GPU 모드로 셋업해줘" 라고 하면 됨
```
