import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { WorkspaceRepository } from '../api/repository';
import type { Delivery, Integration, Member, Policy, Usage } from '../model/types';

export interface WorkspaceViewModel {
  members: Member[];
  policy: Policy | undefined;
  integrations: Integration[];
  deliveries: Delivery[];
  usage: Usage | undefined;
  error: string;
  notice: string;
  busy: boolean;
  invite: (email: string, role: string) => Promise<boolean | undefined>;
  updateMember: (member: Member) => Promise<boolean | undefined>;
  saveSettings: (policy: Policy) => Promise<boolean | undefined>;
  connect: (provider: string) => Promise<boolean | undefined>;
  disconnect: (id: string) => Promise<boolean | undefined>;
  retry: (id: string, ack: boolean) => Promise<boolean | undefined>;
}

export function useWorkspaceVM(
  repo: WorkspaceRepository,
  org: string,
  role: string
): WorkspaceViewModel {
  const cache = useQueryClient();
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const members = useQuery({
    queryKey: ['members', org],
    queryFn: () => repo.members(org),
  });
  const settings = useQuery({
    queryKey: ['settings', org],
    queryFn: () => repo.settings(org),
  });
  const integrations = useQuery({
    queryKey: ['integrations', org],
    queryFn: () => repo.integrations(org),
  });
  const deliveries = useQuery({
    queryKey: ['deliveries', org],
    queryFn: () => repo.deliveries(org),
    enabled: role !== 'member',
    refetchInterval: 5000,
  });
  const usage = useQuery({
    queryKey: ['usage', org],
    queryFn: () => repo.usage(org),
    enabled: role === 'admin',
  });

  async function perform(action: () => Promise<unknown>, message: string) {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      await action();
      setNotice(message);
      await cache.invalidateQueries();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  return {
    members: members.data?.items || [],
    policy: settings.data,
    integrations: integrations.data?.items || [],
    deliveries: deliveries.data?.items || [],
    usage: usage.data,
    error:
      error ||
      [members, settings, integrations, deliveries, usage].find(q => q.error)
        ?.error?.message ||
      '',
    notice,
    busy,
    invite: (email: string, role: string) =>
      perform(() => repo.invite(org, email, role), '초대 메일을 요청했습니다.'),
    updateMember: (member: Member) =>
      perform(
        () =>
          repo.updateMember(org, member.id, {
            role: member.role,
            active: member.active,
            aliases: member.aliases,
          }),
        '직원 정보를 변경했습니다.'
      ),
    saveSettings: (policy: Policy) =>
      perform(() => {
        const { policy_version: _, ...data } = policy;
        void _;
        return repo.saveSettings(org, data);
      }, '설정을 저장했습니다.'),
    connect: (provider: string) =>
      perform(async () => {
        const result = await repo.connect(org, provider);
        location.assign(result.authorize_url);
      }, ''),
    disconnect: (id: string) =>
      perform(() => repo.disconnect(org, id), '연동을 해제했습니다.'),
    retry: (id: string, ack: boolean) =>
      perform(() => repo.retry(org, id, ack), '재시도를 요청했습니다.'),
  };
}

