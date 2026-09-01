import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppShell } from '../src/components/layout/AppShell'

const ROUTER_FUTURE = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
}

vi.mock('../src/lib/api/tasks', () => ({ fetchTasks: vi.fn().mockResolvedValue([]) }))

describe('AppShell sidebar default', () => {
  beforeEach(() => localStorage.clear())

  it('uses the full pinned sidebar when no preference has been stored', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/']} future={ROUTER_FUTURE}>
        <Routes><Route element={<AppShell />}><Route index element={<div>内容</div>} /></Route></Routes>
      </MemoryRouter>,
    )

    expect(container.querySelector('.app-shell')).toHaveClass('is-pinned')
    for (const label of ['山野小读', '任务队列', '新建任务', '资产管理', '设置', '帮助']) {
      expect(screen.getByText(label)).toBeVisible()
    }
  })
})
