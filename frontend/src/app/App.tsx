import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { authRepository, AuthView, useAuthVM } from '../features/auth';
import {
  meetingsRepository,
  MeetingsView,
  MeetingDetailView,
  useMeetingsVM,
  useMeetingDetailVM,
} from '../features/meetings';
import {
  workspaceRepository,
  WorkspaceView,
  useWorkspaceVM,
} from '../features/workspace';
import { ErrorNotice, Loading } from '../shared/ui';

export function App() {
  const auth = useAuthVM(authRepository);
  const cache = useQueryClient();
  const [selected, setSelected] = useState(
    new URLSearchParams(location.search).get('org') || ''
  );
  const [companyName, setCompanyName] = useState('');
  const [error, setError] = useState('');

  if (auth.loading) return <Loading />;
  if (!auth.user) return <AuthView vm={auth} />;

  const company =
    auth.companies.find(c => c.id === selected) || auth.companies[0];

  if (!company) {
    return (
      <main className="onboarding">
        <div className="brand">
          <span className="brand-icon">M</span> meeting agent
        </div>
        <section className="card">
          <p className="eyebrow">FIRST WORKSPACE</p>
          <h1>팀의 기록을 시작하세요</h1>
          <p className="muted">
            회사를 만들거나, 초대 메일의 링크로 회사에 참여하세요.
          </p>
          <form
            onSubmit={e => {
              e.preventDefault();
              void auth
                .createCompany(companyName)
                .catch(e => setError(e.message));
            }}
          >
            <label>
              회사 이름
              <input
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                required
                maxLength={100}
              />
            </label>
            <ErrorNotice message={error} />
            <button className="primary">회사 만들기</button>
          </form>
        </section>
        <button onClick={() => void auth.logout()}>로그아웃</button>
      </main>
    );
  }

  const handleCompanyChange = (orgId: string) => {
    void cache.cancelQueries();
    cache.removeQueries({ predicate: q => q.queryKey[0] !== 'session' });
    setSelected(orgId);
  };

  return (
    <>
      <ErrorNotice message={auth.error} />
      {auth.message && (
        <p role="status" className="notice">
          {auth.message}
        </p>
      )}
      <WorkspaceShell
        key={company.id}
        org={company.id}
        role={company.role}
        userName={auth.user.name}
        companies={auth.companies}
        selectedCompanyId={company.id}
        onSelectCompany={handleCompanyChange}
        onLogout={() => void auth.logout()}
      />
    </>
  );
}

interface WorkspaceShellProps {
  org: string;
  role: string;
  userName: string;
  companies: { id: string; name: string }[];
  selectedCompanyId: string;
  onSelectCompany: (id: string) => void;
  onLogout: () => void;
}

const ROLE_LABELS: Record<string, string> = {
  admin: '회사 관리자',
  manager: '회의 관리자',
  member: '일반 직원',
};

function WorkspaceShell({
  org,
  role,
  userName,
  companies,
  selectedCompanyId,
  onSelectCompany,
  onLogout,
}: WorkspaceShellProps) {
  const [section, setSection] = useState('meetings');
  const [meeting, setMeeting] = useState(
    new URLSearchParams(location.search).get('meeting') || ''
  );

  const meetings = useMeetingsVM(meetingsRepository, org);
  const workspace = useWorkspaceVM(workspaceRepository, org, role);
  const isManager = role !== 'member';

  const navItems: [string, string, string][] = [
    ['meetings', '▤', '회의 기록'],
    ['members', '♙', '직원 관리'],
    ['integrations', '⌘', '서비스 연결'],
    ...(isManager ? ([['deliveries', '↗', '발송 이력']] as [string, string, string][]) : []),
    ['settings', '⚙', '자동화 설정'],
  ];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">M</span> meeting agent
        </div>

        <div className="company-switch">
          <select
            aria-label="회사 선택"
            value={selectedCompanyId}
            onChange={e => onSelectCompany(e.target.value)}
          >
            {companies.map(c => (
              <option value={c.id} key={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <small>팀 워크스페이스</small>
        </div>

        <nav aria-label="주 메뉴">
          {navItems.map(([key, icon, title]) => (
            <button
              key={key}
              className={section === key ? 'active' : ''}
              onClick={() => {
                setSection(key);
                setMeeting('');
              }}
            >
              <span aria-hidden="true">{icon}</span>
              {title}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <strong>{userName}</strong>
          <small>{ROLE_LABELS[role] || role}</small>
          <button onClick={onLogout}>로그아웃</button>
        </div>
      </aside>

      <main className="content">
        <div className="topbar">
          <span>WORKSPACE / {section === 'meetings' ? 'MEETINGS' : 'SETTINGS'}</span>
          <span className="privacy">
            <span />
            회사 전용 공간
          </span>
        </div>

        {section === 'meetings' ? (
          meeting ? (
            <MeetingDetailContainer
              org={org}
              id={meeting}
              isManager={isManager}
              members={workspace.members}
              back={() => setMeeting('')}
            />
          ) : (
            <MeetingsView vm={meetings} open={setMeeting} isManager={isManager} />
          )
        ) : (
          <WorkspaceView vm={workspace} section={section} role={role} />
        )}
      </main>
    </div>
  );
}

function MeetingDetailContainer({
  org,
  id,
  isManager,
  members,
  back,
}: {
  org: string;
  id: string;
  isManager: boolean;
  members: { id: string; name: string; email: string; active: boolean }[];
  back: () => void;
}) {
  const vm = useMeetingDetailVM(meetingsRepository, org, id, isManager);
  return (
    <MeetingDetailView
      vm={vm}
      members={members}
      isManager={isManager}
      back={back}
    />
  );
}

