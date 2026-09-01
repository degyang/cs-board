/**
 * CCF-CREATE-TASK-13 (§3Q) — CreateTaskPage behavior suite
 *
 * Strategy: stub global.fetch (NOT the client module). The component uses the
 * REAL createTask / uploadInputs from src/lib/api/client, so MountainApiError
 * identity, JSON multipart boundary handling, and the two-step request sequence
 * are all exercised at the real HTTP boundary — not just mock call counts.
 *
 * This file is gate-scanned for forbidden browser-storage / audio-read /
 * secondary-engine / gated-execution patterns; none are used here.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { CreateTaskPage } from '../src/pages/CreateTaskPage'

// ── fetch helpers (match web-v2/tests/http-contract.test.ts) ─────────────

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    headers: new Headers({ 'content-type': 'application/json' }),
  }
}

const CREATE_OK = {
  ok: true,
  command: 'task.create',
  task_id: 't/special', // contains '/' → verifies encodeURIComponent navigation
  run_id: 'r1',
  trace_id: 'tr-1',
  command_id: 'c-1',
  event_sequence: 1,
}
const SAVE_OK = { ok: true, task_id: 't/special', input_saved: true }

function defaultFetch(url: string) {
  const u = String(url)
  if (u.endsWith('/inputs')) return jsonResponse(SAVE_OK)
  if (u.endsWith('/tasks')) return jsonResponse(CREATE_OK)
  return jsonResponse({ detail: { code: 'NOT_FOUND', message: 'not found' } }, 404)
}

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  fetchMock.mockImplementation(defaultFetch)
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/tasks/new']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/tasks/new" element={<CreateTaskPage />} />
        <Route path="/tasks/:id" element={<div>task-detail</div>} />
        <Route path="/" element={<div>task-list</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

const SCRIPT = '这是一段不少于十字的量子计算科普文案内容。'

function fillValid() {
  fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '量子计算科普' } })
  fireEvent.change(screen.getByLabelText('文案'), { target: { value: SCRIPT } })
}

const createCalls = () => fetchMock.mock.calls.filter(c => String(c[0]).endsWith('/tasks'))
const uploadCalls = () => fetchMock.mock.calls.filter(c => String(c[0]).endsWith('/inputs'))

// ───────────────────────────────────────────────────────────────────────────
// Form rendering
// ───────────────────────────────────────────────────────────────────────────

describe('CreateTaskPage — form rendering', () => {
  it('renders all core input fields with whiteboard engine fixed (no infographic)', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: '新建任务' })).toBeInTheDocument()
    expect(screen.getByLabelText('任务名称')).toBeInTheDocument()
    expect(screen.getByLabelText('文案')).toBeInTheDocument()
    expect(screen.getByLabelText('最小')).toBeInTheDocument()
    expect(screen.getByLabelText('目标')).toBeInTheDocument()
    expect(screen.getByLabelText('最大')).toBeInTheDocument()
    expect(screen.getByLabelText('参考音频（可选）')).toBeInTheDocument()
    // engine is fixed to whiteboard (shown via the dedicated hint)
    expect(screen.getByText('引擎：白板动画（固定）')).toBeInTheDocument()
    // forbidden features MUST NOT appear
    expect(screen.queryByText(/动态信息图/)).toBeNull()
    expect(screen.queryByText(/manual|gated/i)).toBeNull()
  })

  it('cancel navigates to task list', () => {
    renderPage()
    fireEvent.click(screen.getByRole('link', { name: '取消' }))
    expect(screen.getByText('task-list')).toBeInTheDocument()
  })
})

// ───────────────────────────────────────────────────────────────────────────
// Validation (no request sent on invalid input)
// ───────────────────────────────────────────────────────────────────────────

describe('CreateTaskPage — validation blocks the request', () => {
  it('empty title → field error, no request', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('文案'), { target: { value: SCRIPT } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('请输入任务名称')).toBeInTheDocument())
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('empty script → field error, no request', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('请输入文案')).toBeInTheDocument())
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('non-integer char field → field error, no request', async () => {
    renderPage()
    fillValid()
    fireEvent.change(screen.getByLabelText('目标'), { target: { value: '1.5' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('字数必须为整数')).toBeInTheDocument())
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('char out of bounds (max>500) → field error, no request', async () => {
    renderPage()
    fillValid()
    fireEvent.change(screen.getByLabelText('最大'), { target: { value: '9999' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText(/字数范围超出合理界限/)).toBeInTheDocument())
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('inverted rule (min>target) → field error, no request', async () => {
    renderPage()
    fillValid()
    fireEvent.change(screen.getByLabelText('最小'), { target: { value: '100' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText(/需满足 1 ≤ 最小 ≤ 目标 ≤ 最大 ≤ 500/)).toBeInTheDocument())
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

// ───────────────────────────────────────────────────────────────────────────
// Two-step save: create (JSON) then upload (FormData) at the real HTTP boundary
// ───────────────────────────────────────────────────────────────────────────

describe('CreateTaskPage — two-step save (create → upload)', () => {
  it('POST /tasks JSON then POST /inputs FormData, navigates to encoded task id', async () => {
    renderPage()
    fillValid()
    const file = new File(['audio-bytes'], 'ref.wav', { type: 'audio/wav' })
    fireEvent.change(screen.getByLabelText('参考音频（可选）'), { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('task-detail')).toBeInTheDocument())

    // exactly two HTTP calls
    expect(fetchMock).toHaveBeenCalledTimes(2)

    // 1) create: POST /tasks, JSON body, Content-Type application/json
    const [createUrl, createOpts] = fetchMock.mock.calls[0]
    expect(String(createUrl)).toContain('/api/v1/tasks')
    expect(String(createUrl)).not.toContain('/inputs')
    expect(createOpts.method).toBe('POST')
    expect(createOpts.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(createOpts.body)).toEqual({
      title: '量子计算科普',
      engine: 'whiteboard',
      pipeline_id: 'mountain-av-v1',
    })

    // 2) upload: POST /tasks/{encodedId}/inputs, FormData body, NO manual Content-Type
    const [uploadUrl, uploadOpts] = fetchMock.mock.calls[1]
    expect(String(uploadUrl)).toContain('/api/v1/tasks/t%2Fspecial/inputs')
    expect(uploadOpts.method).toBe('POST')
    expect(uploadOpts.body).toBeInstanceOf(FormData)
    // browser must set multipart Content-Type itself — client must not set it
    expect(uploadOpts.headers).toBeUndefined()

    const form = uploadOpts.body as FormData
    expect(form.get('script')).toBe(SCRIPT)
    expect(form.get('target_chars')).toBe('80')
    expect(form.get('min_chars')).toBe('35')
    expect(form.get('max_chars')).toBe('140')
    expect(form.get('visual_anchor_enabled')).toBe('true')
    expect(form.get('include_subtitles')).toBe('true')
    expect(form.get('style')).toBe('极简粗线简笔白板风')
    expect(form.get('stroke_detail')).toBe('detailed')
    expect(form.get('pen_text')).toBe('')
    expect(form.get('reference')).toBe(file)
  })

  it('without reference audio: FormData has no reference key', async () => {
    renderPage()
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('task-detail')).toBeInTheDocument())
    const form = fetchMock.mock.calls[1][1].body as FormData
    expect(form.get('reference')).toBeNull()
    expect(form.get('script')).toBe(SCRIPT)
  })

  it('create failure → no upload, safe error shown, no navigation', async () => {
    fetchMock.mockImplementation(url =>
      String(url).endsWith('/tasks')
        ? jsonResponse({ detail: { code: 'VALIDATION', message: '任务名称不能为空' } }, 400)
        : jsonResponse(SAVE_OK),
    )
    renderPage()
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('任务名称不能为空')).toBeInTheDocument())
    expect(screen.getByText('代码：VALIDATION')).toBeInTheDocument()
    // no upload attempted
    expect(uploadCalls()).toHaveLength(0)
    expect(createCalls()).toHaveLength(1)
    expect(screen.queryByText('task-detail')).toBeNull()
    // form still editable (title input not disabled) — createdTask is null
    expect(screen.getByLabelText('任务名称')).not.toBeDisabled()
  })
})

// ───────────────────────────────────────────────────────────────────────────
// Partial failure: keep task_id/run_id, retry only re-uploads, enter workbench
// ───────────────────────────────────────────────────────────────────────────

describe('CreateTaskPage — partial failure & retry', () => {
  function uploadFailsFirst() {
    fetchMock.mockImplementation(url => {
      if (String(url).endsWith('/inputs')) {
        return jsonResponse({ detail: { code: 'UPLOAD_FAILED', message: '保存输入失败' } }, 400)
      }
      return jsonResponse(CREATE_OK)
    })
  }

  it('create ok + upload fail → keeps task, no navigation, no re-create, shows retry + workbench', async () => {
    uploadFailsFirst()
    renderPage()
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('任务已创建、输入保存失败')).toBeInTheDocument())
    // safe message + code from MountainApiError
    expect(screen.getByText('保存输入失败')).toBeInTheDocument()
    expect(screen.getByText('代码：UPLOAD_FAILED')).toBeInTheDocument()
    // Task was created exactly once (no duplicate create)
    expect(createCalls()).toHaveLength(1)
    // upload was attempted once
    expect(uploadCalls()).toHaveLength(1)
    // no navigation to workbench
    expect(screen.queryByText('task-detail')).toBeNull()
    // retry + enter-workbench actions present
    expect(screen.getByRole('button', { name: '重试保存输入' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '进入任务工作台' })).toBeInTheDocument()
    // the original "创建任务" submit button is gone (cannot re-create)
    expect(screen.queryByRole('button', { name: '创建任务' })).toBeNull()
  })

  it('retry → re-calls only upload (not create), success → navigate to encoded id', async () => {
    let inputsCount = 0
    fetchMock.mockImplementation(url => {
      if (String(url).endsWith('/inputs')) {
        inputsCount++
        return inputsCount === 1
          ? jsonResponse({ detail: { code: 'UPLOAD_FAILED', message: '保存输入失败' } }, 400)
          : jsonResponse(SAVE_OK) // retry succeeds
      }
      return jsonResponse(CREATE_OK)
    })
    renderPage()
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('任务已创建、输入保存失败')).toBeInTheDocument())
    // initial state: 1 create + 1 upload
    expect(createCalls()).toHaveLength(1)
    expect(uploadCalls()).toHaveLength(1)

    // act: retry
    fireEvent.click(screen.getByRole('button', { name: '重试保存输入' }))

    await waitFor(() => expect(screen.getByText('task-detail')).toBeInTheDocument())
    // create NOT re-called; upload called a 2nd time
    expect(createCalls()).toHaveLength(1)
    expect(uploadCalls()).toHaveLength(2)
  })

  it('enter workbench from partial failure → navigate to encoded task id', async () => {
    uploadFailsFirst()
    renderPage()
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('任务已创建、输入保存失败')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '进入任务工作台' }))

    await waitFor(() => expect(screen.getByText('task-detail')).toBeInTheDocument())
    // no extra create or upload from entering workbench
    expect(createCalls()).toHaveLength(1)
    expect(uploadCalls()).toHaveLength(1)
  })
})

// ───────────────────────────────────────────────────────────────────────────
// Concurrency & unmount safety
// ───────────────────────────────────────────────────────────────────────────

describe('CreateTaskPage — concurrency & unmount safety', () => {
  it('shows loading state (创建中…)', async () => {
    fetchMock.mockImplementation(url =>
      String(url).endsWith('/tasks') ? new Promise(() => {}) : jsonResponse(SAVE_OK),
    )
    renderPage()
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByRole('button', { name: '创建中…' })).toBeDisabled())
    // create was called once, upload not yet
    expect(createCalls()).toHaveLength(1)
    expect(uploadCalls()).toHaveLength(0)
  })

  it('double submit → single create (no duplicate Task)', async () => {
    fetchMock.mockImplementation(url =>
      String(url).endsWith('/tasks') ? new Promise(() => {}) : jsonResponse(SAVE_OK),
    )
    const { container } = renderPage()
    fillValid()
    const formEl = container.querySelector('form')!
    fireEvent.submit(formEl)
    fireEvent.submit(formEl) // 2nd synchronous submit

    await waitFor(() => expect(screen.getByRole('button', { name: '创建中…' })).toBeInTheDocument())
    expect(createCalls()).toHaveLength(1)
  })

  it('unmount during upload → no state update, no navigation, 0 warnings', async () => {
    let uploadResolve!: (v: ReturnType<typeof jsonResponse>) => void
    fetchMock.mockImplementation(url => {
      if (String(url).endsWith('/inputs')) {
        return new Promise(r => { uploadResolve = r })
      }
      return jsonResponse(CREATE_OK)
    })
    // call-through spy: must NOT suppress — proves no warning is emitted
    const spy = vi.spyOn(console, 'error')

    const { unmount } = renderPage()
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    // wait until create resolved + upload fetch is in flight
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    // task was created → component now awaiting upload
    unmount()

    // resolve the pending upload AFTER unmount; component must not setState/navigate
    await act(async () => {
      uploadResolve(jsonResponse(SAVE_OK))
    })

    const warnings = spy.mock.calls
      .map(args => String(args[0]))
      .filter(s => /unmounted|can't perform a react state update|not wrapped in act/i.test(s))
    expect(warnings).toHaveLength(0)
    spy.mockRestore()
  })
})

// ───────────────────────────────────────────────────────────────────────────
// Error security: only safe message/code rendered; never path/token/secret/traceback/reference
// ───────────────────────────────────────────────────────────────────────────

describe('CreateTaskPage — error security', () => {
  it('renders only safe message/code; never sensitive detail fields', async () => {
    fetchMock.mockImplementation(url => {
      if (String(url).endsWith('/inputs')) {
        return jsonResponse(
          {
            detail: {
              code: 'SENSITIVE',
              message: '安全错误信息',
              details: {
                path: '/etc/secret/key',
                command: 'rm -rf /',
                token: 'sk-live-secret-token',
                secret: 'topsecret-value',
                traceback: 'Traceback (most recent call last)',
                reference: 'audio-bytes-content',
              },
            },
          },
          400,
        )
      }
      return jsonResponse(CREATE_OK)
    })
    renderPage()
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => expect(screen.getByText('任务已创建、输入保存失败')).toBeInTheDocument())
    // safe fields ARE shown
    expect(screen.getByText('安全错误信息')).toBeInTheDocument()
    expect(screen.getByText('代码：SENSITIVE')).toBeInTheDocument()
    // sensitive detail fields are NEVER rendered
    expect(screen.queryByText('/etc/secret/key')).toBeNull()
    expect(screen.queryByText('rm -rf /')).toBeNull()
    expect(screen.queryByText('sk-live-secret-token')).toBeNull()
    expect(screen.queryByText('topsecret-value')).toBeNull()
    expect(screen.queryByText('Traceback (most recent call last)')).toBeNull()
    expect(screen.queryByText('audio-bytes-content')).toBeNull()
  })
})
