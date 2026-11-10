export interface Meeting {id:string;title:string;status:string;start_at:string;timezone:string}
export interface Evidence {text:string;evidence_ids:string[]}
export interface TranscriptSegment {id:string;text:string}
export interface Action extends Evidence {assignee_id:string|null;assignee_name:string|null;due_raw:string|null;due_at:string|null}
export interface Summary {title:string;overview:Evidence;discussions:Evidence[];decisions:Evidence[];actions:Action[];warnings:string[]}
export interface Minutes {version:number;content:Summary;published:boolean}
export interface Recipient {user_id:string;email:boolean;kakao:boolean}
export interface MeetingDetail extends Meeting {recipients:Recipient[]}
export const statusLabel = (status:string):string => ({
 waiting_source:'입력 대기',transcribing:'녹취 처리',summarizing:'요약 중',rendering:'문서 생성',
 review_required:'검토 대기',ready:'발송 준비',completed:'완료',failed:'처리 실패',
 pending:'대기',sending:'발송 중',accepted:'접수 완료',unknown:'결과 확인 필요',
 cancelled:'취소',skipped:'채널 미연결',retry_wait:'재시도 대기',
}[status]||status);
export function canAutoSend(content:{warnings:string[];actions:{assignee_id:string|null}[]}){
 return content.warnings.length===0&&content.actions.every(a=>!!a.assignee_id);
}

