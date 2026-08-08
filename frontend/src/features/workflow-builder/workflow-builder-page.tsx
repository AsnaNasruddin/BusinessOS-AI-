import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Background,
  BackgroundVariant,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Node,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { RectNode } from '@/features/workflow-builder/nodes/rect-node'
import { CircleNode } from '@/features/workflow-builder/nodes/circle-node'
import { ConditionNode } from '@/features/workflow-builder/nodes/condition-node'
import { NodePalette } from '@/features/workflow-builder/node-palette'
import { InspectorPanel } from '@/features/workflow-builder/inspector-panel'
import { RealWorkflowView } from '@/features/workflow-builder/real-workflow-view'
import { initialEdges, initialNodes } from '@/features/workflow-builder/initial-graph'

const nodeTypes = {
  rect: RectNode,
  circle: CircleNode,
  condition: ConditionNode,
}

const RUN_STEPS = [
  'Queued…',
  'Running — Triage Classifier',
  'Running — search_kb',
  'Awaiting approval',
]

export function WorkflowBuilderPage() {
  const { id } = useParams<{ id: string }>()
  if (id) {
    return <RealWorkflowView workflowId={id} />
  }
  return <MockWorkflowBuilder />
}

/** The pre-existing "Customer Support Triage" example — a fixed visual
 * mockup demonstrating the intended design (condition/approval/parallel
 * nodes v0's linear-only engine couldn't run yet when this was built).
 * Left exactly as it was; only reachable at the bare /workflows route now
 * that /workflows/:id renders a real one instead. */
function MockWorkflowBuilder() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges] = useEdgesState(initialEdges)
  const [selectedId, setSelectedId] = useState<string | null>('draft')
  const [runState, setRunState] = useState('Idle')

  const onNodeClick = useCallback<NodeMouseHandler<Node>>((_event, node) => {
    setSelectedId(node.id)
  }, [])

  function handleRun() {
    RUN_STEPS.forEach((label, i) => {
      setTimeout(() => setRunState(label), i * 700)
    })
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-[17px] font-semibold">Customer Support Triage</h2>
          <div className="mt-1 flex gap-2.5 text-xs text-fg-faint">
            <span>v3</span>
            <span>·</span>
            <span>edited 2 hours ago</span>
            <span>·</span>
            <span>trigger: webhook</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-fg-dim">{runState}</span>
          <Link
            to="/workflows/generate"
            className="inline-flex h-8 items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-signal-solid bg-transparent px-3.5 text-[13px] font-medium text-signal-ink transition-colors hover:bg-signal-100"
          >
            ✨ Describe with AI
          </Link>
          <Button>Save</Button>
          <Button variant="primary" onClick={handleRun}>
            ▸ Run
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-[200px_minmax(0,1fr)_300px] items-start gap-4">
        <NodePalette />

        <Card className="overflow-hidden">
          <div style={{ height: 320 }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              nodesConnectable={false}
              fitView
              fitViewOptions={{ padding: 0.15 }}
              proOptions={{ hideAttribution: true }}
              defaultEdgeOptions={{ style: { stroke: 'var(--border)', strokeWidth: 1.6 } }}
            >
              <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="var(--border)" />
            </ReactFlow>
          </div>
        </Card>

        <InspectorPanel nodeId={selectedId} />
      </div>
    </div>
  )
}
