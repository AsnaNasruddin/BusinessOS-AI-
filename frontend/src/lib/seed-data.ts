/**
 * Placeholder data source standing in for the FastAPI backend (implementation
 * plan phases 1-3 aren't built yet). Every hook in `src/hooks` reads from here.
 * Swapping a hook over to `api` later is a one-file change — see the comment
 * at the top of each hook.
 */
import type {
  Agent,
  ApprovalRequest,
  KbDocument,
  KnowledgeBase,
  RetrievedChunk,
  Tool,
  Workflow,
  WorkflowRun,
  WorkflowStep,
} from '@/types'

export const currentOrg = { id: 'org_1', name: 'Acme Robotics', slug: 'acme-robotics' }
export const currentUser = { id: 'user_1', fullName: 'Jordan Avery', initials: 'JA', role: 'owner' as const }

export const tools: Tool[] = [
  { id: 'search_kb', name: 'search_kb', displayName: 'search_kb', description: 'Vector search over a knowledge base.', category: 'retrieval' },
  { id: 'send_email', name: 'send_email', displayName: 'send_email', description: 'Sends an approved reply. Stubbed in dev.', category: 'communication' },
  { id: 'log_activity', name: 'log_activity', displayName: 'log_activity', description: 'Writes an interaction record to the CRM.', category: 'data' },
  { id: 'http_request', name: 'http_request', displayName: 'http_request', description: 'Generic outbound HTTP call.', category: 'data' },
]

export const agents: Agent[] = [
  {
    id: 'agent_triage',
    orgId: currentOrg.id,
    name: 'Triage Classifier',
    description: 'Classifies incoming support email.',
    systemPrompt:
      'Classify the incoming email into billing_refund, technical_issue, or general_inquiry. Decide if knowledge-base lookup is needed. Return JSON: {category, urgency, needs_kb}.',
    modelProvider: 'ollama',
    modelName: 'llama3.1:8b',
    temperature: 0.2,
    allowedTools: [],
    memoryScope: 'none',
  },
  {
    id: 'agent_draft',
    orgId: currentOrg.id,
    name: 'Draft Reply Writer',
    description: 'Writes the customer-facing reply.',
    systemPrompt:
      'You are a support specialist for Acme Robotics. Use retrieved knowledge-base context, if any, to write a warm, precise reply. Never promise refunds outside policy. Return JSON: {subject, body, confidence}.',
    modelProvider: 'ollama',
    modelName: 'llama3.1:8b',
    temperature: 0.4,
    allowedTools: ['search_kb', 'send_email'],
    memoryScope: 'session',
  },
  {
    id: 'agent_memory',
    orgId: currentOrg.id,
    name: 'Memory Extractor',
    description: 'Extracts durable facts after each agent turn.',
    systemPrompt:
      'After each agent turn, decide if anything durable happened worth remembering about this customer or deal. Return JSON: {should_remember, fact, importance}.',
    modelProvider: 'ollama',
    modelName: 'qwen2.5:7b',
    temperature: 0.1,
    allowedTools: [],
    memoryScope: 'persistent',
  },
  {
    id: 'agent_lead',
    orgId: currentOrg.id,
    name: 'Lead Enrichment Agent',
    description: 'Enriches inbound leads with firmographic data.',
    systemPrompt:
      'Given a new lead company domain, research and summarize firmographic details relevant to sales qualification. Return JSON: {company_size, industry, fit_score}.',
    modelProvider: 'anthropic',
    modelName: 'claude-haiku',
    temperature: 0.3,
    allowedTools: ['http_request'],
    memoryScope: 'none',
  },
]

export const knowledgeBases: KnowledgeBase[] = [
  { id: 'kb_support', orgId: currentOrg.id, name: 'Support Macros', description: 'Canned replies and escalation scripts.', documentCount: 18 },
  { id: 'kb_product', orgId: currentOrg.id, name: 'Product Docs', description: 'Manuals and FAQs.', documentCount: 42 },
  { id: 'kb_policy', orgId: currentOrg.id, name: 'Policy & Refunds', description: 'Returns, warranty, and chargeback policy.', documentCount: 7 },
]

export const kbDocuments: Record<string, KbDocument[]> = {
  kb_policy: [
    { id: 'd1', kbId: 'kb_policy', filename: 'Returns-Policy.pdf', mimeType: 'PDF', sizeLabel: '412 KB', status: 'ready', chunkCount: 12 },
    { id: 'd2', kbId: 'kb_policy', filename: 'Warranty-Terms.docx', mimeType: 'DOCX', sizeLabel: '88 KB', status: 'ready', chunkCount: 6 },
    { id: 'd3', kbId: 'kb_policy', filename: 'Refund-Exceptions.pdf', mimeType: 'PDF', sizeLabel: '156 KB', status: 'ready', chunkCount: 5 },
    { id: 'd4', kbId: 'kb_policy', filename: 'Shipping-Damage-Claims.pdf', mimeType: 'PDF', sizeLabel: '203 KB', status: 'processing', chunkCount: null },
    { id: 'd5', kbId: 'kb_policy', filename: 'Chargeback-Guidelines.pdf', mimeType: 'PDF', sizeLabel: '97 KB', status: 'ready', chunkCount: 4 },
    { id: 'd6', kbId: 'kb_policy', filename: 'International-Returns.pdf', mimeType: 'PDF', sizeLabel: '301 KB', status: 'failed', chunkCount: null },
    { id: 'd7', kbId: 'kb_policy', filename: 'Extended-Warranty-Addendum.pdf', mimeType: 'PDF', sizeLabel: '64 KB', status: 'ready', chunkCount: 3 },
  ],
  kb_support: [
    { id: 'd8', kbId: 'kb_support', filename: 'Greeting-Macros.docx', mimeType: 'DOCX', sizeLabel: '40 KB', status: 'ready', chunkCount: 8 },
    { id: 'd9', kbId: 'kb_support', filename: 'Escalation-Scripts.pdf', mimeType: 'PDF', sizeLabel: '120 KB', status: 'ready', chunkCount: 14 },
  ],
  kb_product: [
    { id: 'd10', kbId: 'kb_product', filename: 'Model-X200-Manual.pdf', mimeType: 'PDF', sizeLabel: '2.1 MB', status: 'ready', chunkCount: 88 },
    { id: 'd11', kbId: 'kb_product', filename: 'Model-X200-FAQ.html', mimeType: 'HTML', sizeLabel: '22 KB', status: 'ready', chunkCount: 9 },
  ],
}

export const sampleRetrieval: RetrievedChunk[] = [
  { source: 'Returns-Policy.pdf', chunkIndex: 4, score: 0.891, text: 'Items arriving damaged are eligible for a full refund or free replacement within 30 days of delivery, no return shipping required for verified damage claims.' },
  { source: 'Shipping-Damage-Claims.pdf', chunkIndex: 1, score: 0.845, text: 'To file a damage claim, attach photos of the packaging and unit. Claims must be submitted within the 30-day window from delivery date.' },
  { source: 'Refund-Exceptions.pdf', chunkIndex: 2, score: 0.762, text: 'Exceptions to the standard refund window apply to custom-configured units and clearance items, which are final sale.' },
]

export const workflows: Workflow[] = [
  { id: 'wf_support', orgId: currentOrg.id, name: 'Customer Support Triage', description: 'Classify, retrieve, draft, and reply to support email.', triggerType: 'webhook', isActive: true, version: 3, updatedAtLabel: '2 hours ago' },
  { id: 'wf_invoice', orgId: currentOrg.id, name: 'Invoice Approval', description: 'Route high-value invoices for human sign-off.', triggerType: 'manual', isActive: true, version: 2, updatedAtLabel: '1 day ago' },
  { id: 'wf_report', orgId: currentOrg.id, name: 'Weekly Report Digest', description: 'Summarize the week and email leadership.', triggerType: 'schedule', isActive: true, version: 1, updatedAtLabel: '5 days ago' },
  { id: 'wf_lead', orgId: currentOrg.id, name: 'Lead Enrichment', description: 'Enrich and score new inbound leads.', triggerType: 'schedule', isActive: true, version: 4, updatedAtLabel: '3 days ago' },
  { id: 'wf_contract', orgId: currentOrg.id, name: 'Contract Review', description: 'Draft clause redlines for legal review.', triggerType: 'manual', isActive: false, version: 1, updatedAtLabel: '2 weeks ago' },
  { id: 'wf_churn', orgId: currentOrg.id, name: 'Churn Risk Alert', description: 'Flag accounts showing churn signals.', triggerType: 'schedule', isActive: false, version: 1, updatedAtLabel: '3 weeks ago' },
]

export const dashboardStats = {
  activeWorkflows: 4,
  totalWorkflows: 6,
  runs24h: 37,
  successRate7d: 94.6,
  tokens30d: '1.84M',
  estCost30d: 1.12,
  costNote: '2 runs on Claude Haiku · rest on Ollama',
}

export const recentRuns: WorkflowRun[] = [
  { id: 'run_4128', workflowId: 'wf_support', workflowName: 'Customer Support Triage', status: 'succeeded', triggerLabel: 'webhook', durationLabel: '8.2s', totalTokens: 2140, totalCostUsd: 0, startedAtLabel: '2 min ago' },
  { id: 'run_4127', workflowId: 'wf_invoice', workflowName: 'Invoice Approval', status: 'awaiting_approval', triggerLabel: 'manual', durationLabel: '1.1s', totalTokens: 310, totalCostUsd: 0, startedAtLabel: '14 min ago' },
  { id: 'run_4126', workflowId: 'wf_lead', workflowName: 'Lead Enrichment', status: 'succeeded', triggerLabel: 'schedule', durationLabel: '4.6s', totalTokens: 1780, totalCostUsd: 0.02, startedAtLabel: '41 min ago' },
  { id: 'run_4125', workflowId: 'wf_report', workflowName: 'Weekly Report Digest', status: 'succeeded', triggerLabel: 'schedule', durationLabel: '12.4s', totalTokens: 3920, totalCostUsd: 0, startedAtLabel: '3 hr ago' },
  { id: 'run_4124', workflowId: 'wf_support', workflowName: 'Customer Support Triage', status: 'failed', triggerLabel: 'webhook', durationLabel: '2.0s', totalTokens: 640, totalCostUsd: 0, startedAtLabel: '5 hr ago', errorNote: 'tool timeout · send_email stub' },
  { id: 'run_4123', workflowId: 'wf_invoice', workflowName: 'Invoice Approval', status: 'succeeded', triggerLabel: 'manual', durationLabel: '0.9s', totalTokens: 290, totalCostUsd: 0, startedAtLabel: '6 hr ago' },
]

export const runSteps: WorkflowStep[] = [
  { id: 's1', runId: 'run_4128', nodeId: 'trigger', nodeType: 'trigger', label: 'New Email', sub: 'trigger · webhook', latencyLabel: '0ms', payload: { from: 'sam.rivera@customer.com', subject: 'Damaged unit — order #58213', body: 'Hi, my order arrived with a cracked housing...' } },
  { id: 's2', runId: 'run_4128', nodeId: 'triage', nodeType: 'agent', label: 'Triage Classifier', sub: 'agent · llama3.1:8b', latencyLabel: '640ms', tokensUsed: 210, payload: { category: 'billing_refund', urgency: 'normal', needs_kb: true } },
  { id: 's3', runId: 'run_4128', nodeId: 'cond', nodeType: 'condition', label: 'needs_kb?', sub: 'condition', latencyLabel: '<1ms', note: 'needs_kb == true → search_kb' },
  { id: 's4', runId: 'run_4128', nodeId: 'searchkb', nodeType: 'tool', label: 'search_kb', sub: 'tool · RAG retrieval', latencyLabel: '310ms', payload: sampleRetrieval.map((c) => ({ source: c.source, score: c.score })) },
  { id: 's5', runId: 'run_4128', nodeId: 'draft', nodeType: 'agent', label: 'Draft Reply Writer', sub: 'agent · llama3.1:8b', latencyLabel: '1,120ms', tokensUsed: 780, payload: { subject: 'Re: Damaged unit — order #58213', confidence: 0.93 } },
  { id: 's6', runId: 'run_4128', nodeId: 'approval', nodeType: 'approval', label: 'Human Review', sub: 'approval', latencyLabel: '—', payload: { decided_by: 'Jordan Avery', status: 'approved', waited: '6m 40s' }, note: 'execution paused here — resumed on approval webhook' },
  { id: 's7', runId: 'run_4128', nodeId: 'sendemail', nodeType: 'tool', label: 'send_email', sub: 'tool · Gmail (stub)', latencyLabel: '240ms', note: 'sent (logged — no live provider configured)' },
  { id: 's8', runId: 'run_4128', nodeId: 'logactivity', nodeType: 'tool', label: 'log_activity', sub: 'tool · CRM write', latencyLabel: '90ms' },
  { id: 's9', runId: 'run_4128', nodeId: 'end', nodeType: 'end', label: 'Resolved', sub: 'end', latencyLabel: '2,140 tok total' },
]

export const approvals: ApprovalRequest[] = [
  {
    id: 'ap1',
    runId: 'run_4128',
    workflowName: 'Customer Support Triage',
    title: 'Reply to Sam Rivera — order #58213',
    requestedBy: 'Draft Reply Writer',
    status: 'pending',
    payloadSubject: 'Re: Damaged unit — order #58213',
    payloadBody:
      "Hi Sam,\n\nThanks for flagging this — I'm sorry the unit arrived damaged. Per our 30-day damaged-goods policy, you're eligible for a full refund or a replacement unit shipped at no cost. Let me know which you'd prefer and I'll process it right away.\n\n— Acme Robotics Support",
  },
  {
    id: 'ap2',
    runId: 'run_4131',
    workflowName: 'Invoice Approval',
    title: 'Invoice #A-2291 — $4,820.00 to Meridian Supplies',
    requestedBy: 'Invoice Approval workflow',
    status: 'pending',
  },
]
