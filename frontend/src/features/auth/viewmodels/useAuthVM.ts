import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import type { AuthRepository } from '../api/repository';
import type { Company, User } from '../model/types';

export type AuthMode = 'login' | 'register' | 'reset';

export interface AuthViewModel {
  user: User | undefined;
  companies: Company[];
  loading: boolean;
  mode: AuthMode;
  setMode: (mode: AuthMode) => void;
  hasReset: boolean;
  email: string;
  setEmail: (email: string) => void;
  password: string;
  setPassword: (password: string) => void;
  name: string;
  setName: (name: string) => void;
  error: string;
  message: string;
  busy: boolean;
  submit: () => Promise<void>;
  logout: () => Promise<void>;
  createCompany: (companyName: string) => Promise<void>;
}

export function useAuthVM(repo: AuthRepository): AuthViewModel {
  const cache = useQueryClient();
  const session = useQuery({
    queryKey: ['session'],
    queryFn: () => repo.session(),
    retry: false,
  });

  const hasReset = !!new URLSearchParams(location.search).get('reset');
  const [mode, setMode] = useState<AuthMode>(hasReset ? 'reset' : 'login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const once = useRef(false);
  const acceptedInvite = useRef('');
  const refetchSession = session.refetch;

  useEffect(() => {
    const invite = new URLSearchParams(location.search).get('invite');
    if (invite && session.data?.user && acceptedInvite.current !== invite) {
      acceptedInvite.current = invite;
      void repo
        .accept(invite)
        .then(async () => {
          setMessage('회사 초대를 수락했습니다.');
          const url = new URL(location.href);
          url.searchParams.delete('invite');
          history.replaceState({}, '', url);
          await refetchSession();
        })
        .catch(e => setError((e as Error).message));
    }
  }, [repo, session.data?.user, refetchSession]);

  useEffect(() => {
    const token = new URLSearchParams(location.search).get('verify');
    if (token && !once.current) {
      once.current = true;
      void repo
        .verify(token)
        .then(() => setMessage('이메일 확인 완료. 로그인해 주세요.'))
        .catch(e => setError(String(e.message)));
    }
  }, [repo]);

  async function submit() {
    if (busy) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const resetToken = new URLSearchParams(location.search).get('reset');
      if (mode === 'register') {
        await repo.register(email, password, name);
        setMessage('확인 메일을 보냈습니다. 메일의 링크를 열어 주세요.');
        setMode('login');
      } else if (mode === 'reset') {
        if (resetToken) {
          await repo.confirmReset(resetToken, password);
          setMessage('비밀번호를 변경했습니다.');
          setMode('login');
        } else {
          await repo.reset(email);
          setMessage('가입한 이메일이면 재설정 안내가 발송됩니다.');
        }
      } else {
        const s = await repo.login(email, password);
        cache.setQueryData(['session'], s);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await repo.logout();
    cache.clear();
    location.assign('/');
  }

  async function createCompany(companyName: string) {
    await repo.createCompany(companyName);
    await session.refetch();
  }

  return {
    user: session.data?.user,
    companies: session.data?.organizations || [],
    loading: session.isPending,
    mode,
    setMode,
    hasReset,
    email,
    setEmail,
    password,
    setPassword,
    name,
    setName,
    error,
    message,
    busy,
    submit,
    logout,
    createCompany,
  };
}

