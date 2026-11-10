# Meeting Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax. User explicitly authorized implementation after all documents; do not pause for another approval.

**Goal:** 회사별 Zoom 회의록 생성과 승인 기반 이메일·카카오 발송 SaaS.
**Architecture:** React MVVM + FastAPI 모듈형 단일 서버, PostgreSQL 작업 원장, Celery 실행자. 한 작성자와 읽기 전용 검토자.
**Tech Stack:** Python3.12, TypeScript, React/Vite, SQLAlchemy/Alembic, Celery/Redis, pytest/Vitest/Playwright.
**Spec:** ../../설계/요구사항-상세설계.md 및 ../../api/API설계.md, ../../db/DB설계.md.

## Global Constraints
회사 격리, 파일500줄 미만, API 키 비공개, 실제 발송/배포/commit/push 금지. 명시적 fake 모드는 개발·테스트만. 사용자 지정 경로에 구현. aio4는 Git 저장소가 아니므로 신규 폴더가 독립 작성 범위이며 기존 저장소를 수정하지 않는다. Ponytail: 작업 테이블을 outbox로 함께 사용, 값 객체는 JSON, 사용하지 않는 추상화 금지.

## Review Focus
- 늦은 응답/전환으로 이전 회사 데이터 표시 → Task5 hook 테스트.
- unknown 발송을 일반 실패로 취급해 중복 전송 → Task4 timeout 테스트.
- 수신자 변경 후 옛 승인 재사용 → Task3 API 테스트.
- RLS 없는 SQLite 통과를 운영 검증으로 오인 → Task6 별도 PG 검증.
- 초대/회사 수신자 지정만으로 초안 노출 → Task2/3 권한 테스트.

## Task 1: 기초와 인증·회사
Files: backend/pyproject.toml, src/meeting_agent/{config,db,models,security,main}.py, modules/identity.py, modules/organizations.py, tests/unit/test_security.py, tests/integration/test_identity.py.
Consumes: 환경변수. Produces: create_app(settings), DB session dependency, require_member(org,user), csrf guard.
- [ ] 실패 테스트: 암호 검증, 미인증401, CSRF403, 가입/확인/회사 생성/초대수락, 교차회사404.
- [ ] pytest 실행해 구현 누락 실패 확인.
- [ ] 최소 구현, 활성 세션/멤버십/토큰 해시 저장. API 입력 경계 검증.
- [ ] focused suite 통과, Alembic schema 작성.

## Task 2: 회의·수신자·입력
Files: modules/meetings.py, schemas.py, storage.py, tests/integration/test_meetings.py.
Consumes: Task1 member/context. Produces: 회의 조회/생성/파일 업로드, recipient snapshot.
- [ ] 실패 테스트: 2회사404, 일반직원 초안/녹취 거부, 수신자 변경 무효화, 위장/초과 파일 거부.
- [ ] RED 확인 후 구현. 업로드/파싱은 입력 크기 제한, 비공개 파일 키.
- [ ] focused suite 실행, 정상/실패 경로 검증.

## Task 3: 요약·PDF·승인
Files: modules/minutes.py, integrations/groq.py, documents.py, jobs/pipeline.py, tests/unit/test_summary.py.
Consumes: transcript segments. Produces: validate_summary(content,segments), immutable Minutes, approval snapshot.
- [ ] 근거 없는 요약, 동명이인·비정상JSON·문서 버전 변경/수신자 변경 승인 실패 테스트 RED.
- [ ] Groq HTTP 어댑터·명시적 test provider·한국어 PDF 구현.
- [ ] 문서 접근·PDF 추출·버전 인수 테스트 통과.

## Task 4: 외부 연동·작업자·발송
Files: integrations/{oauth,zoom,kakao,mail}.py, modules/integrations.py, modules/deliveries.py, jobs/worker.py, tests/integration/test_providers.py.
Consumes: Task1 crypto/session, Task3 approval. Produces: Zoom webhook receipts, durable jobs, dispatch_pending, deliver_once.
- [ ] OAuth state 재사용/Zoom HMAC·중복/timeout unknown/fence·재시도 테스트 RED.
- [ ] 토큰 암호화·갱신·provider 어댑터·DB claim·Celery/Beat 구현.
- [ ] 외부 발송 없이 mock 계약 테스트 통과. 운영 미설정 실패 명확히.

## Task 5: React MVVM UI
Files: frontend/src/{app,shared,features}/**, package.json, tsconfig, eslint, frontend/e2e.
Consumes: API 계약. Produces: Repository, use*VM, 한국어 View.
- [ ] 모델/VM(loading,error,org switch,duplicate submit) 테스트 RED.
- [ ] MVVM 레이어와 기능별 화면 구현. View에서 HTTP import ESLint 금지.
- [ ] Vitest/typecheck/lint/build, Playwright 핵심 여정.

## Task 6: 운영·문서·검증
Files: config/compose.yaml, Dockerfiles, migrations, docs/automation/run.py, docs/automation/검증결과.md, README.
Consumes: Task1–5. Produces: 실행 환경, 자동화 runner, OpenAPI, source-bound 결과.
- [ ] PG RLS/unique/동시성 테스트와 UI E2E 작성.
- [ ] 가용 환경 검사, 실행 가능한 gate 전부 실행. 미실행 항목은 별도 표기.
- [ ] 독립 코드 검토, 중요 발견은 재현 테스트 RED→GREEN 후 수정.
- [ ] 소스 hash·검증 명령·결과·외부 계정 설정 필요 항목 기록.

## 사용자 지시에 따른 실행
문서 전부 작성 및 교차 검토 후 위 순서로 중단 없이 구현. 자동 commit/push 없음. credential 없는 외부 검증과 환경 부재는 완료한 것으로 표시하지 않는다.

