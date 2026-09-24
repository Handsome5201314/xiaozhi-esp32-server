import { describe, expect, it } from 'vitest';
import { resolveDeleteAgentTarget } from '../src/utils/agentDeletion.mjs';

describe('resolveDeleteAgentTarget', () => {
  it('uses the agent name when it is present', () => {
    expect(resolveDeleteAgentTarget({ id: 'agent-1', agentName: '助手' })).toEqual({
      id: 'agent-1',
      confirmationValue: '助手',
      usesId: false,
    });
  });

  it('falls back to the ID for legacy agents without a name', () => {
    expect(resolveDeleteAgentTarget({ id: 'agent-2', agentName: '  ' })).toEqual({
      id: 'agent-2',
      confirmationValue: 'agent-2',
      usesId: true,
    });
  });

  it('rejects entries without a stable ID', () => {
    expect(resolveDeleteAgentTarget({ agentName: '助手' })).toBeNull();
    expect(resolveDeleteAgentTarget(null)).toBeNull();
  });
});
