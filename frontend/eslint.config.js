import js from '@eslint/js';
import ts from 'typescript-eslint';
import hooks from 'eslint-plugin-react-hooks';
export default ts.config(js.configs.recommended, ...ts.configs.recommended,
 {files:['src/**/*.{ts,tsx}'],plugins:{'react-hooks':hooks},rules:{
 ...hooks.configs.recommended.rules,'@typescript-eslint/no-explicit-any':'error',
 'react-hooks/set-state-in-effect':'off','react-hooks/refs':'off'}},
 {files:['src/**/views/**/*.{ts,tsx}'],rules:{'no-restricted-imports':['error',{
 patterns:[{group:['**/api/**','**/shared/http*','**/repository*'],message:'View는 ViewModel만 호출합니다.'}]}]}},
 {files:['src/**/model/**/*.ts'],rules:{'no-restricted-imports':['error',{
 patterns:[{group:['react','react-dom','**/api/**','**/viewmodels/**'],message:'Model은 React/HTTP에 의존하지 않습니다.'}]}]}}
);

