/** CCF-TASK-CREATE-SIX-TAB-18 — explicit test fixtures for the real API boundary. */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act, cleanup } from '@testing-library/react'
import { StrictMode } from 'react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { CreateTaskPage } from '../src/pages/CreateTaskPage'

const OPTIONS = {
  engines: [{ id: 'whiteboard', label: '白板动画', available: true }, { id: 'infographic-remotion', label: '动态信息图', available: false, reason: 'CAPABILITY_NOT_AVAILABLE' }],
  visual_sources: [{ id: 'preset', label: '预设风格', available: true }, { id: 'custom-reference', label: '自定义参考', available: false, reason: 'CAPABILITY_NOT_AVAILABLE' }],
  voice_sources: [{ id: 'voice-asset', label: '真实音色资产', available: true }, { id: 'uploaded-reference', label: '上传参考音频', available: true }],
  limits: { script_min_chars: 10, target_chars_min: 5, target_chars_max: 500, brand_text_max_chars: 12 },
  defaults: { engine: 'whiteboard', visual_source: 'preset', target_chars: 45, shots_per_image: 2, line_density: 'rich', visual_anchor_enabled: true, include_subtitles: true },
}
const VOICES = { items: [{ voice_id: 'voice-real', name: '真实女声', description: '测试音色', tags: ['中文'], duration_ms: 3200, sample_rate: 48000, channels: 1, format: 'wav', enabled: true, status: 'active', content_url: null, language: '普通话', emotion_mode: '自然', example_text: '这是一段来自真实音色资产的示例。', availability_status: 'verified', status_note: '已通过样例试听验证', engine: 'qwen-tts', compatibility: { engines: ['whiteboard'], emotion_modes: ['自然'], limitations: [] }, created_at: '', updated_at: '' }, { voice_id: 'voice-disabled', name: '已停用音色', description: '', tags: [], duration_ms: 1000, sample_rate: 48000, channels: 1, format: 'wav', enabled: false, status: 'inactive', content_url: null, created_at: '', updated_at: '' }], next_cursor: null, total: 2 }
const STYLES = { items: [{ style_id: 'style-real', kind: 'preset', name: '真实水彩', description: '测试风格', engine: 'whiteboard', status: 'active', revision: 1, tags: ['水彩'], prompt_text: null, negative_prompt: null, preview_asset_id: 'preview-1', config: {}, created_at: '', updated_at: '' }, { style_id: 'style-disabled', kind: 'preset', name: '停用风格', description: '', engine: 'whiteboard', status: 'inactive', revision: 1, tags: [], prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' }], next_cursor: null, total: 2 }
const AUTHORITATIVE_PREVIEW = {
  algorithm_version: 'paragraph-first-v2', raw_script: '医学2.0 和医学3.0。\r\n\r\n这是什么意思呢？', normalized_processing_text: '医学2.0 和医学3.0。\n这是什么意思呢？', rules: { target_chars: 70, min_chars: 42, max_chars: 140 },
  source_mapping: {
    index_unit: 'unicode-code-point', range_semantics: 'zero-based, end-exclusive', raw_length: 25, normalized_length: 22,
    paragraphs: [
      { raw_range: { start: 0, end: 13 }, paragraph_index: 1, normalized_range: { start: 0, end: 13 } },
      { raw_range: { start: 17, end: 25 }, paragraph_index: 2, normalized_range: { start: 14, end: 22 } },
    ],
    raw_to_normalized: [
      { raw_range: { start: 0, end: 13 }, normalized_range: { start: 0, end: 13 } },
      { raw_range: { start: 17, end: 25 }, normalized_range: { start: 14, end: 22 } },
    ],
    normalized_to_raw: [
      { normalized_range: { start: 0, end: 13 }, raw_range: { start: 0, end: 13 } },
      { normalized_range: { start: 14, end: 22 }, raw_range: { start: 17, end: 25 } },
    ],
    ignored_raw_ranges: [{ start: 13, end: 17, reason: 'paragraph-boundary' }],
  },
  voice_units: [
    { unit_id: 'unit-001', order: 1, text: '医学2.0 和医学3.0。', paragraph_index: 1, source_range: { start: 0, end: 13 }, normalized_range: { start: 0, end: 13 }, boundary_reason: 'paragraph', undersize_reason: 'paragraph-boundary' },
    { unit_id: 'unit-002', order: 2, text: '这是什么意思呢？', paragraph_index: 2, source_range: { start: 17, end: 25 }, normalized_range: { start: 14, end: 22 }, boundary_reason: 'paragraph', undersize_reason: 'paragraph-boundary' },
  ],
}
const CCB_EDGE_MATRIX_RESPONSE = {
  ...AUTHORITATIVE_PREVIEW,
  raw_script: '医学2.0、医学3.0、IP 127.0.0.1、日期 2026.09.03。访问 example.com/path、a@b.com、v1.2.txt；Dr. Wang 说 U.S. 与 e.g.。\n\n“引号、括号（和省略号……）？！都由权威服务保留。”\n\n身体、医学2.0、医学3.0、冰山、在面对慢性健康问题时的现状均保持权威返回的边界。',
  normalized_processing_text: '医学2.0、医学3.0、IP 127.0.0.1、日期 2026.09.03。访问 example.com/path、a@b.com、v1.2.txt；Dr. Wang 说 U.S. 与 e.g.。\n“引号、括号（和省略号……）？！都由权威服务保留。”\n身体、医学2.0、医学3.0、冰山、在面对慢性健康问题时的现状均保持权威返回的边界。',
  source_mapping: {
    index_unit: 'unicode-code-point', range_semantics: 'zero-based, end-exclusive', raw_length: 171, normalized_length: 169,
    paragraphs: [
      { raw_range: { start: 0, end: 99 }, paragraph_index: 1, normalized_range: { start: 0, end: 99 } },
      { raw_range: { start: 101, end: 127 }, paragraph_index: 2, normalized_range: { start: 100, end: 126 } },
      { raw_range: { start: 129, end: 171 }, paragraph_index: 3, normalized_range: { start: 127, end: 169 } },
    ],
    raw_to_normalized: [
      { raw_range: { start: 0, end: 99 }, normalized_range: { start: 0, end: 99 } },
      { raw_range: { start: 101, end: 127 }, normalized_range: { start: 100, end: 126 } },
      { raw_range: { start: 129, end: 171 }, normalized_range: { start: 127, end: 169 } },
    ],
    normalized_to_raw: [
      { normalized_range: { start: 0, end: 99 }, raw_range: { start: 0, end: 99 } },
      { normalized_range: { start: 100, end: 126 }, raw_range: { start: 101, end: 127 } },
      { normalized_range: { start: 127, end: 169 }, raw_range: { start: 129, end: 171 } },
    ],
    ignored_raw_ranges: [{ start: 99, end: 101, reason: 'paragraph-boundary' }, { start: 127, end: 129, reason: 'paragraph-boundary' }],
  },
  voice_units: [
    { unit_id: 'unit-001', order: 1, text: '医学2.0、医学3.0、IP 127.0.0.1、日期 2026.09.03。访问 example.com/path、a@b.com、v1.2.txt；Dr. Wang 说 U.S. 与 e.g.。', paragraph_index: 1, source_range: { start: 0, end: 99 }, normalized_range: { start: 0, end: 99 }, boundary_reason: 'paragraph', undersize_reason: null },
    { unit_id: 'unit-002', order: 2, text: '“引号、括号（和省略号……）？！都由权威服务保留。”', paragraph_index: 2, source_range: { start: 101, end: 127 }, normalized_range: { start: 100, end: 126 }, boundary_reason: 'paragraph', undersize_reason: 'paragraph-boundary' },
    { unit_id: 'unit-003', order: 3, text: '身体、医学2.0、医学3.0、冰山、在面对慢性健康问题时的现状均保持权威返回的边界。', paragraph_index: 3, source_range: { start: 129, end: 171 }, normalized_range: { start: 127, end: 169 }, boundary_reason: 'paragraph', undersize_reason: null },
  ],
}
const CREATED = { ok: true, command: 'task.create', task_id: 'task-new', run_id: 'run-new', trace_id: 'trace-new', command_id: 'cmd-new', event_sequence: 1 }
const SAVED = { ok: true, task_id: 'task-new', input_saved: true, execution_plan: { mode: 'legacy' } }
const RECOVERY_TASK = { task: { task_id: 'task-recovered', title: '恢复任务', summary: '恢复摘要', engine: 'whiteboard', active_run_id: 'run-recovered' }, active_run: { task_id: 'task-recovered', run_id: 'run-recovered' }, stages: [], warnings: [], artifacts: [], trace: { trace_id: 'trace-recovered', command_ids: [] } }
function recoveryInputs(uploaded = true) { return { task_id: 'task-recovered', saved: true, inputs: { script: '恢复文案内容足够长。', style: 'style-real', voice_source: 'voice-asset', voice_asset_id: 'voice-real', visual_source: 'preset', style_asset_id: 'style-real', target_chars: 20, shots_per_image: 3, line_density: 'minimal', brand_text: '恢复品牌', include_subtitles: false, pen_text: '', stroke_detail: '' }, reference_audio: { uploaded, filename: uploaded ? 'old.wav' : null }, rules: { target_chars: 20, min_chars: 1, max_chars: 500 }, script_preparation: null, visual_anchor_enabled: false, execution_plan: { mode: 'legacy' } } }
const fetchMock = vi.fn()

function json(body: unknown, status = 200) { return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body), headers: new Headers({ 'content-type': 'application/json' }) } }
function defaultFetch(url: string) {
  const value = String(url)
  if (value.endsWith('/tasks/create-options')) return json(OPTIONS)
  if (value.endsWith('/scripts/prepare')) return json(AUTHORITATIVE_PREVIEW)
  if (value.includes('/assets/voices')) return json(VOICES)
  if (value.includes('/assets/styles')) return json(STYLES)
  if (value.endsWith('/inputs')) return json(SAVED)
  if (value.endsWith('/tasks')) return json(CREATED)
  return json({ error: { code: 'NOT_FOUND', message: '未找到' } }, 404)
}
beforeEach(() => { fetchMock.mockReset(); fetchMock.mockImplementation(defaultFetch); vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })
function renderPage() { return render(<MemoryRouter initialEntries={['/tasks/new']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /><Route path="/tasks/:id" element={<div data-testid="active-workbench">任务工作台</div>} /><Route path="/" element={<div>任务队列</div>} /></Routes></MemoryRouter>) }
function next() { fireEvent.click(screen.getByRole('button', { name: '下一步' })) }
function goFinal() { for (let i = 0; i < 4; i += 1) next() }
function createCalls() { return fetchMock.mock.calls.filter((call) => String(call[0]).endsWith('/tasks')) }
function inputCalls() { return fetchMock.mock.calls.filter((call) => String(call[0]).endsWith('/inputs')) }
function inputSaveCalls() { return fetchMock.mock.calls.filter((call) => String(call[0]).endsWith('/inputs') && call[1]?.method === 'POST') }
async function ready() { await waitFor(() => expect(screen.getByRole('tab', { name: '任务介绍' })).toBeInTheDocument()) }
function fillIntroAndScript() { fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '测试任务' } }); fireEvent.change(screen.getByLabelText('任务摘要'), { target: { value: '用于自动化验收的摘要' } }); next(); fireEvent.change(screen.getByLabelText('原始文案'), { target: { value: '第一句完整内容。第二句完整内容！第三句完整内容？' } }) }
function renderRecoveryRoute(taskId = 'task-recovered', runId = 'run-recovered') { return render(<MemoryRouter initialEntries={[`/tasks/new?task_id=${taskId}&run_id=${runId}&tab=final`]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /><Route path="/tasks/:id" element={<div data-testid="active-workbench">任务工作台</div>} /></Routes></MemoryRouter>) }
function recoveryPage(taskId = 'task-recovered', runId = 'run-recovered', inputBody = recoveryInputs()) { fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith(`/tasks/${taskId}/inputs`)) return json({ ...inputBody, task_id: taskId }); if (value.endsWith(`/tasks/${taskId}`)) return json({ ...RECOVERY_TASK, task: { ...RECOVERY_TASK.task, task_id: taskId, active_run_id: runId }, active_run: { ...RECOVERY_TASK.active_run, task_id: taskId, run_id: runId } }); return defaultFetch(url) }); return renderRecoveryRoute(taskId, runId) }

describe('CreateTaskPage six-tab preview-first flow', () => {
  it('shows tabs in the contract order and preserves fields across navigation', async () => {
    renderPage(); await ready()
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent?.trim())).toEqual(['任务介绍', '视频文案0', '声音生成', '输出类型', '视觉设置', '成片设置'])
    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '跨 Tab 状态' } }); next(); fireEvent.change(screen.getByLabelText('原始文案'), { target: { value: '保留这段跨 Tab 的测试文案。' } }); fireEvent.click(screen.getByRole('tab', { name: '任务介绍' })); expect(screen.getByLabelText('任务名称')).toHaveValue('跨 Tab 状态'); next(); expect(screen.getByLabelText('原始文案')).toHaveValue('保留这段跨 Tab 的测试文案。')
  })
  it('moves roving focus and exposes a matching active tabpanel for keyboard navigation', async () => {
    renderPage(); await ready(); const intro = screen.getByRole('tab', { name: '任务介绍' }); fireEvent.keyDown(intro, { key: 'ArrowRight' }); const script = screen.getByRole('tab', { name: /视频文案/ }); expect(script).toHaveFocus(); expect(script).toHaveAttribute('tabindex', '0'); expect(intro).toHaveAttribute('tabindex', '-1'); expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'tab-panel-script'); expect(script).toHaveAttribute('aria-controls', 'tab-panel-script'); fireEvent.keyDown(script, { key: 'ArrowLeft' }); expect(intro).toHaveFocus(); fireEvent.keyDown(intro, { key: 'End' }); const final = screen.getByRole('tab', { name: '成片设置' }); expect(final).toHaveFocus(); fireEvent.keyDown(final, { key: 'Home' }); expect(intro).toHaveFocus(); expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'tab-intro')
  })
  it('renders API-produced authoritative units without parsing or injecting layout whitespace', async () => {
    renderPage(); await ready(); next(); const script = screen.getByLabelText('原始文案'); const raw = '医学2.0 和医学3.0。\r\n\r\n这是什么意思呢？'; const browserRaw = raw.replace(/\r\n/gu, '\n'); fireEvent.change(script, { target: { value: raw } }); fireEvent.change(screen.getByLabelText('目标分段长度'), { target: { value: '70' } }); await waitFor(() => expect(screen.getByText('paragraph-first-v2')).toBeInTheDocument()); expect(screen.getByLabelText('原始文案')).toHaveValue(browserRaw); const units = screen.getAllByRole('listitem'); expect(units.map((unit) => unit.querySelector('.script-preview-unit-text')?.textContent)).toEqual(AUTHORITATIVE_PREVIEW.voice_units.map((unit) => unit.text)); expect(units.every((unit) => !/[\r\n]/u.test(unit.querySelector('.script-preview-unit-text')?.textContent || ''))).toBe(true); expect(units[1]).toHaveAttribute('data-undersize-reason', 'paragraph-boundary'); expect(screen.getByText(/权威规则/)).toHaveTextContent('最小'); const previewCalls = fetchMock.mock.calls.filter((call) => String(call[0]).endsWith('/scripts/prepare')); expect(JSON.parse(previewCalls[previewCalls.length - 1][1].body)).toEqual({ script: browserRaw, target_chars: 70 })
  })
  it('renders every CCB edge-matrix unit unchanged, including context-sensitive punctuation and mapping metadata', async () => {
    fetchMock.mockImplementation((url) => String(url).endsWith('/scripts/prepare') ? json(CCB_EDGE_MATRIX_RESPONSE) : defaultFetch(url))
    renderPage(); await ready(); next(); fireEvent.change(screen.getByLabelText('原始文案'), { target: { value: CCB_EDGE_MATRIX_RESPONSE.raw_script } }); await waitFor(() => expect(screen.getAllByRole('listitem')).toHaveLength(CCB_EDGE_MATRIX_RESPONSE.voice_units.length)); const units = screen.getAllByRole('listitem'); expect(units.map((unit) => unit.querySelector('.script-preview-unit-text')?.textContent)).toEqual(CCB_EDGE_MATRIX_RESPONSE.voice_units.map((unit) => unit.text)); expect(units.map((unit) => unit.getAttribute('data-boundary-reason'))).toEqual(CCB_EDGE_MATRIX_RESPONSE.voice_units.map((unit) => unit.boundary_reason)); expect(units.map((unit) => unit.textContent)).toEqual(CCB_EDGE_MATRIX_RESPONSE.voice_units.map((unit) => `${unit.text}#${unit.order} · 段落 ${unit.paragraph_index} · ${unit.boundary_reason}${unit.undersize_reason ? ` · ${unit.undersize_reason}` : ''} · raw ${unit.source_range.start}–${unit.source_range.end} · normalized ${unit.normalized_range.start}–${unit.normalized_range.end}`)); expect(CCB_EDGE_MATRIX_RESPONSE.source_mapping.ignored_raw_ranges).toEqual([{ start: 99, end: 101, reason: 'paragraph-boundary' }, { start: 127, end: 129, reason: 'paragraph-boundary' }]); const renderedUnitText = units.map((unit) => unit.querySelector('.script-preview-unit-text')?.textContent).join('\n'); for (const token of ['身体', '医学2.0', '医学3.0', '127.0.0.1', 'example.com', 'a@b.com', 'v1.2.txt', 'Dr.', 'U.S.', 'e.g.', '……', '？！', '冰山', '在面对慢性健康问题时的现状']) expect(renderedUnitText).toContain(token); expect(units.every((unit) => !/[\r\n]/u.test(unit.textContent || ''))).toBe(true)
  })
  it('loads real voice/style assets with preview URLs and visible disabled state', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '声音生成' })); await waitFor(() => expect(screen.getAllByText('真实女声').length).toBeGreaterThan(0)); expect(screen.getByText('已停用音色（不可用）')).toBeInTheDocument(); expect(document.querySelectorAll('audio')).toHaveLength(1); expect(document.querySelector('audio')).toHaveAttribute('src', expect.stringContaining('/assets/voices/voice-real/content')); fireEvent.click(screen.getByRole('tab', { name: '视觉设置' })); await waitFor(() => expect(screen.getByAltText('真实水彩 预览')).toBeInTheDocument()); expect(screen.getByText('停用风格（不可用）')).toBeInTheDocument(); expect(screen.getByAltText('真实水彩 预览')).toHaveAttribute('src', expect.stringContaining('/assets/blobs/preview-1')); expect(fetchMock.mock.calls.some((call) => String(call[0]).includes('/assets/styles?kind=preset') && !String(call[0]).includes('engine='))).toBe(true)
  })
  it('keeps unavailable engine/source visible and disabled with server reason', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '输出类型' })); expect(screen.getByRole('button', { name: /动态信息图/ })).toBeDisabled(); expect(screen.getByText(/CAPABILITY_NOT_AVAILABLE/)).toBeInTheDocument(); fireEvent.click(screen.getByRole('tab', { name: '视觉设置' })); expect(screen.getByRole('button', { name: /自定义参考/ })).toBeDisabled()
  })
  it('shows a real options error and keeps preview navigation available', async () => {
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks/create-options') ? json({ error: { code: 'OPTIONS_UNAVAILABLE', message: '选项接口待联调' } }, 503) : defaultFetch(url))
    renderPage(); await waitFor(() => expect(screen.getByText(/选项接口待联调/)).toBeInTheDocument()); next(); expect(screen.getByLabelText('原始文案')).toBeInTheDocument(); goFinal(); expect(screen.getByRole('button', { name: '创建并保存 Task' })).toBeDisabled()
  })
  it('starts with the shared 45/2/rich defaults before any recovery', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: /视频文案/ })); expect(screen.getByLabelText('目标分段长度')).toHaveValue(45); fireEvent.click(screen.getByRole('tab', { name: /成片设置/ })); expect(screen.getByLabelText('每张图分镜数')).toHaveValue('2'); expect(screen.getByLabelText('线条绘制量')).toHaveValue('rich')
  })
  it('shows the backend default output root without inventing a task package path', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: /成片设置/ })); expect(screen.getByLabelText('输出目录')).toHaveValue(''); expect(screen.getByText(/后端默认项目 outputs\//)).toBeInTheDocument(); expect(screen.queryByText(/Task ID：/)).not.toBeInTheDocument()
  })
  it('keeps recovered values when options resolve before or after recovery', async () => {
    let resolveOptions!: (value: unknown) => void; fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/task-recovered')) return json(RECOVERY_TASK); if (value.endsWith('/tasks/task-recovered/inputs')) return json(recoveryInputs()); if (value.endsWith('/tasks/create-options')) return new Promise((resolve) => { resolveOptions = resolve }); return defaultFetch(url) }); const view = render(<MemoryRouter initialEntries={['/tasks/new?task_id=task-recovered&run_id=run-recovered&tab=final']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /></Routes></MemoryRouter>); await waitFor(() => expect(screen.getByLabelText('每张图分镜数')).toHaveValue('3')); fireEvent.click(screen.getByRole('tab', { name: /视频文案/ })); await waitFor(() => expect(screen.getByLabelText('目标分段长度')).toHaveValue(20)); await act(async () => resolveOptions(json(OPTIONS))); expect(screen.getByLabelText('目标分段长度')).toHaveValue(20); view.unmount()
    let resolveInputsSecond!: (value: unknown) => void; fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/task-recovered')) return json(RECOVERY_TASK); if (value.endsWith('/tasks/task-recovered/inputs')) return new Promise((resolve) => { resolveInputsSecond = resolve }); if (value.endsWith('/tasks/create-options')) return json(OPTIONS); return defaultFetch(url) }); render(<MemoryRouter initialEntries={['/tasks/new?task_id=task-recovered&run_id=run-recovered&tab=final']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /></Routes></MemoryRouter>); await act(async () => resolveInputsSecond(json(recoveryInputs()))); await waitFor(() => expect(screen.getByLabelText('线条绘制量')).toHaveValue('minimal')); fireEvent.click(screen.getByRole('tab', { name: /视频文案/ })); expect(screen.getByLabelText('目标分段长度')).toHaveValue(20)
  })
  it('renders the final summary from all six-tab selections', async () => {
    renderPage(); await ready(); fillIntroAndScript(); next(); await waitFor(() => expect(screen.getByLabelText('真实女声试听')).toBeInTheDocument()); next(); next(); fireEvent.click(screen.getByRole('tab', { name: '视觉设置' })); await waitFor(() => expect(screen.getByAltText('真实水彩 独立参考预览')).toBeInTheDocument()); next(); const summary = screen.getByLabelText('最终汇总'); expect(summary).toHaveTextContent('任务：测试任务'); expect(summary).toHaveTextContent('视觉：真实水彩')
  })
})

describe('CreateTaskPage golden parity for the last four tabs', () => {
  it('shows the voice-library guidance, selected metadata, sample and single audition player', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '声音生成' }))
    await waitFor(() => expect(screen.getByText('音色库示例')).toBeInTheDocument())
    expect(screen.getByText(/音色管理/)).toBeInTheDocument()
    expect(screen.getByText(/普通话 · 自然 · 3.2 秒 · qwen-tts/)).toBeInTheDocument()
    expect(screen.getByText(/这是一段来自真实音色资产的示例/)).toBeInTheDocument()
    expect(screen.getByText('已通过样例试听验证')).toBeInTheDocument()
    expect(document.querySelectorAll('audio')).toHaveLength(1)
  })

  it('shows examples, fit and the server-disabled state for both output types', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '输出类型' }))
    expect(screen.getByText('示例：概念拆解、课程知识点、方法步骤')).toBeInTheDocument()
    expect(screen.getByText('适合：讲解型内容与知识科普')).toBeInTheDocument()
    expect(screen.getByText('示例：数据对比、趋势复盘、商业报告')).toBeInTheDocument()
    expect(screen.getByText(/白板动画强调“逐笔讲解”/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /动态信息图/ })).toBeDisabled()
  })

  it('unions a missing product engine into the UI and previews it without changing the submitted engine', async () => {
    const whiteboardOnly = { ...OPTIONS, engines: [{ id: 'whiteboard', label: '白板动画', available: true }] }
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks/create-options') ? json(whiteboardOnly) : defaultFetch(url))
    renderPage(); await ready(); fillIntroAndScript(); fireEvent.click(screen.getByRole('tab', { name: '输出类型' }))
    const unavailable = await screen.findByRole('button', { name: /动态信息图/ })
    expect(unavailable).toBeDisabled()
    expect(unavailable).toHaveTextContent('服务端：服务端未提供此引擎')
    fireEvent.click(screen.getByRole('button', { name: '查看未开放引擎的成片说明' }))
    expect(screen.getByRole('heading', { name: '成片设置 · 动态信息图' })).toBeInTheDocument()
    expect(screen.getByRole('status', { name: '只读引擎预览' })).toHaveTextContent('真实提交引擎仍为 白板动画')
    expect(screen.getByLabelText('最终汇总')).toHaveTextContent('真实提交引擎：白板动画')
    expect(screen.queryByLabelText('每张图分镜数')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' }))
    await waitFor(() => expect(screen.getByTestId('active-workbench')).toBeInTheDocument())
    expect(JSON.parse(createCalls()[0][1].body)).toMatchObject({ engine: 'whiteboard' })
  })

  it('shows visual-source guidance, combination capability and independent selected preview', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '视觉设置' }))
    await waitFor(() => expect(screen.getByText('预设风格库示例')).toBeInTheDocument())
    expect(screen.getByRole('status', { name: '当前视觉组合状态' })).toHaveTextContent('白板动画 + 预设风格')
    expect(screen.getByAltText('真实水彩 独立参考预览')).toBeInTheDocument()
    expect(screen.getByText(/revision 1 · whiteboard · 水彩/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /自定义参考/ })).toHaveTextContent('风格参考图与 1–5 个人物组')
  })

  it('renders whiteboard controls and keeps unsupported manual execution visible but disabled', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '成片设置' }))
    expect(screen.getByRole('heading', { name: '成片设置 · 白板动画' })).toBeInTheDocument()
    expect(screen.getByLabelText('每张图分镜数')).toHaveDisplayValue('2 个分镜（推荐）')
    expect(screen.getByText(/Shot 是同一张图片的渲染分镜/)).toBeInTheDocument()
    expect(screen.getByText('画面锚定重点文字')).toBeInTheDocument()
    expect(screen.getByLabelText('执行策略')).toBeDisabled()
    expect(screen.getByRole('option', { name: '手动完成（服务端尚未开放）' })).toBeDisabled()
    expect(screen.getByRole('group', { name: '手动完成能力预览（未开放）' })).toBeDisabled()
    expect(screen.getByLabelText('可选择的人工触发阶段')).toHaveTextContent('画面锚定配音分镜插画动画/渲染合成')
    expect(screen.getByLabelText('输出目录')).toBeInTheDocument()
  })

  it('switches to the infographic-only feature branch when the server opens that engine', async () => {
    const infographicOptions = { ...OPTIONS, engines: OPTIONS.engines.map((item) => item.id === 'infographic-remotion' ? { ...item, available: true, reason: undefined } : item), defaults: { ...OPTIONS.defaults, engine: 'infographic-remotion' } }
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks/create-options') ? json(infographicOptions) : defaultFetch(url))
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '成片设置' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: '成片设置 · 动态信息图' })).toBeInTheDocument())
    expect(screen.getByText('语义时间轴')).toBeInTheDocument()
    expect(screen.getByText('智能结构')).toBeInTheDocument()
    expect(screen.getByText('文字安全')).toBeInTheDocument()
    expect(screen.queryByLabelText('每张图分镜数')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('线条绘制量')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('账号/笔身文字')).not.toBeInTheDocument()
  })
})

describe('CreateTaskPage real submission contract', () => {
  it('sends one create JSON then one multipart input payload and never starts a run', async () => {
    renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText('任务工作台')).toBeInTheDocument()); expect(createCalls()).toHaveLength(1); expect(inputCalls()).toHaveLength(1)
    const createOptions = createCalls()[0][1]; expect(JSON.parse(createOptions.body)).toMatchObject({ title: '测试任务', summary: '用于自动化验收的摘要', engine: 'whiteboard', pipeline_id: 'mountain-av-v1' }); const submissionId = JSON.parse(createOptions.body).submission_id as string; expect(submissionId).toEqual(expect.any(String)); expect(submissionId.length).toBeGreaterThanOrEqual(16); expect(new Set(submissionId).size / submissionId.length).toBeGreaterThanOrEqual(0.45); const inputOptions = inputCalls()[0][1]; expect(inputOptions.method).toBe('POST'); expect(inputOptions.body).toBeInstanceOf(FormData); const body = inputOptions.body as FormData; expect(body.get('script')).toContain('第一句'); expect(body.get('target_chars')).toBe('45'); expect(body.get('voice_source')).toBe('voice-asset'); expect(body.get('voice_asset_id')).toBe('voice-real'); expect(body.get('visual_source')).toBe('preset'); expect(body.get('style_asset_id')).toBe('style-real'); expect(body.get('shots_per_image')).toBe('2'); expect(body.get('line_density')).toBe('rich'); expect(body.get('visual_anchor_enabled')).toBe('true'); expect(body.get('include_subtitles')).toBe('true'); expect(fetchMock.mock.calls.some((call) => /\/start|\/stages\/|\/gate/i.test(String(call[0])))).toBe(false)
  })
  it('sends a custom output root unchanged and displays only backend package placement', async () => {
    fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks')) return json({ ...CREATED, output_root: '/project/exports', package_path: '/project/exports/task-new' }); if (value.endsWith('/inputs')) return json({ error: { code: 'INPUT_FAILED', message: '输入保存失败（测试）' } }, 400); return defaultFetch(url) })
    renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.change(screen.getByLabelText('输出目录'), { target: { value: 'exports/final' } }); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText('后端输出：/project/exports/task-new')).toBeInTheDocument()); const body = JSON.parse(createCalls()[0][1].body); expect(body.output_root).toBe('exports/final'); expect(screen.getByText('Task ID：task-new')).toBeInTheDocument(); expect(document.body).not.toHaveTextContent('exports/final/task-new')
  })
  it('surfaces backend output-root and submission conflict codes', async () => {
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks') ? json({ error: { code: 'OUTPUT_ROOT_FORBIDDEN', message: '输出目录必须位于项目目录内' } }, 400) : defaultFetch(url)); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.change(screen.getByLabelText('输出目录'), { target: { value: '../outside' } }); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText(/OUTPUT_ROOT_FORBIDDEN：输出目录必须位于项目目录内/)).toBeInTheDocument()); cleanup()
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks') ? json({ error: { code: 'SUBMISSION_CONFLICT', message: '同一 submission_id 已用于其他请求参数' } }, 409) : defaultFetch(url)); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText(/SUBMISSION_CONFLICT：同一 submission_id 已用于其他请求参数/)).toBeInTheDocument())
  })
  it('double submit creates only one Task', async () => {
    let resolveCreate!: (value: unknown) => void; fetchMock.mockImplementation((url) => String(url).endsWith('/tasks') ? new Promise((resolve) => { resolveCreate = resolve }) : defaultFetch(url)); renderPage(); await ready(); fillIntroAndScript(); goFinal(); const form = screen.getByRole('button', { name: '创建并保存 Task' }).closest('form')!; fireEvent.submit(form); fireEvent.submit(form); expect(createCalls()).toHaveLength(1); await act(async () => resolveCreate(json(CREATED))); await waitFor(() => expect(inputCalls()).toHaveLength(1)); expect(createCalls()).toHaveLength(1)
  })
  it('reuses the submission id after a response-lost create retry', async () => {
    let attempts = 0; fetchMock.mockImplementation((url) => { if (String(url).endsWith('/tasks')) { attempts += 1; return attempts === 1 ? Promise.reject(new Error('network socket /mnt/private/token=secret')) : json(CREATED) }; return defaultFetch(url) }); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText(/网络请求失败，请稍后重试/)).toBeInTheDocument()); const firstBody = JSON.parse(createCalls()[0][1].body); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByTestId('active-workbench')).toBeInTheDocument()); const secondBody = JSON.parse(createCalls()[1][1].body); expect(secondBody.submission_id).toBe(firstBody.submission_id); expect(inputCalls()).toHaveLength(1)
  })
  it('creates only once under StrictMode and keeps create/save loading states disabled', async () => {
    let resolveCreate!: (value: unknown) => void; let resolveSave!: (value: unknown) => void; fetchMock.mockImplementation((url, init) => { const value = String(url); if (value.endsWith('/tasks')) return new Promise((resolve) => { resolveCreate = resolve }); if (value.endsWith('/inputs') && init?.method === 'POST') return new Promise((resolve) => { resolveSave = resolve }); return defaultFetch(url) }); render(<StrictMode><MemoryRouter initialEntries={['/tasks/new']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /><Route path="/tasks/:id" element={<div>任务工作台</div>} /></Routes></MemoryRouter></StrictMode>); await ready(); fillIntroAndScript(); goFinal(); const button = screen.getByRole('button', { name: '创建并保存 Task' }); await waitFor(() => expect(button).toBeEnabled()); fireEvent.click(button); expect(button).toBeDisabled(); expect(createCalls()).toHaveLength(1); await act(async () => resolveCreate(json(CREATED))); await waitFor(() => expect(inputSaveCalls()).toHaveLength(1)); expect(screen.getByRole('button', { name: '重试保存输入' })).toBeDisabled(); await act(async () => resolveSave(json(SAVED))); await waitFor(() => expect(screen.getByText('任务工作台')).toBeInTheDocument())
  })
  it('create failure keeps all entered fields and sends no input request', async () => {
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks') ? json({ error: { code: 'CREATE_FAILED', message: '创建失败（测试）' } }, 400) : defaultFetch(url)); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText(/创建失败（测试）/)).toBeInTheDocument()); expect(inputCalls()).toHaveLength(0); fireEvent.click(screen.getByRole('tab', { name: '任务介绍' })); expect(screen.getByLabelText('任务名称')).toHaveValue('测试任务')
  })
  it('input failure exposes task/run and retry only calls input save', async () => {
    let attempts = 0; fetchMock.mockImplementation((url) => { if (String(url).endsWith('/inputs')) { attempts += 1; return attempts === 1 ? json({ error: { code: 'INPUT_FAILED', message: '输入保存失败（测试）' } }, 400) : json(SAVED) }; return defaultFetch(url) }); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText(/输入保存失败（测试）/)).toBeInTheDocument()); expect(screen.getByText(/task_id：task-new · run_id：run-new/)).toBeInTheDocument(); expect(createCalls()).toHaveLength(1); fireEvent.click(screen.getByRole('button', { name: '重试保存输入' })); await waitFor(() => expect(screen.getByText('任务工作台')).toBeInTheDocument()); expect(createCalls()).toHaveLength(1); expect(inputCalls().length).toBeGreaterThanOrEqual(2)
  })
  it('unmount during pending save produces no warning or navigation', async () => {
    let resolveSave!: (value: unknown) => void; fetchMock.mockImplementation((url) => String(url).endsWith('/inputs') ? new Promise((resolve) => { resolveSave = resolve }) : defaultFetch(url)); const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {}); const view = renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(inputCalls()).toHaveLength(1)); view.unmount(); await act(async () => resolveSave(json(SAVED))); expect(errorSpy).not.toHaveBeenCalled(); errorSpy.mockRestore()
  })
  it('unmount during pending create produces no warning, input save, or navigation', async () => {
    let resolveCreate!: (value: unknown) => void; fetchMock.mockImplementation((url) => String(url).endsWith('/tasks') ? new Promise((resolve) => { resolveCreate = resolve }) : defaultFetch(url)); const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {}); const view = renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(createCalls()).toHaveLength(1)); view.unmount(); await act(async () => resolveCreate(json(CREATED))); expect(inputCalls()).toHaveLength(0); expect(errorSpy).not.toHaveBeenCalled(); errorSpy.mockRestore()
  })
})

describe('CreateTaskPage deterministic boundaries', () => {
  it('keeps voice-asset disabled when the real capability response says it is unavailable', async () => {
    const unavailableOptions = {
      ...OPTIONS,
      voice_sources: [
        { id: 'voice-asset', label: '真实音色资产', available: false, reason: 'CAPABILITY_NOT_AVAILABLE' },
        { id: 'uploaded-reference', label: '上传参考音频', available: true },
      ],
    }
    fetchMock.mockImplementation((url) => {
      const value = String(url)
      if (value.endsWith('/tasks/create-options')) return json(unavailableOptions)
      if (value.includes('/assets/voices')) return json({ items: [], next_cursor: null, total: 0 })
      return defaultFetch(url)
    })

    renderPage()
    await ready()
    fireEvent.click(screen.getByRole('tab', { name: '声音生成' }))
    await waitFor(() => expect(screen.getByText(/CAPABILITY_NOT_AVAILABLE/)).toBeInTheDocument())
    expect(screen.getAllByRole('radio')[0]).toBeDisabled()
    expect(screen.getByText('真实音色列表为空。')).toBeInTheDocument()
  })
  it('keeps one audition player while switching voice selection', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('tab', { name: '声音生成' })); await waitFor(() => expect(document.querySelector('audio')).toBeInTheDocument()); fireEvent.click(screen.getByRole('button', { name: /真实女声/ })); expect(document.querySelectorAll('audio')).toHaveLength(1)
  })
  it('recovers URL task/input state without creating another task', async () => {
    const recoveryTask = { task: { task_id: 'task-old', title: '恢复任务', summary: '恢复摘要', engine: 'whiteboard', active_run_id: 'run-old' }, active_run: { task_id: 'task-old', run_id: 'run-old' }, stages: [], warnings: [], artifacts: [], trace: { trace_id: 'trace-old', command_ids: [] } }
    const recoveryInputs = { task_id: 'task-old', saved: true, inputs: { script: '恢复文案。', style: 'style-real', voice_source: 'voice-asset', voice_asset_id: 'voice-real', visual_source: 'preset', style_asset_id: 'style-real', target_chars: 20, shots_per_image: 3, line_density: 'minimal', brand_text: '恢复品牌', include_subtitles: false, pen_text: '', stroke_detail: '' }, reference_audio: { uploaded: true, filename: 'old.wav' }, rules: { target_chars: 20, min_chars: 1, max_chars: 500 }, script_preparation: null, visual_anchor_enabled: false, execution_plan: { mode: 'legacy' } }
    fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/task-old/inputs')) return json(recoveryInputs); if (value.endsWith('/tasks/task-old')) return json(recoveryTask); return defaultFetch(url) })
    const view = render(<MemoryRouter initialEntries={['/tasks/new?submission_id=sub-old&task_id=task-old&run_id=run-old']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /></Routes></MemoryRouter>); await waitFor(() => expect(screen.getByText(/已恢复 Task：task-old/)).toBeInTheDocument()); expect(screen.getByLabelText('任务名称')).toHaveValue('恢复任务'); expect(screen.getByLabelText('任务摘要')).toHaveValue('恢复摘要'); fireEvent.click(screen.getByRole('tab', { name: /视频文案/ })); await waitFor(() => expect(screen.getByLabelText('原始文案')).toHaveValue('恢复文案。')); fireEvent.click(screen.getByRole('tab', { name: /成片设置/ })); expect(screen.getByLabelText('每张图分镜数')).toHaveValue('3'); expect(screen.getByLabelText('线条绘制量')).toHaveValue('minimal'); expect(screen.getByLabelText('账号/笔身文字')).toHaveValue('恢复品牌'); expect(screen.getByRole('button', { name: '重试保存输入' })).toBeEnabled(); expect(createCalls()).toHaveLength(0); view.unmount()
  })

  it('restores the validated Task and all inputs after an actual remount', async () => {
    const recoveryTask = { task: { task_id: 'task-remount', title: '重挂载任务', summary: '重挂载摘要', engine: 'whiteboard', active_run_id: 'run-remount' }, active_run: { task_id: 'task-remount', run_id: 'run-remount' }, stages: [], warnings: [], artifacts: [], trace: null }
    const recoveryInputs = { task_id: 'task-remount', saved: true, inputs: { script: '重挂载文案。', style: 'style-real', voice_source: 'voice-asset', voice_asset_id: 'voice-real', visual_source: 'preset', style_asset_id: 'style-real', target_chars: 33, shots_per_image: 4, line_density: 'complete', brand_text: '重挂载品牌', include_subtitles: true, pen_text: '', stroke_detail: '' }, reference_audio: { uploaded: true }, rules: { target_chars: 33, min_chars: 1, max_chars: 500 }, script_preparation: null, visual_anchor_enabled: true, execution_plan: { mode: 'legacy' } }
    fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/task-remount/inputs')) return json(recoveryInputs); if (value.endsWith('/tasks/task-remount')) return json(recoveryTask); return defaultFetch(url) })
    const route = '/tasks/new?task_id=task-remount&run_id=run-remount'
    const renderRecovery = () => render(<MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /></Routes></MemoryRouter>)
    const first = renderRecovery(); await waitFor(() => expect(screen.getByLabelText('任务名称')).toHaveValue('重挂载任务')); first.unmount(); renderRecovery(); await waitFor(() => expect(screen.getByLabelText('任务摘要')).toHaveValue('重挂载摘要')); fireEvent.click(screen.getByRole('tab', { name: /视频文案/ })); expect(screen.getByLabelText('原始文案')).toHaveValue('重挂载文案。'); fireEvent.click(screen.getByRole('tab', { name: /成片设置/ })); expect(screen.getByLabelText('每张图分镜数')).toHaveValue('4'); expect(screen.getByLabelText('线条绘制量')).toHaveValue('complete'); expect(screen.getByRole('button', { name: '重试保存输入' })).toBeEnabled(); expect(createCalls()).toHaveLength(0)
  })

  it('navigates to the actual active workbench route after create and save', async () => {
    renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByTestId('active-workbench')).toBeInTheDocument()); expect(screen.getByTestId('active-workbench')).toHaveTextContent('任务工作台'); expect(inputCalls()).toHaveLength(1)
  })
  it('saves recovered inputs without creating a second Task', async () => {
    recoveryPage(); await waitFor(() => expect(screen.getByRole('button', { name: '重试保存输入' })).toBeEnabled()); fireEvent.click(screen.getByRole('button', { name: '重试保存输入' })); await waitFor(() => expect(inputSaveCalls()).toHaveLength(1)); await waitFor(() => expect(screen.getByTestId('active-workbench')).toBeInTheDocument()); expect(createCalls()).toHaveLength(0); expect(inputSaveCalls()).toHaveLength(1)
  })
  it('requires a new reference when recovery reports uploaded=false', async () => {
    const inputs = recoveryInputs(false); inputs.inputs.voice_source = 'uploaded-reference'; recoveryPage('task-recovered', 'run-recovered', inputs); await waitFor(() => expect(screen.getByRole('button', { name: '重试保存输入' })).toBeEnabled()); fireEvent.click(screen.getByRole('button', { name: '重试保存输入' })); fireEvent.click(screen.getByRole('tab', { name: '声音生成' })); expect(await screen.findByText('请选择参考音频')).toBeInTheDocument(); expect(inputSaveCalls()).toHaveLength(0)
  })
  it('allows omitted reference when recovery reports uploaded=true', async () => {
    const inputs = recoveryInputs(true); inputs.inputs.voice_source = 'uploaded-reference'; recoveryPage('task-recovered', 'run-recovered', inputs); await waitFor(() => expect(screen.getByRole('button', { name: '重试保存输入' })).toBeEnabled()); fireEvent.click(screen.getByRole('button', { name: '重试保存输入' })); await waitFor(() => expect(inputSaveCalls()).toHaveLength(1)); await waitFor(() => expect(screen.getByTestId('active-workbench')).toBeInTheDocument()); expect(inputSaveCalls()).toHaveLength(1)
  })
  it('fails closed for forged identity, Task 404, inputs 404, and recovery loading', async () => {
    fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/forged')) return json({ ...RECOVERY_TASK, task: { ...RECOVERY_TASK.task, task_id: 'server-task' } }); if (value.endsWith('/tasks/forged/inputs')) return json(recoveryInputs()); return defaultFetch(url) }); render(<MemoryRouter initialEntries={['/tasks/new?task_id=forged&run_id=run-recovered&tab=final']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /></Routes></MemoryRouter>); await waitFor(() => expect(screen.getByText(/身份不匹配/)).toBeInTheDocument()); expect(screen.getByRole('button', { name: '创建并保存 Task' })).toBeDisabled(); cleanup()
    fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/task-recovered')) return json(RECOVERY_TASK); if (value.endsWith('/tasks/task-recovered/inputs')) return json({ error: { code: 'INPUTS_NOT_FOUND', message: '输入不存在' } }, 404); return defaultFetch(url) }); renderRecoveryRoute(); await waitFor(() => expect(screen.getByText(/输入读取失败/)).toBeInTheDocument()); expect(screen.getByRole('button', { name: '创建并保存 Task' })).toBeDisabled(); cleanup()
    fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/task-recovered')) return json({ error: { code: 'TASK_NOT_FOUND', message: 'Task 不存在' } }, 404); if (value.endsWith('/tasks/task-recovered/inputs')) return json(recoveryInputs()); return defaultFetch(url) }); renderRecoveryRoute(); await waitFor(() => expect(screen.getByText(/Task 读取失败/)).toBeInTheDocument()); expect(screen.getByRole('button', { name: '创建并保存 Task' })).toBeDisabled(); cleanup()
    fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/task-recovered')) return json({ ...RECOVERY_TASK, task: { ...RECOVERY_TASK.task, active_run_id: 'other-run' } }); if (value.endsWith('/tasks/task-recovered/inputs')) return json(recoveryInputs()); return defaultFetch(url) }); renderRecoveryRoute(); await waitFor(() => expect(screen.getByText(/身份不匹配/)).toBeInTheDocument()); expect(screen.getByRole('button', { name: '创建并保存 Task' })).toBeDisabled(); cleanup()
    let resolveTask!: (value: unknown) => void; let resolveInputs!: (value: unknown) => void; fetchMock.mockImplementation((url) => { const value = String(url); if (value.endsWith('/tasks/task-recovered')) return new Promise((resolve) => { resolveTask = resolve }); if (value.endsWith('/tasks/task-recovered/inputs')) return new Promise((resolve) => { resolveInputs = resolve }); return defaultFetch(url) }); renderRecoveryRoute(); expect(screen.getByRole('button', { name: '创建并保存 Task' })).toBeDisabled(); await act(async () => { resolveTask(json(RECOVERY_TASK)); resolveInputs(json(recoveryInputs())) }); await waitFor(() => expect(screen.getByRole('button', { name: '重试保存输入' })).toBeEnabled())
  })
  it('keeps error output safe and does not leak structured details', async () => {
    fetchMock.mockImplementation((url) => String(url).endsWith('/tasks') ? json({ error: { code: 'CREATE_FAILED', message: '创建失败' }, details: '/srv/private', token: 'secret-token', request_body: '用户文案' }, 400) : defaultFetch(url)); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByText(/创建失败/)).toBeInTheDocument()); expect(document.body).not.toHaveTextContent('/srv/private'); expect(document.body).not.toHaveTextContent('secret-token'); expect(document.body).not.toHaveTextContent('用户文案')
  })
  it('enforces title and summary required boundaries before any create request', async () => {
    renderPage(); await ready(); next(); fireEvent.change(screen.getByLabelText('原始文案'), { target: { value: '这是一段满足最小长度的文案。' } }); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); expect(createCalls()).toHaveLength(0); fireEvent.click(screen.getByRole('tab', { name: '任务介绍' })); expect(screen.getByText('请输入任务名称')).toBeInTheDocument(); expect(screen.getByText('请输入任务摘要')).toBeInTheDocument()
  })
  it('accepts the documented target, shots, line, brand, and new reference boundaries', async () => {
    renderPage(); await ready(); fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '边界任务' } }); fireEvent.change(screen.getByLabelText('任务摘要'), { target: { value: '边界摘要' } }); next(); fireEvent.change(screen.getByLabelText('原始文案'), { target: { value: '这是十个字的完整文案。' } }); fireEvent.change(screen.getByLabelText('目标分段长度'), { target: { value: '5' } }); fireEvent.click(screen.getByRole('tab', { name: '声音生成' })); fireEvent.click(screen.getByLabelText('上传参考音频')); fireEvent.change(screen.getByLabelText('参考音频'), { target: { files: [new File(['wav'], 'reference.wav', { type: 'audio/wav' })] } }); fireEvent.click(screen.getByRole('tab', { name: '成片设置' })); fireEvent.change(screen.getByLabelText('每张图分镜数'), { target: { value: '4' } }); fireEvent.change(screen.getByLabelText('线条绘制量'), { target: { value: 'complete' } }); fireEvent.change(screen.getByLabelText('账号/笔身文字'), { target: { value: '一二三四五六七八九十' } }); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); await waitFor(() => expect(screen.getByTestId('active-workbench')).toBeInTheDocument()); const body = inputCalls().find((call) => call[1]?.method === 'POST')![1].body as FormData; expect(body.get('target_chars')).toBe('5'); expect(body.get('shots_per_image')).toBe('4'); expect(body.get('line_density')).toBe('complete'); expect(body.get('brand_text')).toBe('一二三四五六七八九十'); expect(body.get('reference')).toBeInstanceOf(File)
  })
  it('blocks submission when the real style asset boundary is empty', async () => {
    fetchMock.mockImplementation((url) => String(url).includes('/assets/styles') ? json({ items: [], next_cursor: null, total: 0 }) : defaultFetch(url)); renderPage(); await ready(); fillIntroAndScript(); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); expect(createCalls()).toHaveLength(0); fireEvent.click(screen.getByRole('tab', { name: '视觉设置' })); expect(screen.getByText('请选择真实风格资产')).toBeInTheDocument()
  })
  it('cancels through the real queue route and blocks field boundary violations', async () => {
    renderPage(); await ready(); fireEvent.click(screen.getByRole('link', { name: '取消' })); expect(screen.getByText('任务队列')).toBeInTheDocument(); cleanup(); renderPage(); await ready(); fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '边界任务' } }); fireEvent.change(screen.getByLabelText('任务摘要'), { target: { value: '边界摘要' } }); next(); fireEvent.change(screen.getByLabelText('原始文案'), { target: { value: '短' } }); fireEvent.change(screen.getByLabelText('目标分段长度'), { target: { value: '501' } }); goFinal(); fireEvent.click(screen.getByRole('button', { name: '创建并保存 Task' })); expect(createCalls()).toHaveLength(0); fireEvent.click(screen.getByRole('tab', { name: /视频文案/ })); expect(screen.getByText(/文案至少需要/)).toBeInTheDocument(); expect(screen.getByText(/目标分段长度需在/)).toBeInTheDocument()
  })
})
