import { useState } from 'react';
import type { Summary } from '../model/types';

interface MinutesEditorProps {
  initial: Summary;
  save: (content: Summary) => Promise<boolean | undefined>;
  cancel: () => void;
  busy: boolean;
}

export function MinutesEditor({
  initial,
  save,
  cancel,
  busy,
}: MinutesEditorProps) {
  const [draft, setDraft] = useState<Summary>(() => structuredClone(initial));

  return (
    <form
      onSubmit={e => {
        e.preventDefault();
        void save(draft).then(ok => {
          if (ok) cancel();
        });
      }}
    >
      <label>
        회의록 제목
        <input
          value={draft.title}
          onChange={e => setDraft({ ...draft, title: e.target.value })}
          required
        />
      </label>

      <label>
        요약 내용
        <textarea
          rows={5}
          value={draft.overview.text}
          onChange={e =>
            setDraft({
              ...draft,
              overview: { ...draft.overview, text: e.target.value },
            })
          }
          required
        />
      </label>

      {(['discussions', 'decisions', 'actions'] as const).map((key, index) => (
        <section key={key}>
          <h3>
            {['논의 수정', '결정사항 수정', '담당 업무 수정'][index]}
          </h3>
          {draft[key].map((item, i) => (
            <div key={i}>
              <label>
                항목 {i + 1}
                <textarea
                  value={item.text}
                  onChange={e =>
                    setDraft({
                      ...draft,
                      [key]: draft[key].map((row, j) =>
                        j === i ? { ...row, text: e.target.value } : row
                      ),
                    })
                  }
                  required
                />
              </label>
              {'assignee_name' in item && (
                <>
                  <label>
                    담당자 이름
                    <input
                      value={item.assignee_name || ''}
                      onChange={e =>
                        setDraft({
                          ...draft,
                          actions: draft.actions.map((row, j) =>
                            j === i
                              ? {
                                  ...row,
                                  assignee_name: e.target.value,
                                  assignee_id: null,
                                }
                              : row
                          ),
                        })
                      }
                    />
                  </label>
                  <label>
                    기한 원문
                    <input
                      value={item.due_raw || ''}
                      onChange={e =>
                        setDraft({
                          ...draft,
                          actions: draft.actions.map((row, j) =>
                            j === i
                              ? { ...row, due_raw: e.target.value, due_at: null }
                              : row
                          ),
                        })
                      }
                    />
                  </label>
                </>
              )}
            </div>
          ))}
        </section>
      ))}

      <p className="muted">
        원문 근거 연결은 유지됩니다. 변경한 내용과 담당자를 검토한 뒤 다시 승인하세요.
      </p>

      <div className="actions">
        <button className="primary" disabled={busy}>
          새 버전 저장
        </button>
        <button type="button" onClick={cancel}>
          취소
        </button>
      </div>
    </form>
  );
}

