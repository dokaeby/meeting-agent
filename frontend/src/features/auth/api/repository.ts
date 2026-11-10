import {json,request,setCsrf} from '../../../shared/http';
import type {AuthSession,Company} from '../model/types';
export const authRepository = {
 async session(){const s=await request<AuthSession>('/auth/session');setCsrf(s.csrf_token);return s;},
 async login(email:string,password:string){const s=await request<AuthSession>('/auth/login',json('POST',{email,password}));setCsrf(s.csrf_token);return s;},
 register:(email:string,password:string,name:string)=>request<{test_token?:string}>('/auth/register',json('POST',{email,password,name})),
 verify:(token:string)=>request('/auth/verify-email',json('POST',{token})),
 reset:(email:string)=>request('/auth/password-reset',json('POST',{email})),
 confirmReset:(token:string,password:string)=>request('/auth/password-reset/confirm',json('POST',{token,password})),
 accept:(token:string)=>request('/invitations/accept',json('POST',{token})),
 logout:()=>request('/auth/logout',json('POST',{})),
 createCompany:(name:string)=>request<Company>('/organizations',json('POST',{name})),
};
export type AuthRepository = typeof authRepository;

