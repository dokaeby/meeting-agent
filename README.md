# Meeting Agent

회사별 Zoom 회의록 자동 생성 및 승인 기반 이메일·카카오톡 발송 SaaS 솔루션입니다.

---

## 1. 핵심 아키텍처 및 철학 (Ponytail 원칙)

본 프로젝트는 **Ponytail** 원칙(최소 코드, 실용적 설계, 불필요한 계층화 및 추상화 배제)을 기반으로 구축되었습니다:
1. **작업 테이블(Job)을 Event Outbox로 단일화**: 분산 트랜잭션 및 별도 이중 상태 테이블을 만들지 않고, DB `jobs` 테이블을 작업 큐이자 Outbox로 일원화하여 트랜잭션 안전성과 복구 보장.
2. **복합 엔티티 대신 JSON 값 객체 활용**: 회의록 요약, 근거 구간, 경고 목록 등을 정규화된 테이블로 과도하게 쪼개지 않고 정형 JSON으로 처리하여 스키마 단순화 및 생산성 극대화.
3. **사용하지 않는 추상화 금지**: 리포지토리/서비스 계층의 과도한 인터페이스화를 지양하고, React MVVM (ViewModel / View / API) 구조와 FastAPI 기능별 모듈(Feature Modules)로 직관적으로 구성.
4. **안전한 테넌트 격리**: 회사(Organization) 단위의 철저한 접근 제어 및 데이터 격리.

---

## 2. 기술 스택

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery / Redis (비동기 작업 및 스케줄링)
- **Frontend**: TypeScript, React 19, Vite, TanStack Query, React MVVM 아키텍처
- **AI & Integrations**: Groq API (STT & Summary), Zoom OAuth & Webhook, Kakao Talk API, SMTP (Mailpit)
- **Quality & Automation**: Pytest, Ruff, Vitest, Testing Library, Playwright (E2E)

---

## 3. 디렉토리 구조

```text
meeting-agent/
├── backend/                  # FastAPI 백엔드
│   ├── src/meeting_agent/    # 핵심 소스코드 (인증, 회사, 회의, 회의록, 발송, 연동)
│   ├── tests/                # 단위 및 통합 테스트 (pytest)
│   ├── migrations/           # Alembic 데이터베이스 마이그레이션
│   └── pyproject.toml        # 의존성 및 도구 설정
├── frontend/                 # React 프론트엔드 (MVVM)
│   ├── src/                  # App, Shared UI, Features (auth, meetings, workspace)
│   ├── e2e/                  # Playwright E2E 사용자 시나리오 테스트
│   └── package.json          # 프론트엔드 의존성
├── config/                   # Docker Compose 및 인프라 구성
│   └── compose.yaml          # PG, Redis, Mailpit, API, Worker, Web 통합 실행
├── docs/                     # 상세 설계 및 문서
│   ├── 설계/                 # 요구사항, 아키텍처, MVVM 상세
│   ├── api/                  # API 명세 및 openapi.json
│   ├── db/                   # DB 설계 및 ERD
│   ├── tests/                # 테스트 전략 문서
│   └── automation/           # 자동화 러너(run.py), 검증결과.md, 테스트 증거
└── var/                      # 로컬 테스트 DB 및 임시 파일 저장소
```

---

## 4. 로컬 실행 및 테스트

### 4.1 품질 게이트 전체 실행 (All-in-One)

백엔드 단위/통합 테스트, 코드 스타일 린트/포맷, 프론트엔드 타입/단위 테스트/린트/빌드, OpenAPI 스키마 내보내기, Playwright E2E 테스트를 한 번에 검증합니다:

```bash
python docs/automation/run.py --ui
```

### 4.2 백엔드 개발 서버 실행

```bash
cd backend
python -m uvicorn meeting_agent.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

### 4.3 프론트엔드 개발 서버 실행

```bash
cd frontend
npm run dev
```

### 4.4 Docker Compose 전체 환경 실행

```bash
docker compose -f config/compose.yaml up --build
```

