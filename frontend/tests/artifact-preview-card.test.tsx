import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ArtifactPreviewCard } from '../src/components/tasks/ArtifactPreviewCard'

const RECORD = {
  asset_id: 'asset-image-001',
  revision: 3,
  positive_prompt: '一只山间小鹿',
  steps: 28,
  editable_fields: ['positive_prompt', 'steps'],
  output_relative_path: 'outputs/task-001/runs/run-001/assets/asset-image-001/current.png',
  provider_id: 'image-service',
  api_key: 'must-not-render',
  authorization: 'Bearer must-not-render',
  scratch_path: '/tmp/outside-project/current.png',
  input_asset_refs: ['outputs/task-001/input.png', '/tmp/outside-project/input.png'],
}

function renderCard(kind: 'image' | 'audio' | 'video') {
  return render(<ArtifactPreviewCard assetId={`asset-${kind}`} label={`${kind} 资产`} kind={kind} mediaUrl={`/media/${kind}`} generationRecord={RECORD} />)
}

describe('ArtifactPreviewCard provenance interaction skeleton', () => {
  it.each(['image', 'audio', 'video'] as const)('opens the %s preview from the asset body', async (kind) => {
    renderCard(kind)
    const name = kind === 'image' ? '查看图片预览' : kind === 'audio' ? '试听音频' : '播放视频'
    await userEvent.click(screen.getByRole('button', { name: `${name}：${kind} 资产` }))
    const dialog = screen.getByRole('dialog', { name: `${kind} 资产 预览` })
    expect(dialog.querySelector(kind === 'image' ? 'img' : kind)).not.toBeNull()
    expect(within(dialog).getByRole('button', { name: '关闭预览' })).toBeInTheDocument()
  })

  it('keeps the configuration entry reachable by mouse, keyboard focus, and touch click', async () => {
    renderCard('image')
    const trigger = screen.getByRole('button', { name: '查看 image 资产 生成配置' })
    fireEvent.mouseEnter(trigger.closest('.artifact-preview-card')!)
    await userEvent.click(trigger)
    expect(screen.getByRole('dialog', { name: 'image 资产 生成配置' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '关闭' }))
    trigger.focus()
    await userEvent.keyboard('{Enter}')
    expect(screen.getByRole('dialog', { name: 'image 资产 生成配置' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '关闭' }))
    fireEvent.pointerDown(trigger, { pointerType: 'touch' })
    await userEvent.click(trigger)
    expect(screen.getByRole('dialog', { name: 'image 资产 生成配置' })).toBeInTheDocument()
  })

  it('shows passed record fields, permits only declared draft fields, hides sensitive data, and leaves regeneration unwired', async () => {
    renderCard('image')
    await userEvent.click(screen.getByRole('button', { name: '查看 image 资产 生成配置' }))
    const drawer = screen.getByRole('dialog', { name: 'image 资产 生成配置' })
    expect(within(drawer).getByLabelText('positive_prompt')).toHaveValue('一只山间小鹿')
    expect(within(drawer).getByLabelText('steps')).toHaveValue('28')
    await userEvent.clear(within(drawer).getByLabelText('positive_prompt'))
    await userEvent.type(within(drawer).getByLabelText('positive_prompt'), '新的实际草稿')
    expect(within(drawer).getByLabelText('positive_prompt')).toHaveValue('新的实际草稿')
    const json = within(drawer).getByLabelText('实际生成记录').textContent
    expect(json).toContain('output_relative_path')
    expect(json).not.toContain('must-not-render')
    expect(json).not.toContain('/tmp/outside-project')
    expect(json).toContain('outputs/task-001/input.png')
    expect(within(drawer).getByRole('button', { name: '再次生成' })).toBeDisabled()
    expect(within(drawer).getByText(/等待后端再生成契约/)).toBeInTheDocument()
  })
})
