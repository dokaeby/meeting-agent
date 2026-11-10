import {json,request} from '../../../shared/http';
import type {Delivery,Integration,Member,Policy,Usage} from '../model/types';
const base=(org:string)=>'/organizations/'+org;
export const workspaceRepository={
 members:(org:string)=>request<{items:Member[]}>(base(org)+'/members'),
 invite:(org:string,email:string,role:string)=>request(base(org)+'/invitations',json('POST',{email,role})),
 updateMember:(org:string,user:string,data:{role:string;active:boolean;aliases:string[]})=>request(base(org)+'/members/'+user,json('PATCH',data)),
 settings:(org:string)=>request<Policy>(base(org)+'/settings'),
 saveSettings:(org:string,data:Policy)=>request<Policy>(base(org)+'/settings',json('PATCH',{
 auto_send:data.auto_send,retention_days:data.retention_days,audio_retention_days:data.audio_retention_days,
 audit_retention_days:data.audit_retention_days,monthly_meetings:data.monthly_meetings,ai_consent:data.ai_consent})),
 integrations:(org:string)=>request<{items:Integration[]}>(base(org)+'/integrations'),
 connect:(org:string,provider:string)=>request<{authorize_url:string}>(base(org)+'/integrations/'+provider+'/authorize',json('POST',{})),
 disconnect:(org:string,id:string)=>request(base(org)+'/integrations/'+id,json('DELETE',{})),
 deliveries:(org:string)=>request<{items:Delivery[]}>(base(org)+'/deliveries'),
 retry:(org:string,id:string,acknowledge_duplicate_risk:boolean)=>request(base(org)+'/deliveries/'+id+'/retry',json('POST',{acknowledge_duplicate_risk})),
 usage:(org:string)=>request<Usage>(base(org)+'/usage'),
};
export type WorkspaceRepository=typeof workspaceRepository;

