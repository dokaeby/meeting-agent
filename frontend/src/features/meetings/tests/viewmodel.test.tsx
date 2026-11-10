import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { expect, it, vi } from 'vitest';
import { useMeetingsVM } from '../viewmodels/useMeetingsVM';

function wrapper({ children }: { children: ReactNode }) {
 const client = new QueryClient({defaultOptions:{queries:{retry:false}}});
 return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
it('불러오기 실패를 노출하고 재시도한다', async () => {
 const repo = { list: vi.fn().mockRejectedValueOnce(new Error('연결 실패')).mockResolvedValue({items:[],total:0}),
 create: vi.fn() };
 const { result } = renderHook(() => useMeetingsVM(repo, 'A'), {wrapper});
 await waitFor(() => expect(result.current.error).toBe('연결 실패'));
 await act(async () => { await result.current.reload(); });
 expect(result.current.items).toEqual([]);
});
it('회사 전환 후 이전 회사의 늦은 응답을 표시하지 않는다', async () => {
 let resolveA: (value: {items: {id:string,title:string,status:string,start_at:string,timezone:string}[], total:number}) => void;
 const pending = new Promise<{items: {id:string,title:string,status:string,start_at:string,timezone:string}[],total:number}>(resolve => { resolveA = resolve; });
 const repo = { list: vi.fn((org:string) => org === 'A' ? pending : Promise.resolve({items:[],total:0})),create:vi.fn() };
 const {result,rerender}=renderHook(({org})=>useMeetingsVM(repo,org),{initialProps:{org:'A'},wrapper});
 rerender({org:'B'});
 await waitFor(()=>expect(result.current.loading).toBe(false));
 await act(async()=>{resolveA!({items:[{id:'old',title:'A 비밀회의',status:'ready',start_at:'',timezone:'Asia/Seoul'}],total:1});});
 expect(result.current.items).toEqual([]);
});
