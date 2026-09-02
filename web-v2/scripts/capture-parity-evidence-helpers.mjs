/** Wait for a create-task asset request to reach a visible terminal state. */
export async function waitForAssetTerminal(page, asset, timeout = 8_000) {
  const config = asset === 'voice'
    ? {
        loading: '正在加载音色…',
        empty: '暂无可用音色',
        error: '音色加载失败，请稍后重试',
        cards: '.asset-state .choice-card',
      }
    : {
        loading: '正在加载风格…',
        empty: '暂无可用风格，将使用标准白板风格',
        error: '风格加载失败，暂不可选择资产',
        cards: '.choice-grid .choice-card:not(.disabled)',
      }
  const loading = page.getByText(config.loading, { exact: true })
  await loading.waitFor({ state: 'hidden', timeout })
  const cards = page.locator(config.cards)
  const empty = page.getByText(config.empty, { exact: true })
  const error = page.getByText(config.error, { exact: true })
  const [cardCount, emptyVisible, errorVisible] = await Promise.all([
    cards.count(),
    empty.isVisible().catch(() => false),
    error.isVisible().catch(() => false),
  ])
  if (cardCount === 0 && !emptyVisible && !errorVisible) {
    throw new Error(`Evidence assertion failed: ${asset} asset request reached no terminal state`)
  }
  return { state: cardCount > 0 ? 'success' : emptyVisible ? 'empty' : 'error', cardCount }
}
