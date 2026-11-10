import { useState } from 'react';
import type { WorkspaceViewModel } from '../viewmodels/useWorkspaceVM';

interface MembersTabProps {
  vm: WorkspaceViewModel;
  role: string;
}

export function MembersTab({ vm, role }: MembersTabProps) {
  const [email, setEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');

  return (
    <>
      <section className="card">
        <h2>직원 초대</h2>
        {role === 'admin' ? (
          <form
            className="inline-form"
            onSubmit={e => {
              e.preventDefault();
              void vm.invite(email, inviteRole).then(ok => {
                if (ok) setEmail('');
              });
            }}
          >
            <label>
              초대 이메일
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              역할
              <select
                value={inviteRole}
                onChange={e => setInviteRole(e.target.value)}
              >
                <option value="member">일반 직원</option>
                <option value="manager">회의 관리자</option>
                <option value="admin">회사 관리자</option>
              </select>
            </label>
            <button className="primary" disabled={vm.busy}>
              초대하기
            </button>
          </form>
        ) : (
          <p>회사 관리자에게 초대를 요청해 주세요.</p>
        )}
      </section>

      <section className="card">
        <h2>회사 직원</h2>
        {vm.members.map(m => (
          <div className="member-row" key={m.id}>
            <div>
              <strong>{m.name}</strong>
              <small>
                {m.email} · {m.active ? '활성' : '비활성'}
              </small>
            </div>
            <span className="badge">{m.role}</span>
            {role === 'admin' && (
              <>
                <select
                  aria-label={m.name + ' 역할'}
                  value={m.role}
                  onChange={e =>
                    void vm.updateMember({ ...m, role: e.target.value })
                  }
                >
                  <option value="member">일반 직원</option>
                  <option value="manager">회의 관리자</option>
                  <option value="admin">회사 관리자</option>
                </select>
                <button
                  disabled={vm.busy}
                  onClick={() =>
                    void vm.updateMember({ ...m, active: !m.active })
                  }
                >
                  {m.active ? '비활성화' : '활성화'}
                </button>
                <label>
                  확인된 별칭
                  <input
                    defaultValue={m.aliases.join(',')}
                    placeholder="별칭을 쉼표로 구분"
                    onBlur={e => {
                      const aliases = e.target.value
                        .split(',')
                        .map(s => s.trim())
                        .filter(Boolean);
                      if (aliases.join(',') !== m.aliases.join(',')) {
                        void vm.updateMember({ ...m, aliases });
                      }
                    }}
                  />
                </label>
              </>
            )}
          </div>
        ))}
      </section>
    </>
  );
}

