import type { MeetingsViewModel } from '../viewmodels/useMeetingsVM';
import { statusLabel } from '../model/types';
import { Empty, ErrorNotice, Loading } from '../../../shared/ui';

interface MeetingsViewProps {
  vm: MeetingsViewModel;
  open: (id: string) => void;
  isManager: boolean;
}

export function MeetingsView({ vm, open, isManager }: MeetingsViewProps) {
  const reviewCount = vm.items.filter(m => m.status === 'review_required').length;
  const completedCount = vm.items.filter(m => m.status === 'completed').length;

  return (
    <>
      <header className="page-heading">
        <div>
          <p className="eyebrow">MEETING WORKSPACE</p>
          <h1>회의 기록</h1>
          <p className="muted">대화를 기록하고, 결정한 일을 팀에게 전달하세요.</p>
        </div>
        <span className="count">{vm.total}개의 회의</span>
      </header>

      <div className="metrics">
        <div>
          <span>전체 회의</span>
          <strong>{vm.total}</strong>
        </div>
        <div>
          <span>검토 대기</span>
          <strong>{reviewCount}</strong>
        </div>
        <div>
          <span>처리 완료</span>
          <strong>{completedCount}</strong>
        </div>
      </div>

      <ErrorNotice message={vm.error} />
      {vm.error && (
        <button onClick={() => void vm.reload()}>다시 불러오기</button>
      )}

      {isManager && (
        <form
          className="card inline-form"
          onSubmit={e => {
            e.preventDefault();
            void vm.create().then(id => {
              if (id) open(id);
            });
          }}
        >
          <label>
            회의 제목
            <input
              placeholder="예: 제품팀 주간 회의"
              value={vm.title}
              onChange={e => vm.setTitle(e.target.value)}
              required
              maxLength={200}
            />
          </label>
          <label>
            회의 일시
            <input
              type="datetime-local"
              value={vm.start}
              onChange={e => vm.setStart(e.target.value)}
              required
            />
          </label>
          <button className="primary" disabled={vm.busy}>
            회의 등록
          </button>
        </form>
      )}

      <section className="card">
        <div className="section-heading">
          <h2>최근 회의</h2>
          <span className="muted">최신순</span>
        </div>

        {vm.loading ? (
          <Loading />
        ) : !vm.items.length ? (
          <Empty>
            아직 회의가 없습니다. 회의를 등록하거나 Zoom을 연결해 주세요.
          </Empty>
        ) : (
          <div className="meeting-list">
            {vm.items.map(item => (
              <button
                className="meeting-row"
                key={item.id}
                onClick={() => open(item.id)}
              >
                <span className="meeting-icon">▤</span>
                <span className="meeting-copy">
                  <strong>{item.title}</strong>
                  <small>
                    {new Date(item.start_at).toLocaleString('ko-KR')}
                  </small>
                </span>
                <span className={'badge ' + item.status}>
                  {statusLabel(item.status)}
                </span>
                <span aria-hidden="true">→</span>
              </button>
            ))}
          </div>
        )}

        <div className="actions">
          <button
            disabled={vm.page === 0}
            onClick={() => vm.setPage(vm.page - 1)}
          >
            이전
          </button>
          <span>{vm.page + 1} 페이지</span>
          <button
            disabled={(vm.page + 1) * 30 >= vm.total}
            onClick={() => vm.setPage(vm.page + 1)}
          >
            다음
          </button>
        </div>
      </section>
    </>
  );
}


