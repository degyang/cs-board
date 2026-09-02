import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TaskWorkbenchPage } from '../src/pages/TaskWorkbenchPage'
import type { CapabilitiesResponse, InputsReadback, StageWorkOrder, TaskDetail } from '../src/lib/api/types'

vi.mock('../src/lib/api/client', async (importOriginal) => ({
  ...await importOriginal<typeof import('../src/lib/api/client')>(),
  fetchTask: vi.fn(), fetchCapabilities: vi.fn(), fetchInputs: vi.fn(), fetchUnits: vi.fn(),
  fetchEvents: vi.fn(), fetchLogs: vi.fn(), uploadInputs: vi.fn(), fetchWorkOrder: vi.fn(),
}))

import { fetchTask, fetchCapabilities, fetchInputs, fetchUnits, fetchEvents, fetchLogs, fetchWorkOrder } from '../src/lib/api/client'

const detail: TaskDetail = {
  task: { task_id: 'task-1', title: '工作单测试', pipeline_id: 'mountain-av-v1', engine: 'whiteboard', status: 'running', created_at: '', updated_at: '', active_run_id: 'run-1', revision: 1, schema_version: 1 },
  active_run: { schema_version: 1, run_id: 'run-1', task_id: 'task-1', trace_id: 'trace-1', entrypoint: 'web', command_ids: [], status: 'pending', target_stage: null, started_at: '', finished_at: null, stages: {}, warnings: [] },
  stages: [], warnings: [], artifacts: [], trace: null,
}
const inputs: InputsReadback = { task_id: 'task-1', saved: true, inputs: { script: '已保存的测试文案。', style: '', include_subtitles: false, pen_text: '', stroke_detail: '' }, reference_audio: { uploaded: true, filename: 'ref.wav', content_type: 'audio/wav', size_bytes: 4 }, rules: null, script_preparation: null, visual_anchor_enabled: true, execution_plan: { mode: 'auto', manual_stages: [] } }
const capabilities: CapabilitiesResponse = { items: [], providers: { all_available: true, unavailable: [], providers: {} } }
const order: StageWorkOrder = { schema_version: '1.0', work_order_id: 'wo-a1', identity: { task_id: 'task-1', run_id: 'run-1', stage: 'clone-voice', skill: 'voice-cloner', pipeline_id: 'mountain-av-v1', engine: 'whiteboard' }, revision: 1, input_fingerprint: 'sha256:' + 'a'.repeat(64), status: 'ready', scope: { kind: 'stage' }, input_artifacts: [{ artifact_key: 'planning.av-plan', revision: 1, sha256: 'sha256:' + 'b'.repeat(64), status: 'succeeded', relative_path: 'artifacts/plan.json' }], parameters_path: 'work-orders/clone-voice/parameters.json', instructions_path: 'work-orders/clone-voice/instructions.md', output_directory: 'work-orders/clone-voice/output', expected_outputs: [{ artifact_key: 'audio.voice-manifest', status: 'succeeded' }], commands: { run: [{ command_id: 'run', argv: ['stage', 'run'], idempotency_key: 'key', preconditions: [] }] }, next_action: { code: 'RUN_AVAILABLE', message: '可使用 run command 执行' } }

describe('Task Workbench Work Order consumer', () => {
  beforeEach(() => {
    vi.mocked(fetchTask).mockResolvedValue(detail); vi.mocked(fetchCapabilities).mockResolvedValue(capabilities); vi.mocked(fetchInputs).mockResolvedValue(inputs)
    vi.mocked(fetchUnits).mockResolvedValue({ items: [] }); vi.mocked(fetchEvents).mockResolvedValue({ items: [], next_cursor: 0 }); vi.mocked(fetchLogs).mockResolvedValue({ items: [] }); vi.mocked(fetchWorkOrder).mockResolvedValue(order)
  })
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('requests the selected stage and renders only safe Work Order summaries', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/tasks/task-1']}><Routes><Route path="/tasks/:taskId" element={<TaskWorkbenchPage />} /></Routes></MemoryRouter>)
    await screen.findByDisplayValue('已保存的测试文案。')
    await user.click(screen.getAllByRole('button', { name: '查看工作单' })[1])
    await waitFor(() => expect(fetchWorkOrder).toHaveBeenCalledWith('task-1', 'run-1', 'clone-voice'))
    expect(await screen.findByText(/下一动作：/)).toBeInTheDocument()
    expect(screen.getByText(/参数：work-orders\/clone-voice\/parameters\.json/)).toBeInTheDocument()
    expect(screen.queryByText('stage run')).not.toBeInTheDocument()
  })

  it('serializes the selected execution mode and canonical stage order', async () => {
    const user = userEvent.setup(); const upload = (await import('../src/lib/api/client')).uploadInputs
    vi.mocked(upload).mockResolvedValue({ ok: true, task_id: 'task-1', input_saved: true, execution_plan: { mode: 'selective', manual_stages: ['generate-illustrations', 'compose-video'] } })
    render(<MemoryRouter initialEntries={['/tasks/task-1']}><Routes><Route path="/tasks/:taskId" element={<TaskWorkbenchPage />} /></Routes></MemoryRouter>)
    await screen.findByDisplayValue('已保存的测试文案。'); await user.click(screen.getByRole('radio', { name: '选择手动阶段' })); await user.click(screen.getByRole('checkbox', { name: '合成成片' })); await user.click(screen.getByRole('checkbox', { name: '生成插画' }))
    await user.click(screen.getByRole('button', { name: '保存制作输入' })); await waitFor(() => expect(upload).toHaveBeenCalled())
    const form = vi.mocked(upload).mock.calls[0][1]; expect(form.get('execution_mode')).toBe('selective'); expect(form.get('manual_stages')).toBe('["generate-illustrations","compose-video"]')
  })
})
