import { useEffect, useRef, useState } from 'react'

/* ==========================================================================
   设置-模型 · 模型服务商列表
   每个条目 = 一个模型服务（provider）：名称 / 类别（文本·图片·视频·语音，多选）/
   模型清单（逗号分隔输入，解析为数组）/ API Key / Base URL。
   localStorage 持久化（mountain.models.v1），支持 增/改/删。
   ========================================================================== */

export interface ModelProvider {
  id: string
  name: string
  categories: string[] // 'text' | 'image' | 'video' | 'speech'（可多选）
  models: string[] // 模型清单（由逗号分隔输入解析）
  apiKey: string // 原型阶段存本机 localStorage；正式版应落系统密钥库
  baseUrl: string
}

export const MODEL_CATEGORIES = [
  { key: 'text', label: '文本' },
  { key: 'image', label: '图片' },
  { key: 'video', label: '视频' },
  { key: 'speech', label: '语音' },
] as const

export function categoryLabel(key: string): string {
  return MODEL_CATEGORIES.find((c) => c.key === key)?.label ?? key
}

const KEY = 'mountain.models.v1'

const SEED_PROVIDERS: ModelProvider[] = [
  {
    id: 'mp-openai',
    name: 'OpenAI 官方',
    categories: ['text'],
    models: ['gpt-4o', 'gpt-4o-mini'],
    apiKey: 'sk-proj-demo-1234567890abcdef',
    baseUrl: 'https://api.openai.com/v1',
  },
  {
    id: 'mp-dashscope',
    name: '阿里云百炼',
    categories: ['text', 'image', 'speech'],
    models: ['qwen-max', 'qwen-plus', 'wanx-v1', 'cosyvoice-v2'],
    apiKey: 'sk-bailian-a1b2c3d4e5f6g7h8',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  },
  {
    id: 'mp-indextts',
    name: '本地 IndexTTS',
    categories: ['speech'],
    models: ['indextts-2'],
    apiKey: '',
    baseUrl: 'http://127.0.0.1:7860',
  },
]

function load(): ModelProvider[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const p = JSON.parse(raw)
      if (Array.isArray(p)) return p as ModelProvider[]
    }
  } catch {
    /* 解析失败回退种子 */
  }
  return SEED_PROVIDERS
}

let _seq = 0
function uid(prefix: string): string {
  _seq += 1
  return `${prefix}-${Date.now().toString(36)}-${_seq}`
}

export function useModelProviders() {
  const init = useRef(load())
  const [providers, setProviders] = useState<ModelProvider[]>(init.current)

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(providers))
    } catch {
      /* 容量超限忽略 */
    }
  }, [providers])

  return {
    providers,
    addProvider: (p: ModelProvider) => setProviders((s) => [...s, p]),
    updateProvider: (p: ModelProvider) => setProviders((s) => s.map((x) => (x.id === p.id ? p : x))),
    removeProvider: (id: string) => setProviders((s) => s.filter((x) => x.id !== id)),
    uid,
  }
}

/** API Key 掩码：保留前 3 后 4，中间打点；过短则全打点 */
export function maskApiKey(v: string): string {
  if (!v) return ''
  if (v.length <= 8) return '•'.repeat(v.length)
  return v.slice(0, 3) + '••••••' + v.slice(-4)
}

