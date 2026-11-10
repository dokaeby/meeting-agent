# Meeting Agent 문서

사용자 승인 설계 기반 문서 모음. 2026-11-10. 문서 작성 후 구현 시작.
설계 원본 복사본의 ‘승인 대기’는 복사 시점 상태다. 사용자는 이후 문서 작성 후 구현을 명시적으로 지시했으며 최신 결정은 automation/진행기록.md와 구현 계획을 따른다.

| 문서 | 내용 |
|---|---|
| [요구사항·상세설계](설계/요구사항-상세설계.md) | 승인 설계 원본 복사 |
| [아키텍처·MVVM](설계/아키텍처-MVVM.md) | 모듈·의존성·실행 배치 |
| [API](api/API설계.md) | 엔드포인트·권한·응답 |
| [DB](db/DB설계.md) | 테이블·제약·트랜잭션 |
| [ERD](db/ERD.md) | Mermaid 엔터티 관계 |
| [자동화](automation/자동화전략.md) | CI·품질 게이트·실행 결과 저장 규칙 |
| [단위](tests/unit/단위테스트.md) | 업무 규칙·ViewModel 테스트 |
| [UI](tests/ui/UI자동화테스트.md) | Playwright 시나리오·접근성 |
| [통합](tests/integration/통합테스트.md) | DB·API·작업자·외부 계약 |
| [구현 계획](superpowers/plans/2026-11-10-meeting-agent.md) | TDD 순서·검증 명령 |

자동화 실행 스크립트와 증거는 docs/automation 아래에 보관한다. 실행 가능한 단위/통합 테스트는 backend/tests, 프런트 테스트는 frontend/src, 브라우저 테스트는 frontend/e2e에 두어 제품 모듈 가까이 유지한다. 테스트 전략과 실행 결과를 혼동하지 않는다.

