import type { AuthViewModel } from '../viewmodels/useAuthVM';
import { ErrorNotice } from '../../../shared/ui';

export function AuthView({ vm }: { vm: AuthViewModel }) {
  return (
    <main className="auth-layout">
      <section className="auth-story">
        <div className="brand">
          <span className="brand-icon">M</span> meeting agent
        </div>
        <p className="eyebrow">회의에서 실행까지</p>
        <h1>
          대화가 끝나면,
          <br />
          다음 일이 시작됩니다.
        </h1>
        <p>
          회의록 정리와 전달은 맡기고,
          <br />
          팀은 중요한 결정에 집중하세요.
        </p>
        <div className="story-steps">
          <span>01 회의 수집</span>
          <span>02 근거와 함께 요약</span>
          <span>03 담당자에게 전달</span>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <p className="eyebrow">TEAM WORKSPACE</p>
          <h2>
            {vm.mode === 'register'
              ? '새 계정 만들기'
              : vm.mode === 'reset'
              ? '비밀번호 재설정'
              : '다시 만나 반갑습니다'}
          </h2>
          <p className="muted">회사별로 안전하게 관리하는 회의 기록</p>

          <form
            onSubmit={e => {
              e.preventDefault();
              void vm.submit();
            }}
          >
            {vm.mode === 'register' && (
              <label>
                이름
                <input
                  value={vm.name}
                  onChange={e => vm.setName(e.target.value)}
                  required
                  autoComplete="name"
                />
              </label>
            )}

            {!(vm.mode === 'reset' && vm.hasReset) && (
              <label>
                이메일
                <input
                  type="email"
                  value={vm.email}
                  onChange={e => vm.setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </label>
            )}

            {(vm.mode !== 'reset' || vm.hasReset) && (
              <label>
                비밀번호
                <input
                  type="password"
                  value={vm.password}
                  onChange={e => vm.setPassword(e.target.value)}
                  required
                  minLength={vm.mode === 'login' ? 1 : 12}
                  autoComplete={
                    vm.mode === 'register' || vm.mode === 'reset'
                      ? 'new-password'
                      : 'current-password'
                  }
                />
              </label>
            )}

            <ErrorNotice message={vm.error} />
            {vm.message && (
              <p role="status" className="notice">
                {vm.message}
              </p>
            )}

            <button className="primary wide" disabled={vm.busy}>
              {vm.busy
                ? '처리 중…'
                : vm.mode === 'register'
                ? '가입하기'
                : vm.mode === 'reset'
                ? '재설정 요청'
                : '로그인'}
            </button>
          </form>

          <div className="auth-links">
            <button
              onClick={() => vm.setMode(vm.mode === 'register' ? 'login' : 'register')}
            >
              {vm.mode === 'register' ? '로그인으로' : '계정 만들기'}
            </button>
            <button onClick={() => vm.setMode('reset')}>비밀번호 찾기</button>
          </div>
        </div>
      </section>
    </main>
  );
}

