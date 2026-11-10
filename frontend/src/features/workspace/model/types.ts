export interface Member {id:string;name:string;email:string;role:string;active:boolean;aliases:string[]}
export interface Integration {id:string;provider:string;user_id:string;status:string;external_user:string}
export interface Delivery {id:string;meeting_id:string;version:number;user_id:string;channel:string;status:string;attempts:number;error:string}
export interface Policy {auto_send:boolean;retention_days:number;audio_retention_days:number;audit_retention_days:number;monthly_meetings:number;ai_consent:boolean;policy_version?:number}
export interface Usage {items:{period:string;meetings:number;tokens:number;stt_seconds:number;bytes:number}[];monthly_meetings:number}

