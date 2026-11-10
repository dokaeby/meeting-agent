import { useEffect, useState } from 'react';
import type { MeetingDetailViewModel } from '../viewmodels/useMeetingDetailVM';
import { MinutesEditor } from './MinutesEditor';
import { statusLabel } from '../model/types';
import { ErrorNotice, Loading } from '../../../shared/ui';

export interface MemberOption {
  id: string;
  name: string;
  email: string;
  active: boolean;
}

interface RecipientCheckboxProps {
  initialChecked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}

function RecipientCheckbox({
  initialChecked,
  disabled,
  onChange,
  label,
}: RecipientCheckboxProps) {
  const [checked, setChecked] = useState(initialChecked);

  useEffect(() => {
    setChecked(initialChecked);
  }, [initialChecked]);

  return (
    <label className="check">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={e => {
          setChecked(e.target.checked);
          onChange(e.target.checked);
        }}
      />
      {label}
    </label>
  );
}

interface MeetingDetailViewProps {
  vm: MeetingDetailViewModel;
  members: MemberOption[];
  isManager: boolean;
  back: () => void;
}

export function MeetingDetailView({
  vm,
  members,
  isManager,
  back,
}: MeetingDetailViewProps) {
  const [editing, setEditing] = useState(false);

  if (vm.loading) return <Loading />;

  return (
    <>
      <button className="back" onClick={back}>
        ← 회의 목록
      </button>

      <header className="page-heading">
        <div>
          <p className="eyebrow">MEETING NOTES</p>
          <h1>{vm.meeting?.title || '회의'}</h1>
          <p className="muted">{statusLabel(vm.meeting?.status || '')}</p>
        </div>
        {vm.minutes && (
          <a className="button" href={vm.pdfUrl}>
            PDF 다운로드
          </a>
        )}
      </header>

      <ErrorNotice message={vm.error} />
      {vm.notice && (
        <p role="status" className="notice">
          {vm.notice}
        </p>
      )}

      {isManager && (
        <section className="card">
          <h2>회의 입력</h2>
          <p className="muted">
            녹취 TXT·VTT·SRT 또는 녹음 MP3·M4A·WAV를 등록하세요. 외부 AI에서 처리됩니다.
          </p>
          <label>
            녹음·녹취 파일
            <input
              type="file"
              accept=".txt,.vtt,.srt,.mp3,.m4a,.wav"
              disabled={vm.busy}
              onChange={e => {
                if (e.target.files?.[0]) void vm.upload(e.target.files[0]);
              }}
            />
          </label>
        </section>
      )}

      <div className="detail-columns">
        <section className="card minutes">
          <div className="section-heading">
            <h2>회의록</h2>
            {vm.minutes && (
              <span className="badge">
                v{vm.minutes.version} ·{' '}
                {vm.minutes.published ? '공개된 버전' : '검토 중'}
              </span>
            )}
          </div>

          {!vm.minutes ? (
            <p className="muted">입력 파일을 등록하면 회의록이 생성됩니다.</p>
          ) : (
            <>
              <p className="notice subtle">
                AI 생성 결과입니다. 결정사항과 담당자·기한을 원문과 확인하세요.
              </p>
              <h3>요약</h3>
              <p>{vm.minutes.content.overview.text}</p>

              {(['discussions', 'decisions', 'actions'] as const).map(
                (key, index) => (
                  <div key={key}>
                    <h3>{['주요 논의', '결정사항', '담당 업무'][index]}</h3>
                    {!vm.minutes!.content[key].length ? (
                      <p className="muted">확인된 항목이 없습니다.</p>
                    ) : (
                      vm.minutes!.content[key].map((item, i) => (
                        <div className="note-item" key={i}>
                          <p>{item.text}</p>
                          {'assignee_name' in item && (
                            <small>
                              담당: {item.assignee_name || '확인 필요'} · 기한:{' '}
                              {item.due_raw || '미정'}
                            </small>
                          )}
                          <small className="evidence">
                            근거 {item.evidence_ids.join(', ')}
                          </small>
                        </div>
                      ))
                    )}
                  </div>
                )
              )}

              {vm.minutes.content.warnings.map((w, i) => (
                <p className="notice" key={i}>
                  {w}
                </p>
              ))}

              {isManager && (
                <>
                  <div className="actions">
                    <button
                      disabled={vm.busy}
                      onClick={() => {
                        setEditing(!editing);
                      }}
                    >
                      회의록 편집
                    </button>
                    <button disabled={vm.busy} onClick={() => void vm.approve()}>
                      현재 버전 승인
                    </button>
                    <button
                      className="primary"
                      disabled={vm.busy || !vm.minutes.published}
                      onClick={() => void vm.send()}
                    >
                      담당자에게 발송
                    </button>
                  </div>

                  {editing && (
                    <MinutesEditor
                      initial={vm.minutes.content}
                      save={vm.save}
                      busy={vm.busy}
                      cancel={() => setEditing(false)}
                    />
                  )}
                </>
              )}
            </>
          )}
        </section>

        {isManager && (
          <aside>
            <section className="card">
              <h2>발송 수신자</h2>
              <p className="muted">
                전체 회의록을 받을 직원입니다. 변경 후 다시 승인하세요.
              </p>
              {members
                .filter(m => m.active)
                .map(member => {
                  const r = vm.meeting?.recipients.find(
                    r => r.user_id === member.id
                  );
                  return (
                    <div className="recipient" key={member.id}>
                      <strong>{member.name}</strong>
                      <small>{member.email}</small>
                      {(['email', 'kakao'] as const).map(channel => (
                        <RecipientCheckbox
                          key={channel}
                          initialChecked={r?.[channel] || false}
                          disabled={vm.busy}
                          onChange={c => {
                            void vm.toggleRecipient(member.id, channel, c);
                          }}
                          label={channel === 'email' ? '이메일' : '카카오톡'}
                        />
                      ))}
                    </div>
                  );
                })}
            </section>

            <section className="card">
              <h2>원문 근거</h2>
              {vm.segments.map(s => (
                <p className="source" key={s.id}>
                  <small>{s.id}</small>
                  {s.text}
                </p>
              ))}
            </section>
          </aside>
        )}
      </div>
    </>
  );
}


