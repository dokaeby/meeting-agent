# DB 설계

PostgreSQL 16+를 운영 기준으로 사용한다. 테스트 SQLite는 빠른 업무/API 검사에만 사용 가능하며 RLS 증거가 아니다. 실제 PG 통합 검사를 별도 제공한다. UUID는 문자열 36자리, timestamp는 UTC. JSON은 요약/정책 등 경계 검증 후 저장한다.

## 테이블
| 테이블 | 핵심 컬럼 | 제약 |
|---|---|---|
| users | id,email,name,password_hash,verified,created_at | email unique |
| sessions | token_hash,user_id,csrf_hash,expires_at | 사용자 FK |
| one_time_tokens | token_hash,user_id,email,org_id,purpose,payload,expires_at | 단기·일회용 |
| organizations | id,name,settings,created_at | 회사 루트 |
| memberships | org_id,user_id,role,active | composite PK |
| integrations | id,org_id,user_id,provider,external_account,external_user,secret,status | unique(org_id,provider,user_id); provider/account/user 전역 중복 연결 금지; 비밀 암호화 |
| meetings | id,org_id,title,external_id,host_id,status,start_at,timezone,deleted | unique(org_id,id),unique(org_id,external_id) |
| recipients | org_id,meeting_id,user_id,email_enabled,kakao_enabled | 회사/회의/직원 복합 FK |
| transcripts | id,org_id,meeting_id,segments,source_key | 회사/회의 FK |
| minutes | id,org_id,meeting_id,version,content,content_hash,pdf_key,published | unique(org_id,meeting_id,version) |
| approvals | id,org_id,meeting_id,version,snapshot_hash,actor_id,kind,policy_version | 버전 승인 불변 |
| deliveries | id,org_id,meeting_id,version,user_id,channel,status,attempts,provider_id,error | unique(회의,버전,직원,채널) |
| jobs | id,org_id,meeting_id,kind,state,input_json,attempts,lease_until,fence,next_at | 작업/아웃박스 겸용, 멱등 key unique |
| webhook_receipts | id,dedupe_hash,received_at | 검증된 이벤트 중복 처리 |
| audit_events | id,org_id,actor_id,action,target_id,created_at | 본문/비밀 제외 |
| usage | org_id,period,stt_seconds,tokens,bytes | 회사·기간 unique |

## RLS와 트랜잭션
회사 소유 테이블은 org_id NOT NULL. 앱은 org ID를 신뢰하지 않고 인증된 membership을 검사한 후 트랜잭션에 set_config('app.org_id', org, true)를 설정한다. 회사 테이블 ENABLE/FORCE ROW LEVEL SECURITY와 USING/WITH CHECK 정책을 적용한다. runtime role은 NOLOGIN이 아닌 NOSUPERUSER/NOBYPASSRLS, migration owner와 분리. 회사 루트·사용자·멤버십·세션·서명검증 후 라우팅용 디렉터리는 최소 전역 조회 예외이며 코드로 권한 검사한다.

## 동시성
settings JSON에 policy_version, auto_send, activated_by, activated_at을 검증해 저장하고 변경 때 버전을 증가시킨다. Membership의 aliases JSON은 관리자 확인 별칭만 저장한다. Approval에 policy_snapshot/checks JSON을 저장하여 활성화 주체와 검사 결과를 보존한다. 관리자 권한 철회·정책 변경·수신자 변경은 발송 직전 재검사해 승인을 무효화한다.
작업 claim은 조건부 UPDATE(state/lease/fence) 후 commit. 결과 저장도 fence 일치 필요. 활성 작업 만료는 큐 재알림. 외부 발송 claim을 먼저 commit하고, 결과 불명확 시 unknown. Redis에만 존재하는 작업 금지. 승인·수신자 변경과 발송 스냅샷은 트랜잭션 잠금으로 직렬화한다.

## 인덱스
Zoom account ID→org ID 소유 매핑은 별도 integration_accounts 디렉터리로 유일하게 관리한다. 한 회사는 여러 account/host를 연결할 수 있고, 다른 회사가 같은 account를 소유할 수 없다. 서명 확인 후 디렉터리 조회에만 전역 권한을 사용하고 인증정보는 회사 컨텍스트 안에서 읽는다.
회사+회의시각, 회사+작업상태+next_at, 회사+발송상태, token_hash, 외부 provider/account/user, 회의+문서 version. 외부 ID는 반복 회의 UUID 원문 보존, API 경로에서 필요한 인코딩.

## 파일
비공개 저장소의 org/meeting/generated-id. 원본 파일명으로 경로 만들지 않음. 파일 접근은 DB 권한 재검사. PDF 생성 후 content hash와 키 기록. 기본 보관: 녹음7일, 녹취/회의록90일, 감사180일. 삭제 중인 회의는 작업 완료를 공개하지 않음.

## 마이그레이션
Alembic으로 최초 schema/RLS 생성. production에서 create_all 금지. 최초 migration은 관리자 연결, runtime은 DML만 허용. 테스트가 migration+실제 PG 제약/RLS를 검사한다. 다운그레이드는 명시적인 운영 승인 없이 실행하지 않는다.

