let csrf = '';
export function setCsrf(value: string) { csrf = value; }
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
 const headers = new Headers(options.headers);
 if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
 if (csrf) headers.set('X-CSRF-Token', csrf);
 const response = await fetch('/api/v1' + path, {...options, headers, credentials:'same-origin'});
 if (!response.ok) {
  const error = await response.json().catch(()=>({message:'요청을 완료하지 못했습니다'}));
  throw new Error(error.message || '요청을 완료하지 못했습니다');
 }
 return response.json() as Promise<T>;
}
export const json = (method: string, body: unknown): RequestInit => ({method,body:JSON.stringify(body)});

