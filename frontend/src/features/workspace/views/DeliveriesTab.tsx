import type { WorkspaceViewModel } from '../viewmodels/useWorkspaceVM';
import { statusLabel } from '../../meetings';
import { Empty } from '../../../shared/ui';

interface DeliveriesTabProps {
  vm: WorkspaceViewModel;
}

export function DeliveriesTab({ vm }: DeliveriesTabProps) {
  return (
    <section className="card">
      <h2>수신자별 발송 결과</h2>
      <p className="muted">
        접수 완료는 외부 서비스가 요청을 받았다는 뜻이며 도착·열람을 보장하지 않습니다.
      </p>
      {!vm.deliveries.length ? (
        <Empty>발송 이력이 없습니다.</Empty>
      ) : (
        vm.deliveries.map(d => (
          <div className="member-row" key={d.id}>
            <div>
              <strong>
                {vm.members.find(m => m.id === d.user_id)?.name || '직원'} ·{' '}
                {d.channel}
              </strong>
              <small>
                회의록 v{d.version} · 시도 {d.attempts}회
              </small>
            </div>
            <span className="badge">{statusLabel(d.status)}</span>
            {['failed', 'unknown'].includes(d.status) && (
              <button
                disabled={vm.busy}
                onClick={() => {
                  const ack =
                    d.status === 'unknown'
                      ? window.confirm(
                          '이미 발송되었을 수 있습니다. 중복 발송 위험을 확인하고 재시도할까요?'
                        )
                      : false;
                  if (d.status !== 'unknown' || ack) {
                    void vm.retry(d.id, ack);
                  }
                }}
              >
                재시도
              </button>
            )}
          </div>
        ))
      )}
    </section>
  );
}

