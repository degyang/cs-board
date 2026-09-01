/* ---------- 文案分割规则（与 TTS 分段一致） ----------
 * 规则：① 换行 = 自然段硬边界（一段绝不跨自然段）；
 *         ② 段内去掉"汉字-汉字 / 汉字-英文 / 英文-汉字"之间的无意义空格（保留英文-英文正常空格）；
 *         ③ 段内仍按"分割字数"贪心装完整句（句末标点为界），超过字数则划分为下一段，超长单句硬切。
 * 不添加"分段N"之类标签，输出即干净段落，直接送 TTS 转化。
 */
const isCJK = (c: string | undefined): boolean =>
  c != null && /[　-〿㐀-鿿豈-﫿＀-￯]/.test(c)

// 去掉相邻汉字 / 汉字-英文之间的空格，保留英文-英文正常空格
function cleanSpaces(s: string): string {
  let out = ''
  for (let i = 0; i < s.length; i++) {
    const c = s[i]
    if (c === ' ' || c === ' ') {
      if (isCJK(s[i - 1]) || isCJK(s[i + 1])) continue
    }
    out += c
  }
  return out
}

// 单块无换行的兜底：按 cap 贪心装完整句（句末标点为界），超长单句硬切
function packByCap(block: string, cap: number): string[] {
  const SENT = /[。？！!?]/
  const sentences: string[] = []
  let cur = ''
  for (const ch of block) {
    cur += ch
    if (SENT.test(ch)) {
      sentences.push(cur)
      cur = ''
    }
  }
  if (cur.trim()) sentences.push(cur)
  const segs: string[] = []
  let buf = ''
  const flush = () => {
    const t = buf.trim()
    if (t) segs.push(t)
    buf = ''
  }
  for (const sent of sentences) {
    if (sent.length > cap) {
      flush()
      for (let i = 0; i < sent.length; i += cap) {
        const piece = sent.slice(i, i + cap).trim()
        if (piece) segs.push(piece)
      }
      continue
    }
    if (buf.length + sent.length > cap) flush()
    buf += sent
  }
  flush()
  return segs
}

export function splitBySentences(raw: string, cap: number): { text: string; segments: number; chars: number } {
  const paragraphs = (raw ?? '').split(/\n+/) // 换行 = 自然段硬边界（不跨段）
  const segs: string[] = []
  let totalChars = 0
  for (const para of paragraphs) {
    const cleaned = cleanSpaces(para)
    const block = cleaned.trim()
    if (!block) continue
    totalChars += cleaned.length
    // 段内仍按"分割字数"贪心装完整句（句末标点为界），超长单句硬切
    segs.push(...packByCap(block, cap))
  }
  const text = segs.join('\n\n') // 不贴"分段N"标签，干净段落直接送 TTS
  return { text, segments: segs.length, chars: totalChars }
}

