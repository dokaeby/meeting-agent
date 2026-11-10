import type { WorkspaceViewModel } from '../viewmodels/useWorkspaceVM';
import { Empty } from '../../../shared/ui';

interface IntegrationsTabProps {
  vm: WorkspaceViewModel;
  role: string;
}

export function IntegrationsTab({ vm, role }: IntegrationsTabProps) {
  return (
    <>
      <div className="integration-grid">
        {(['zoom', 'kakao'] as const).map(provider => (
          <section className="card" key={provider}>
            <span className={'provider-logo ' + provider}>
              {provider === 'zoom' ? 'Z' : 'K'}
            </span>
            <h2>{provider === 'zoom' ? 'Zoom 회의 연결' : '카카오톡 연결'}</h2>
            <p className="muted">
              {provider === 'zoom'
                ? '연결한 호스트의 클라우드 녹음을 회의 후 가져옵니다.'
                : '본인의 카카오 계정을 연결해 회의록 알림을 받습니다.'}
            </p>
            <button
              className="primary"
              disabled={vm.busy || (provider === 'zoom' && role === 'member')}
              onClick={() => void vm.connect(provider)}
            >
              내 계정 연결
            </button>
          </section>
        ))}
      </div>

      <section className="card">
        <h2>연결된 계정</h2>
        {!vm.integrations.length ? (
          <Empty>아직 연결한 서비스가 없습니다.</Empty>
        ) : (
          vm.integrations.map(i => (
            <div className="member-row" key={i.id}>
              <strong>{i.provider}</strong>
              <span className="muted">{i.external_user}</span>
              <span className="badge">{i.status}</span>
              <button
                disabled={vm.busy}
                onClick={() => void vm.disconnect(i.id)}
              >
                연결 해제
              </button>
            </div>
          ))
        )}
      </section>
    </>
  );
}

