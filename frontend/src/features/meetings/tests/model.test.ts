import { describe, expect, it } from 'vitest';
import { statusLabel, canAutoSend } from '../model/types';
describe('회의 정책', () => {
 it('상태를 한국어로 표시한다', () => { expect(statusLabel('review_required')).toBe('검토 대기'); });
 it('불확실한 요약은 자동 발송하지 않는다', () => {
  expect(canAutoSend({ warnings: ['담당자 확인 필요'], actions: [] })).toBe(false);
  expect(canAutoSend({ warnings: [], actions: [{ assignee_id: null }] })).toBe(false);
 });
});

