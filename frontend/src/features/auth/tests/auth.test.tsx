import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {renderHook,waitFor,render,screen} from '@testing-library/react';
import type {ReactNode} from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {useAuthVM} from '../viewmodels/useAuthVM';
import {AuthView} from '../views/AuthView';
import type {AuthRepository} from '../api/repository';
const session={user:{id:'u',email:'u@example.com',name:'테스트',verified:true},csrf_token:'c',organizations:[]};
function wrap({children}:{children:ReactNode}){const cache=new QueryClient({defaultOptions:{queries:{retry:false}}});return <QueryClientProvider client={cache}>{children}</QueryClientProvider>;}
afterEach(()=>history.replaceState({},'','/'));
it('기존 세션에서도 초대 링크를 수락한다',async()=>{
 history.replaceState({},'','/?invite=token');
 const repo={session:vi.fn().mockResolvedValue(session),accept:vi.fn().mockResolvedValue({})} as unknown as AuthRepository;
 renderHook(()=>useAuthVM(repo),{wrapper:wrap});
 await waitFor(()=>expect(repo.accept).toHaveBeenCalledWith('token'));
});
it('재설정 요청에는 비밀번호를 요구하지 않는다',async()=>{
 const repo={session:vi.fn().mockRejectedValue(new Error('login'))} as unknown as AuthRepository;
 function Page(){const vm=useAuthVM(repo);return <AuthView vm={vm}/>;}
 render(<QueryClientProvider client={new QueryClient()}><Page/></QueryClientProvider>);
 screen.getByRole('button',{name:'비밀번호 찾기'}).click();
 await waitFor(()=>expect(screen.queryByLabelText('비밀번호')).not.toBeInTheDocument());
});
it('재설정 링크는 바로 새 비밀번호 입력으로 연다',()=>{
 history.replaceState({},'','/?reset=token');
 const repo={session:vi.fn().mockRejectedValue(new Error('login'))} as unknown as AuthRepository;
 const {result}=renderHook(()=>useAuthVM(repo),{wrapper:wrap});
 expect(result.current.mode).toBe('reset');
});
