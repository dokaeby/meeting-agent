import {defineConfig} from '@playwright/test';
import {resolve} from 'node:path';
const python=process.env.MA_TEST_PYTHON||resolve(process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python');
export default defineConfig({
 testDir:'./e2e',fullyParallel:false,workers:1,timeout:45000,
 use:{baseURL:'http://127.0.0.1:5174',trace:'retain-on-failure',channel:process.env.PLAYWRIGHT_CHANNEL||'msedge'},
 reporter:[['list'],['html',{open:'never'}]],
 webServer:[
 {command:'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174 --strictPort',url:'http://127.0.0.1:5174',reuseExistingServer:false},
 {command:'"'+python+'" "../docs/automation/serve_test.py"',url:'http://127.0.0.1:8000/api/v1/health/live',reuseExistingServer:false},
 ],
});

