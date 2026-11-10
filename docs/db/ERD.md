# ERD

논리 ERD. org_id를 가진 엔터티는 회사 격리 대상. FK는 가능한 경우 org_id를 포함한다.

```mermaid
erDiagram
 USER ||--o{ SESSION : authenticates
 USER ||--o{ ONE_TIME_TOKEN : verifies
 USER ||--o{ MEMBERSHIP : joins
 ORGANIZATION ||--o{ MEMBERSHIP : contains
 ORGANIZATION ||--o{ INTEGRATION : connects
 USER ||--o{ INTEGRATION : authorizes
 ORGANIZATION ||--o{ MEETING : owns
 MEETING ||--o{ RECIPIENT : addresses
 MEMBERSHIP ||--o{ RECIPIENT : receives
 MEETING ||--o{ TRANSCRIPT : records
 MEETING ||--o{ MINUTES : versions
 MINUTES ||--o{ APPROVAL : approves
 MINUTES ||--o{ DELIVERY : distributes
 MEMBERSHIP ||--o{ DELIVERY : receives
 MEETING ||--o{ JOB : processes
 ORGANIZATION ||--o{ AUDIT_EVENT : audits
 ORGANIZATION ||--o{ USAGE : meters
 USER { string id PK
 string email UK
 boolean verified }
 ORGANIZATION { string id PK
 string name
 json settings }
 MEMBERSHIP { string org_id PK,FK
 string user_id PK,FK
 string role
 boolean active }
 MEETING { string id PK
 string org_id FK
 string external_id
 string status }
 MINUTES { string id PK
 string org_id FK
 string meeting_id FK
 int version
 json content
 string content_hash
 boolean published }
 DELIVERY { string id PK
 string org_id FK
 string meeting_id FK
 int version
 string user_id FK
 string channel
 string status }
 JOB { string id PK
 string org_id FK
 string meeting_id FK
 string kind
 string state
 int fence }
```

WebhookReceipt는 서명 검증 이벤트의 중복 해시만 전역 보관하며 공개 API에 노출하지 않는다. 문서의 actions는 회의록 JSON 안의 값 객체로 관리하여 불필요한 별도 ORM 테이블을 줄인다. 현재 물리 스키마는 마이그레이션과 docs/api/openapi.json을 기준으로 추적한다.

