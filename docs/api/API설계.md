# API 설계 v1

기본 /api/v1, JSON UTF-8. 인증된 PATCH/POST/DELETE/PUT는 세션+X-CSRF-Token, org 경로는 활성 Membership 검증. 가입/로그인/확인/재설정은 사전 세션 없이 동작하되 JSON 전용 입력과 Origin 검사로 login CSRF를 차단한다. webhook은 HMAC, OAuth callback은 일회용 state로 보호한다. 알 수 없는/접근 불가 객체는 동일한 404. 입력 오류 422, 인증 401, 권한 403, 버전충돌 409, 제한 429, 외부 준비 안 됨 503. 오류 {code,message,request_id}.

## 인증과 회사
| Method | Path | 입력/반환 |
|---|---|---|
| POST | /auth/register | email,password,name → user; 확인 메일 작업 생성 |
| POST | /auth/verify-email | token → 확인 완료 |
| POST | /auth/login | email,password → user,csrf_token; 세션 쿠키 |
| GET | /auth/session | user,csrf_token,organizations |
| POST | /auth/logout | 세션 폐기 |
| POST | /auth/password-reset | email → 동일한 202 |
| POST | /auth/password-reset/confirm | token,password → 세션 전체 폐기 |
| GET/POST | /organizations | 현재 회사 / name으로 회사 생성 |
| GET/PATCH | /organizations/{org}/settings | 관리자: 자동화/보관/쿼터 |
| GET | /organizations/{org}/members | 직원 목록 |
| PATCH | /organizations/{org}/members/{user} | 관리자: role,active, 마지막 관리자 보호 |
| POST | /organizations/{org}/invitations | email,role → 초대 메일 |
| POST | /invitations/accept | token → 해당 이메일 회원 가입 |

## 회의와 회의록
| Method | org 하위 Path | 동작 |
|---|---|---|
| GET/POST | /meetings | 상태 필터·offset/limit / title,start_at,timezone,recipient_ids |
| GET/DELETE | /meetings/{id} | 상세 / 처리·발송 차단 및 삭제 |
| POST | /meetings/{id}/source | multipart file → 202 job |
| PUT | /meetings/{id}/recipients | [{user_id,email,kakao}] 사내 활성 직원만 |
| GET | /meetings/{id}/transcript | 관리자/회의 관리자만 |
| GET | /meetings/{id}/minutes | 관리자 초안, 직원 공개된 버전 |
| PUT | /meetings/{id}/minutes | expected_version,content → 새 버전 |
| GET | /meetings/{id}/minutes/{version}/pdf | 권한 재검사, application/pdf |
| POST | /meetings/{id}/approve | version → 버전/수신자 hash 승인 |
| POST | /meetings/{id}/send | version, Idempotency-Key → deliveries |
| GET | /meetings/{id}/jobs | 단계별 진행 상태 |
| GET | /deliveries | 채널·상태·수신자별 이력 |
| POST | /deliveries/{id}/retry | unknown은 중복 위험 확인값 필요 |

## 외부 연결
POST /organizations/{org}/integrations/{zoom|kakao}/authorize → authorize_url.
GET /integrations/{provider}/callback?code&state → state 일회 검증 후 토큰 암호 저장.
GET/DELETE /organizations/{org}/integrations/{id} → 연결 상태/해제.
POST /webhooks/zoom → challenge 또는 서명 검증, 검증된 외부 account/user로 라우팅.
GET /organizations/{org}/usage → 사용량/상한.
GET /health/live, /health/ready → liveness/DB readiness. 비밀값 제외.

## 계약
- ID UUID string, 시작/생성은 timezone-aware ISO8601 UTC, timezone은 IANA.
- 목록 {items,total,offset,limit}; limit 1..100.
- Summary {title,overview:{text,evidence_ids},discussions:[{text,evidence_ids}],decisions:[{text,evidence_ids}],actions:[{text,assignee_id|null,assignee_name|null,due_raw|null,due_at|null,evidence_ids}],warnings:[]}. warnings의 모호성은 자동 발송을 차단한다.
- 내용 검증은 근거 존재 확인이며 의미적 정확성을 보장하지 않음.
- 자동 발송은 사람이 승인한 정책 버전을 참조한 system_policy 승인.
- 전달 상태 accepted는 외부 서비스 접수, 열람/도착 보장 아님.
- live OpenAPI는 /openapi.json. 실제 구현 계약을 자동 생성해 docs/api/openapi.json에 동기화한다.
- 비밀값/토큰/녹취 본문을 오류·access log에 남기지 않는다.

