export interface User {id:string;email:string;name:string;verified:boolean}
export interface Company {id:string;name:string;role:string}
export interface AuthSession {user:User;csrf_token:string;organizations:Company[]}

