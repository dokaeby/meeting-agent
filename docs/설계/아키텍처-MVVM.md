# 아키텍처와 MVVM

## 결정
React/TypeScript/Vite + FastAPI/Python, PostgreSQL, Celery/Redis. 하나의 저장소, API와 작업자 프로세스 분리. Ponytail: 기능 모듈을 사용하고 마이크로서비스·범용 에이전트 프레임워크·기능별 불필요한 추상 클래스를 만들지 않는다.

## 배치
브라우저 → 같은 origin의 /api 프록시 → FastAPI → PostgreSQL.
Zoom webhook → 수신 기록/작업 원자 저장 → Celery worker → Groq/STT → 회의록/PDF → 승인 → SMTP/카카오.
DB 작업 테이블을 outbox로 함께 활용해 별도 중복 큐 엔터티를 줄인다. Redis는 실행 알림이며 DB가 작업의 원장이다. Beat가 미발행·만료 작업을 복구한다.

## React 경계
- model/types.ts: DTO와 순수 업무 규칙. React/HTTP 의존 금지.
- api/repository.ts: HTTP 접근. 명시적 Repository 타입은 기능 테스트에 필요한 메서드만 포함.
- viewmodels/use*VM.ts: 상태/입력/동작/오류/비동기 흐름. Repository 주입.
- views/*View.tsx: 상태 표시와 사용자 이벤트 전달. HTTP/업무 판단 금지.
- app: 라우팅·현재 회사·인증 컨텍스트. shared: 공통 HTTP·UI·시간.
- 기능별 공개 진입점만 다른 기능에서 import. 서버 캐시 key는 회사 ID 포함.
- 회사 전환 시 요청 취소/캐시 제거. 늦게 도착한 이전 회사 응답 무시.

## 서버 경계
identity(가입/세션/초대), organizations(멤버/정책), meetings(입력/수신자), minutes(버전/승인), deliveries(발송), integrations(OAuth/외부 API), jobs(실행/복구), infrastructure(DB/암호/저장소).
라우트는 인증/검증/직렬화, 서비스는 업무 트랜잭션, 외부 어댑터는 네트워크만 담당한다. 단일 사용 함수까지 클래스화하지 않는다.

## 화면 시스템
회의 관리자용 업무 화면. 왼쪽 회사/기능 탐색, 오른쪽 회의와 작업 상세. 짙은 남색 #17243b, 청록 #087f8c, 밝은 회색 #f4f6f9. 시스템 한국어 글꼴, 4px 간격 단위, 8px 모서리, 저강도 그림자. 처리 상태는 색과 텍스트 병행, 폼 label 필수, 오류 role=alert. 모바일은 단일 열.

## 보안
세션 쿠키+CSRF, 토큰 암호화, 회사별 query/RLS/복합 FK, 내부 직원 수신, 원문 관리자만, 승인된 문서만 직원 공개. PDF도 API 권한 검사 후 제공. 실제 발송은 운영 설정과 승인된 수신자 필요.

## 상태
회의 API: waiting_source → transcribing → summarizing → rendering → review_required → ready → completed / failed. UI는 중간 세 단계를 ‘처리 중’으로 묶어 표시할 수 있다.
문서: immutable version + content hash. 수정하면 승인 무효.
발송: pending → sending → accepted / retry_wait / unknown / failed / cancelled / skipped. skipped는 채널 미연결/미선택을 명시한 결과이며 성공이 아니다.
외부 호출 결과 불명확 시 unknown. 자동 재발송으로 중복 위험을 숨기지 않는다.

## 코드 품질
파일 500줄 미만. 기능별 최소 모듈. typed 경계, lint/typecheck/단위/통합/E2E. 테스트용 외부 어댑터는 명시적인 test mode에만 허용. production에서 mock/SQLite/기본 비밀값 차단.

