import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Agent, MemoryScope, ModelProvider, Tool } from '@/types'

interface AgentRaw {
  id: string
  org_id: string
  name: string
  description: string
  system_prompt: string
  model_provider: ModelProvider
  model_name: string
  temperature: number
  allowed_tools: string[]
  memory_scope: MemoryScope
}

interface ToolRaw {
  id: string
  name: string
  display_name: string
  description: string
  category: string
}

function toAgent(raw: AgentRaw): Agent {
  return {
    id: raw.id,
    orgId: raw.org_id,
    name: raw.name,
    description: raw.description,
    systemPrompt: raw.system_prompt,
    modelProvider: raw.model_provider,
    modelName: raw.model_name,
    temperature: raw.temperature,
    allowedTools: raw.allowed_tools,
    memoryScope: raw.memory_scope,
  }
}

function toTool(raw: ToolRaw): Tool {
  return {
    id: raw.id,
    name: raw.name,
    displayName: raw.display_name,
    description: raw.description,
    category: raw.category,
  }
}

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const { data } = await api.get<AgentRaw[]>('/agents')
      return data.map(toAgent)
    },
  })
}

export function useTools() {
  return useQuery({
    queryKey: ['tools'],
    queryFn: async () => {
      const { data } = await api.get<ToolRaw[]>('/tools')
      return data.map(toTool)
    },
  })
}
