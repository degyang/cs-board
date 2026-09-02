import { describe, expect, it, vi } from 'vitest'
import { waitForAssetTerminal } from '../scripts/capture-parity-evidence-helpers.mjs'

function fakePage({ loading = true, cards = 0, empty = false, error = false, reject = false } = {}) {
  const waitFor = vi.fn(async ({ state }: { state: string }) => {
    if (reject) throw new Error('Timeout 10ms exceeded')
    if (state === 'hidden' && loading) return
  })
  const text = (value: string) => ({ waitFor, isVisible: vi.fn(async () => value.includes('暂无') ? empty : value.includes('失败') ? error : false) })
  return { page: { getByText: vi.fn(text), locator: vi.fn(() => ({ count: vi.fn(async () => cards) })) }, waitFor }
}

describe('create-task asset evidence terminal guard', () => {
  it('does not proceed while loading text is visible and waits for hidden', async () => {
    const { page, waitFor } = fakePage({ loading: true, cards: 1 })
    await expect(waitForAssetTerminal(page, 'voice', 100)).resolves.toMatchObject({ state: 'success' })
    expect(waitFor).toHaveBeenCalledWith({ state: 'hidden', timeout: 100 })
  })
  it.each([
    ['voice', { cards: 1 }, 'success'], ['voice', { empty: true }, 'empty'], ['voice', { error: true }, 'error'],
    ['visual', { cards: 1 }, 'success'], ['visual', { empty: true }, 'empty'], ['visual', { error: true }, 'error'],
  ] as const)('allows %s only after a real %s terminal state', async (asset, state, expected) => {
    await expect(waitForAssetTerminal(fakePage(state).page, asset, 100)).resolves.toMatchObject({ state: expected })
  })
  it('fails non-zero-equivalent on terminal wait timeout', async () => {
    await expect(waitForAssetTerminal(fakePage({ reject: true }).page, 'visual', 10)).rejects.toThrow('Timeout')
  })
  it('fails when loading ended without card, empty, or error terminal', async () => {
    await expect(waitForAssetTerminal(fakePage({ loading: false }).page, 'voice', 100)).rejects.toThrow('no terminal state')
  })
})
