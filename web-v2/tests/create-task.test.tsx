/** CCF-TASK-CREATE-SIX-TAB-18 — explicit test fixtures for the real API boundary. */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { CreateTaskPage } from '../src/pages/CreateTaskPage'

const OPTIONS = {
  engines: [{ id: 'whiteboard', label: '白板动画', available: true }, { id: 'infographic', label: '动态信息图', available: false, reason: 'CAPABILITY_NOT_AVAILABLE' }],
  visual_sources: [{ id: 'preset', label: '预设风格', available: true }, { id: 'custom-reference', label: '自定义参考', available: false, reason: 'CAPABILITY_NOT_AVAILABLE' }],
  voice_sources: [{ id: 'voice-asset', label: '真实音色资产', available: true }, { id: 'uploaded-reference', label: '上传参考音频', available: true }],
  limits: { script_min_chars: 10, target_chars_min: 1, target_chars_max: 500, brand_text_max_chars: 12 },
  defaults: { engine: 'whiteboard', visual_source: 'preset', target_chars: 80, shots_per_image: 2, line_density: 'rich', visual_anchor_enabled: true, include_subtitles: true },
}
const VOICES = { items: [{ voice_id: 'voice-real', name: '真实女声', description: '测试音色', tags: ['中文'], duration_ms: 3200, sample_rate: 48000, channels: 1, format: 'wav', enabled: true, status: 'active', content_url: null, created_at: '', updated_at: '' }, { voice_id: 'voice-disabled', name: '已停用音色', description: '', tags: [], duration_ms: 1000, sample_rate: 48000, channels: 1, format: 'wav', enabled: false, status: 'inactive', content_url: null, created_at: '', updated_at: '' }], next_cursor: null, total: 2 }
const STYLES = { items: [{ style_id: 'style-real', kind: 'preset', name: '真实水彩', description: '测试风格', engine: 'whiteboard', status: 'active', revision: 1, tags: ['水彩'], prompt_text: null, negative_prompt: null, preview_asset_id: 'preview-1', config: {}, created_at: '', updated_at: '' }, { style_id: 'style-disabled', kind: 'preset', name: '停用风格', description: '', engine: 'whiteboard', status: 'inactive', revision: 1, tags: [], prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' }], next_cursor: null, total: 2 }
const CREATED = { ok: true, command: 'task.create', task_id: 'task-new', run_id: 'run-new', trace_id: 'trace-new', command_id: 'cmd-new', event_sequence: 1 }
const SAVED = { ok: true, task_id: 'task-new', input_saved: true, execution_plan: { mode: 'legacy' } }
const fetchMock = vi.fn()

function json(body: unknown, status = 200) { return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body), headers: new Headers({ 'content-type': 'application/json' }) } }
function defaultFetch(url: string) {
  const value = String(url)
  if (value.endsWith('/tasks/create-options')) return json(OPTIONS)
  if (value.includes('/assets/voices')) return json(VOICES)
  if (value.includes('/assets/styles')) return json(STYLES)
  if (value.endsWith('/inputs')) return json(SAVED)
  if (value.endsWith('/tasks')) return json(CREATED)
  return json({ error: { code: 'NOT_FOUND', message: '未找到' } }, 404)
}
beforeEach(() => { fetchMock.mockReset(); fetchMock.mockImplementation(defaultFetch); vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })
function renderPage() { return render(<MemoryRouter initialEntries={['/tasks/new']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /><Route path="/tasks/:id" element={<div>任务工作台</div>} /><Route path="/" element={<div>任务队列</div>} /></Routes></MemoryRouter>) }
function next() { fireEvent.click(screen.getByRole('button', { name: '下一步' })) }
function goFinal() { for (let i = 0; i < 4; i += 1) next() }
function createCalls() { return fetchMock.mock.calls.filter((call) => String(call[0]).endsWith('/tasks')) }
function inputCalls() { return fetchMock.mock.calls.filter((call) => String(call[0]).endsWith('/inputs')) }
async function ready() { await waitFor(() => expect(screen.getByRole('tab', { name: '任务介绍' })).toBeInTheDocument()) }
function fillIntroAndScript() { fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '测试任务' } }); fireEvent.change(screen.getByLabelText('任务摘要'), { target: { value: '用于自动化验收的摘要' } }); next(); fireEvent.change(screen.getByLabelText('原始文案'), { target: { value: '第一句完整内容。第二句完整内容！第三句完整内容？' } }) }

describe('CreateTaskPage six-tab preview-first flow', () => {
  it('shows tabs in the contract order and preserves fields across navigation', async () => {
    renderPage(); await ready()
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent?.trim())).toEqual(['任务介绍', '视频文案0', '声音生成', '输出类型', '视觉设置', '成片设置'])
    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '跨 Tab 状态' } }); next(); fireEvent.change(screen.getByLabelText('原始文案'), { target: { value: '保留这段跨 Tab 的测试文案。' } }); fireEvent.click(screen.getByRole('tab', { name: '任务介绍' })); expect(screen.getByLabelText('任务名称')).toHaveValue('跨 Tab 状态'); next(); expect(screen.getByLabelText('原始文案')).toHaveValue('保留这段跨 Tab 的测试文案。')
  })
  it('renders complete-sentence preview and live character count', async () => {
    renderPage(); await ready(); next(); const script = screen.getByLabelText('原始文案'); fireEvent.change(script, { target: { value: '甲句。乙句！丙句？' } }); fireEvent.change(screen.getByLabelText('目标分段长度'), { target: { value: '3' } }); expect((document.querySelector('textarea.preview') as HTMLTextAreaElement).value).toBe('甲句。\n\n乙句！\n\n丙句？'); expect(screen.getByText('实时字数：').parentElement).toHaveTextContent('9'); expect(screen.getByText(/提交前预览/)).toBeInTheDocument()
  })
  it('loads real voice/style assets with preview URLs and visible disabled state', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '声音生成' })); await waitFor(() => expect(screen.getByText('真实女声')).toBeInTheDocument()); expect(screen.getByText('已停用音色（不可用）')).toBeInTheDocument(); expect(document.querySelector('audio')).toHaveAttribute('src', expect.stringContaining('/assets/voices/voice-real/content')); fireEvent.click(screen.getByRole('tab', { name: '视觉设置' })); await waitFor(() => expect(screen.getByText('真实水彩')).toBeInTheDocument()); expect(screen.getByText('停用风格（不可用）')).toBeInTheDocument(); expect(screen.getByAltText('真实水彩 预览')).toHaveAttribute('src', expect.stringContaining('/assets/blobs/preview-1'))
  })
  it('keeps unavailable engine/source visible and disabled with server reason', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '输出类型' })); expect(screen.getByRole('button', { name: /动态信息图/ })).toBeDisabled(); expect(screen.getByText(/CAPABILITY_NOT_AVAILABLE/)).toBeInTheDocument(); fireEvent.click(screen.getByRole('tab', { name: '视觉设置' })); expect(screen.getByRole('button', { name: /自定义参考/ })).toBeDisabled()
  })
  it('shows a real options error and keeps preview navigation available', async () => {
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks/create-options') ? json({ error: { code: 'OPTIONS_UNAVAILABLE', message: '选项接口待联调' } }, 503) : defaultFetch(url))
    renderPage(); await waitFor(() => expect(screen.getByText(/选项接口待联调/)).toBeInTheDocument()); next(); expect(screen.getByLabelText('原始文案')).toBeInTheDocument(); goFinal(); expect(screen.getByRole('button', { name: '创建并保存 Task' })).toBeDisabled()
  })
  it('renders the final summary from all six-tab selections', async () => {
    renderPage(); await ready(); fillIntroAndScript(); next(); await waitFor(() => expect(screen.getByText('真实女声')).toBeInTheDocument()); next(); next(); fireEvent.click(screen.getByRole('tab', { name: '视觉设置' })); await waitFor(() => expect(screen.getByText('真实水彩')).toBeInTheDocument()); next(); expect(screen.getByText('最终汇总')).toBeInTheDocument(); expect(screen.getByText(/测试任务/)).toBeInTheDocument(); expect(screen.getByText(/真实水彩/)).toBeInTheDocument()
  })
})

describe('CreateTaskPage real submission contract', () => {
  it('sends one create JSON then one multipart input payload and never starts a run', async () => {
    renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText('任务工作台')).toBeInTheDocument()); expect(createCalls()).toHaveLength(1); expect(inputCalls()).toHaveLength(1)
    const createOptions = createCalls()[0][1]; expect(JSON.parse(createOptions.body)).toMatchObject({ title: '测试任务', summary: '用于自动化验收的摘要', engine: 'whiteboard', pipeline_id: 'mountain-av-v1' }); expect(JSON.parse(createOptions.body).submission_id).toEqual(expect.any(String)); const inputOptions = inputCalls()[0][1]; expect(inputOptions.method).toBe('POST'); expect(inputOptions.body).toBeInstanceOf(FormData); const body = inputOptions.body as FormData; expect(body.get('script')).toContain('第一句'); expect(body.get('target_chars')).toBe('80'); expect(body.get('voice_source')).toBe('voice-asset'); expect(body.get('voice_asset_id')).toBe('voice-real'); expect(body.get('visual_source')).toBe('preset'); expect(body.get('style_asset_id')).toBe('style-real'); expect(body.get('shots_per_image')).toBe('2'); expect(body.get('line_density')).toBe('rich'); expect(body.get('visual_anchor_enabled')).toBe('true'); expect(body.get('include_subtitles')).toBe('true'); expect(fetchMock.mock.calls.some((call) => String(call[0]).includes('/start'))).toBe(false)
  })
  it('double submit creates only one Task', async () => {
    let resolveCreate!: (value: unknown) => void; fetchMock.mockImplementation((url) => String(url).endsWith('/tasks') ? new Promise((resolve) => { resolveCreate = resolve }) : defaultFetch(url)); renderPage(); await ready(); fillIntroAndScript(); goFinal(); const form = screen.getByRole('button', { name: '创建并保存 Task' }).closest('form')!; fireEvent.submit(form); fireEvent.submit(form); expect(createCalls()).toHaveLength(1); await act(async () => resolveCreate(json(CREATED))); await waitFor(() => expect(inputCalls()).toHaveLength(1)); expect(createCalls()).toHaveLength(1)
  })
  it('create failure keeps all entered fields and sends no input request', async () => {
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks') ? json({ error: { code: 'CREATE_FAILED', message: '创建失败（测试）' } }, 400) : defaultFetch(url)); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText(/创建失败（测试）/)).toBeInTheDocument()); expect(inputCalls()).toHaveLength(0); fireEvent.click(screen.getByRole('tab', { name: '任务介绍' })); expect(screen.getByLabelText('任务名称')).toHaveValue('测试任务')
  })
  it('input failure exposes task/run and retry only calls input save', async () => {
    let attempts = 0; fetchMock.mockImplementation((url) => { if (String(url).endsWith('/inputs')) { attempts += 1; return attempts === 1 ? json({ error: { code: 'INPUT_FAILED', message: '输入保存失败（测试）' } }, 400) : json(SAVED) }; return defaultFetch(url) }); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText(/输入保存失败（测试）/)).toBeInTheDocument()); expect(screen.getByText(/task_id：task-new · run_id：run-new/)).toBeInTheDocument(); expect(createCalls()).toHaveLength(1); fireEvent.click(screen.getByRole('button', { name: '重试保存输入' })); await waitFor(() => expect(screen.getByText('任务工作台')).toBeInTheDocument()); expect(createCalls()).toHaveLength(1); expect(inputCalls()).toHaveLength(2)
  })
  it('unmount during pending save produces no warning or navigation', async () => {
    let resolveSave!: (value: unknown) => void; fetchMock.mockImplementation((url) => String(url).endsWith('/inputs') ? new Promise((resolve) => { resolveSave = resolve }) : defaultFetch(url)); const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {}); const view = renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(inputCalls()).toHaveLength(1)); view.unmount(); await act(async () => resolveSave(json(SAVED))); expect(errorSpy).not.toHaveBeenCalled(); errorSpy.mockRestore()
  })
})
