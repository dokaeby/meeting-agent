import {json,request} from '../../../shared/http';
import type {Meeting,MeetingDetail,Minutes,Recipient,Summary} from '../model/types';
const path=(org:string,id?:string)=>'/organizations/'+org+'/meetings'+(id?'/'+id:'');
export const meetingsRepository={
 list:(org:string,offset=0)=>request<{items:Meeting[];total:number}>(path(org)+'?offset='+offset+'&limit=30'),
 create:(org:string,data:{title:string;start_at:string;timezone:string})=>request<Meeting>(path(org),json('POST',data)),
 detail:(org:string,id:string)=>request<MeetingDetail>(path(org,id)),
 minutes:(org:string,id:string)=>request<Minutes>(path(org,id)+'/minutes'),
 transcript:(org:string,id:string)=>request<{segments:{id:string;text:string}[]}>(path(org,id)+'/transcript'),
 recipients:(org:string,id:string,recipients:Recipient[])=>request(path(org,id)+'/recipients',json('PUT',recipients)),
 upload:(org:string,id:string,file:File)=>{const body=new FormData();body.set('file',file);return request(path(org,id)+'/source',{method:'POST',body});},
 approve:(org:string,id:string,version:number)=>request(path(org,id)+'/approve',json('POST',{version})),
 send:(org:string,id:string,version:number)=>request(path(org,id)+'/send',json('POST',{version})),
 edit:(org:string,id:string,version:number,content:Summary)=>request<Minutes>(path(org,id)+'/minutes',json('PUT',{expected_version:version,content})),
 pdf:(org:string,id:string,version:number)=>'/api/v1'+path(org,id)+'/minutes/'+version+'/pdf',
 remove:(org:string,id:string)=>request(path(org,id),json('DELETE',{})),
};
export type MeetingsRepository=typeof meetingsRepository;
export type MeetingListRepository=Pick<MeetingsRepository,'list'|'create'>;

