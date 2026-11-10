import {test,expect} from '@playwright/test';
test('회사 가입부터 회의록 검토와 이메일 발송 접수까지',async({page})=>{
 const email='owner-'+Date.now()+'@example.com';
 const reg=await page.request.post('/api/v1/auth/register',{data:{email,password:'Long-password-123!',name:'김관리'}});
 expect(reg.status()).toBe(201);
 const {test_token}=await reg.json();
 await page.request.post('/api/v1/auth/verify-email',{data:{token:test_token}});
 await page.goto('/');
 await page.getByLabel('이메일',{exact:true}).fill(email);
 await page.getByLabel('비밀번호',{exact:true}).fill('Long-password-123!');
 await page.getByRole('button',{name:'로그인',exact:true}).click();
 await page.getByLabel('회사 이름').fill('회의랩');
 await page.getByRole('button',{name:'회사 만들기'}).click();
 await expect(page.getByRole('heading',{name:'회의 기록',exact:true})).toBeVisible();
 await page.getByLabel('회의 제목',{exact:true}).fill('제품 출시 회의');
 await page.getByLabel('회의 일시',{exact:true}).fill('2026-11-10T10:00');
 await page.getByRole('button',{name:'회의 등록',exact:true}).click();
 await expect(page.getByRole('heading',{name:'제품 출시 회의'})).toBeVisible();
 await page.getByRole('checkbox',{name:'이메일',exact:true}).check();
 await page.getByLabel('녹음·녹취 파일').setInputFiles({name:'회의.txt',mimeType:'text/plain',buffer:Buffer.from('제품 출시를 준비합니다. 품질 검증과 회의록 공유를 진행합니다.','utf8')});
 await expect(page.getByText('테스트 어댑터 결과: 실제 AI 요약 아님')).toBeVisible({timeout:20000});
 await expect(page.locator('.source').first()).toContainText('제품 출시');
 await page.getByRole('button',{name:'현재 버전 승인'}).click();
 await page.getByRole('button',{name:'담당자에게 발송'}).click();
 await page.getByRole('button',{name:'발송 이력',exact:true}).click();
 await expect(page.getByText('접수 완료',{exact:true})).toBeVisible({timeout:15000});
 await page.screenshot({path:'../docs/automation/UI-발송이력.png',fullPage:true});
});
test('모바일 로그인 화면은 넘치지 않고 레이블로 조작된다',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await expect(page.getByLabel('이메일',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.getByRole('button',{name:'비밀번호 찾기'}).click();
 await expect(page.getByLabel('비밀번호',{exact:true})).toHaveCount(0);
 await page.screenshot({path:'../docs/automation/UI-모바일.png',fullPage:true});
});

