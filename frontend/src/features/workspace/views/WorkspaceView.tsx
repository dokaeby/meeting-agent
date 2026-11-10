import type { WorkspaceViewModel } from '../viewmodels/useWorkspaceVM';
import { ErrorNotice } from '../../../shared/ui';
import { MembersTab } from './MembersTab';
import { IntegrationsTab } from './IntegrationsTab';
import { DeliveriesTab } from './DeliveriesTab';
import { SettingsTab } from './SettingsTab';

interface WorkspaceViewProps {
  vm: WorkspaceViewModel;
  section: string;
  role: string;
}

const SECTION_TITLES: Record<string, string> = {
  members: '직원 관리',
  integrations: '서비스 연결',
  deliveries: '발송 이력',
  settings: '자동화 설정',
};

export function WorkspaceView({ vm, section, role }: WorkspaceViewProps) {
  return (
    <>
      <header className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE SETTINGS</p>
          <h1>{SECTION_TITLES[section] || '설정'}</h1>
          <p className="muted">회사의 회의 운영을 한 곳에서 관리하세요.</p>
        </div>
      </header>

      <ErrorNotice message={vm.error} />
      {vm.notice && (
        <p className="notice" role="status">
          {vm.notice}
        </p>
      )}

      {section === 'members' && <MembersTab vm={vm} role={role} />}
      {section === 'integrations' && <IntegrationsTab vm={vm} role={role} />}
      {section === 'deliveries' && <DeliveriesTab vm={vm} />}
      {section === 'settings' && <SettingsTab vm={vm} role={role} />}
    </>
  );
}
export { MembersTab, IntegrationsTab, DeliveriesTab, SettingsTab };


