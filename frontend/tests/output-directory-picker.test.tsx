import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { CreateTaskPage } from '../src/pages/CreateTaskPage'

const fetchMock = vi.fn()
const response = (body: unknown, status = 200) => ({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body), headers: new Headers({ 'content-type': 'application/json' }) })
const options = { engines: [{ id: 'whiteboard', label: '白板动画', available: true }], visual_sources: [{ id: 'preset', label: '预设风格', available: true }], voice_sources: [{ id: 'uploaded-reference', label: '上传参考音频', available: true }], limits: { script_min_chars: 10, target_chars_min: 5, target_chars_max: 500, brand_text_max_chars: 12 }, defaults: { engine: 'whiteboard', visual_source: 'preset', target_chars: 45, shots_per_image: 2, line_density: 'rich', visual_anchor_enabled: true, include_subtitles: true } }

function renderPage() {
  return render(<MemoryRouter initialEntries={['/tasks/new']}><Routes><Route path="/tasks/new" element={<CreateTaskPage />} /></Routes></MemoryRouter>)
}
function goFinal() { fireEvent.click(screen.getByRole('tab', { name: '成片设置' })) }

beforeEach(() => {
  fetchMock.mockReset()
  fetchMock.mockImplementation((url) => {
    const value = String(url)
    if (value.endsWith('/tasks/create-options')) return response(options)
    if (value.includes('/assets/voices')) return response({ items: [], next_cursor: null, total: 0 })
    if (value.includes('/assets/styles')) return response({ items: [], next_cursor: null, total: 0 })
    if (value.endsWith('/directories')) return response({ path: '.', directories: [{ name: 'assets', path: 'assets' }] })
    if (value.endsWith('/directories?path=assets')) return response({ path: 'assets', directories: [{ name: 'nested', path: 'assets/nested' }] })
    if (value.endsWith('/directories?path=assets/nested')) return response({ path: 'assets/nested', directories: [] })
    return response({ error: { code: 'NOT_FOUND', message: '未找到' } }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => { vi.unstubAllGlobals() })

describe('output directory picker', () => {
  it('does not render the dialog until opened', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByRole('tab', { name: '成片设置' })).toBeInTheDocument())
    goFinal()
    expect(screen.queryByRole('dialog', { name: '输出目录选择器' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '选择目录' }))
    expect(await screen.findByRole('dialog', { name: '输出目录选择器' })).toBeInTheDocument()
  })

  it('enters and returns, then confirms the current directory into the input', async () => {
    renderPage(); await waitFor(() => expect(screen.getByRole('tab', { name: '成片设置' })).toBeInTheDocument()); goFinal()
    fireEvent.click(screen.getByRole('button', { name: '选择目录' })); await screen.findByRole('dialog', { name: '输出目录选择器' })
    fireEvent.click(screen.getByRole('button', { name: /assets.*进入/ })); await waitFor(() => expect(screen.getByText('assets')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '返回上级' })); await waitFor(() => expect(screen.getByText('.')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /assets.*进入/ })); await waitFor(() => expect(screen.getByText('assets')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '选择当前目录' })); fireEvent.click(screen.getByRole('button', { name: '确认' }))
    expect(screen.getByLabelText('输出目录')).toHaveValue('assets')
  })

  it('cancels without changing manual input and surfaces API errors', async () => {
    renderPage(); await waitFor(() => expect(screen.getByRole('tab', { name: '成片设置' })).toBeInTheDocument()); goFinal()
    fireEvent.change(screen.getByLabelText('输出目录'), { target: { value: 'manual/path' } }); fireEvent.click(screen.getByRole('button', { name: '选择目录' })); await screen.findByRole('dialog', { name: '输出目录选择器' }); fireEvent.click(screen.getByRole('button', { name: '取消' }))
    expect(screen.getByLabelText('输出目录')).toHaveValue('manual/path')
    fetchMock.mockImplementation((url) => String(url).endsWith('/directories') ? response({ error: { code: 'DIRECTORY_FAILED', message: '目录读取失败（测试）' } }, 502) : response(options))
    fireEvent.click(screen.getByRole('button', { name: '选择目录' })); await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('DIRECTORY_FAILED：目录读取失败（测试）'))
  })
})
