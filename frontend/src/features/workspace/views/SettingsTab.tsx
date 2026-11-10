import { useState } from 'react';
import type { WorkspaceViewModel } from '../viewmodels/useWorkspaceVM';
import type { Policy } from '../model/types';

interface SettingsTabProps {
  vm: WorkspaceViewModel;
  role: string;
}

export function SettingsTab({ vm, role }: SettingsTabProps) {
  if (!vm.policy) return null;

  return (
    <PolicyForm
      key={vm.policy.policy_version}
      policy={vm.policy}
      save={vm.saveSettings}
      busy={vm.busy}
      disabled={role !== 'admin'}
    />
  );
}

function PolicyForm({
  policy,
  save,
  busy,
  disabled,
}: {
  policy: Policy;
  save: (p: Policy) => Promise<boolean | undefined>;
  busy: boolean;
  disabled: boolean;
}) {
  const [draft, setDraft] = useState(policy);

  return (
    <form
      className="card settings-form"
      onSubmit={e => {
        e.preventDefault();
        void save(draft);
      }}
    >
      <h2>처리 및 발송 정책</h2>
      <p className="muted">
        기본은 검토 후 발송입니다. 자동 발송도 모호한 담당자·기한이 있으면 검토를 요청합니다.
      </p>

      <label className="check">
        <input
          type="checkbox"
          checked={draft.ai_consent}
          disabled={disabled}
          onChange={e => setDraft({ ...draft, ai_consent: e.target.checked })}
        />
        녹음·녹취의 외부 AI 처리를 확인하고 동의합니다.
      </label>

      <label className="check">
        <input
          type="checkbox"
          checked={draft.auto_send}
          disabled={disabled}
          onChange={e => setDraft({ ...draft, auto_send: e.target.checked })}
        />
        조건을 통과한 AI 회의록을 사람의 내용 검토 없이 자동 발송합니다.
      </label>

      {(
        [
          'retention_days',
          'audio_retention_days',
          'audit_retention_days',
          'monthly_meetings',
        ] as const
      ).map((key, index) => (
        <label key={key}>
          {
            [
              '회의록 보관 일수',
              '녹음 보관 일수',
              '감사 이력 보관 일수',
              '월 회의 처리 상한',
            ][index]
          }
          <input
            type="number"
            min={1}
            max={[90, 7, 180, 1000][index]}
            value={draft[key]}
            disabled={disabled}
            onChange={e =>
              setDraft({ ...draft, [key]: Number(e.target.value) })
            }
          />
        </label>
      ))}

      <button className="primary" disabled={busy || disabled}>
        설정 저장
      </button>
    </form>
  );
}

