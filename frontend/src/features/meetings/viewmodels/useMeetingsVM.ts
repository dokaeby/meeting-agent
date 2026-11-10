import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { MeetingListRepository } from '../api/repository';
import type { Meeting } from '../model/types';

export interface MeetingsViewModel {
  items: Meeting[];
  total: number;
  page: number;
  setPage: (page: number) => void;
  loading: boolean;
  error: string;
  reload: () => Promise<unknown>;
  title: string;
  setTitle: (title: string) => void;
  start: string;
  setStart: (start: string) => void;
  busy: boolean;
  create: () => Promise<string | undefined>;
}

export function useMeetingsVM(
  repo: MeetingListRepository,
  org: string
): MeetingsViewModel {
  const cache = useQueryClient();
  const [page, setPage] = useState(0);
  const query = useQuery({
    queryKey: ['meetings', org, page],
    queryFn: () => repo.list(org, page * 30),
    refetchInterval: 5000,
    retry: false,
  });

  const [title, setTitle] = useState('');
  const [start, setStart] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function create(): Promise<string | undefined> {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const data = await repo.create(org, {
        title,
        start_at: new Date(start).toISOString(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      setTitle('');
      await cache.invalidateQueries({ queryKey: ['meetings', org] });
      return data.id;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return {
    items: query.data?.items || [],
    total: query.data?.total || 0,
    page,
    setPage,
    loading: query.isPending,
    error: error || (query.error as Error | null)?.message || '',
    reload: query.refetch,
    title,
    setTitle,
    start,
    setStart,
    busy,
    create,
  };
}

