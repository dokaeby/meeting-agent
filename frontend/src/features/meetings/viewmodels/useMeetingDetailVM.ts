import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { MeetingsRepository } from '../api/repository';
import type { MeetingDetail, Minutes, Recipient, Summary, TranscriptSegment } from '../model/types';

export interface MeetingDetailViewModel {
  meeting: MeetingDetail | undefined;
  minutes: Minutes | undefined;
  segments: TranscriptSegment[];
  loading: boolean;
  error: string;
  notice: string;
  busy: boolean;
  pdfUrl: string;
  upload: (file: File) => Promise<boolean | undefined>;
  recipients: (items: Recipient[]) => Promise<boolean | undefined>;
  toggleRecipient: (user: string, channel: 'email' | 'kakao', enabled: boolean) => Promise<void>;
  approve: () => Promise<boolean | undefined>;
  send: () => Promise<boolean | undefined>;
  save: (content: Summary) => Promise<boolean | undefined>;
}

export function useMeetingDetailVM(
  repo: MeetingsRepository,
  org: string,
  id: string,
  isManager: boolean
): MeetingDetailViewModel {
  const cache = useQueryClient();
  const detail = useQuery({
    queryKey: ['detail', org, id],
    queryFn: () => repo.detail(org, id),
    refetchInterval: 4000,
  });
  const minutes = useQuery({
    queryKey: ['minutes', org, id],
    queryFn: () => repo.minutes(org, id),
    retry: false,
    refetchInterval: 4000,
  });
  const transcript = useQuery({
    queryKey: ['transcript', org, id, minutes.data?.version],
    queryFn: () => repo.transcript(org, id),
    enabled: isManager,
    retry: false,
  });

  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  async function perform(action: () => Promise<unknown>, message: string) {
    if (busy) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      setNotice(message);
      await cache.invalidateQueries({ queryKey: [] });
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  return {
    meeting: detail.data,
    minutes: minutes.data,
    segments: transcript.data?.segments || [],
    loading: detail.isPending,
    error: error || (detail.error as Error | null)?.message || '',
    notice,
    busy,
    pdfUrl: minutes.data ? repo.pdf(org, id, minutes.data.version) : '',
    upload: (file: File) =>
      perform(() => repo.upload(org, id, file), '처리를 시작했습니다. 잠시 후 결과가 표시됩니다.'),
    recipients: (items: Recipient[]) =>
      perform(() => repo.recipients(org, id, items), '수신자를 저장했습니다. 변경 후에는 다시 승인해 주세요.'),
    toggleRecipient: async (user: string, channel: 'email' | 'kakao', enabled: boolean) => {
      const current = detail.data?.recipients.find(r => r.user_id === user);
      const items = (detail.data?.recipients || []).filter(r => r.user_id !== user);
      items.push({
        user_id: user,
        email: current?.email || false,
        kakao: current?.kakao || false,
        [channel]: enabled,
      });
      const filtered = items.filter(r => r.email || r.kakao);
      cache.setQueryData(['detail', org, id], (old: unknown) =>
        old ? { ...(old as object), recipients: filtered } : old
      );
      try {
        await repo.recipients(org, id, filtered);
        setNotice('수신자를 저장했습니다. 다시 승인해 주세요.');
        await cache.invalidateQueries({ queryKey: ['detail', org, id] });
      } catch (e) {
        setError((e as Error).message);
      }
    },
    approve: () => perform(() => repo.approve(org, id, minutes.data!.version), '이 버전을 승인했습니다.'),
    send: () =>
      perform(() => repo.send(org, id, minutes.data!.version), '발송을 요청했습니다. 발송 이력에서 확인하세요.'),
    save: (content: Summary) =>
      perform(() => repo.edit(org, id, minutes.data!.version, content), '새 버전을 저장했습니다.'),
  };
}

