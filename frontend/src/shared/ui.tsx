import type { ReactNode } from 'react';
export function ErrorNotice({message}:{message?:string}) {
 return message ? <p className="notice error" role="alert">{message}</p> : null;
}
export function Empty({children}:{children:ReactNode}) {
 return <div className="empty"><span className="empty-mark">○</span><p>{children}</p></div>;
}
export function Loading() { return <p role="status" className="muted">불러오는 중…</p>; }

