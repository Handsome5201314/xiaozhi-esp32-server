function normalize(value) {
  if (value === null || value === undefined) return '';
  return String(value).trim();
}

/**
 * Resolve the stable identity and confirmation value used before deletion.
 * Older records may have an empty agent name, so the ID remains a safe fallback.
 */
export function resolveDeleteAgentTarget(agent) {
  if (!agent || typeof agent !== 'object') return null;

  const id = normalize(agent.agentId || agent.id);
  if (!id) return null;

  const name = normalize(agent.agentName || agent.name);
  return {
    id,
    confirmationValue: name || id,
    usesId: !name,
  };
}
