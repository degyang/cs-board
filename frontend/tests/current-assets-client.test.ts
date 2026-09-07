import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchCurrentAssets } from '../src/lib/api/client'

describe('fetchCurrentAssets', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('uses the accepted task/run asset discovery URL with encoded stable identities', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [] }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await fetchCurrentAssets('task / one', 'run?two')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/tasks/task%20%2F%20one/runs/run%3Ftwo/assets',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) }),
    )
  })
})
