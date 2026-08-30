import { useEffect, useRef, useState } from 'react'
import { settingsSections } from '../../lib/api/mock'
import { submitCommand } from '../../lib/api/client'

/* ==========================================================================
   设置 · 可编辑配置存储
   把原先「只读展示」的 SettingsSectionView 升级为可编辑字段模型：
   - 字段类型：text / select / toggle / secret / info（只读信息）
   - 全部可编辑项支持 修改 -> 暂存(dirty) -> 保存(submitCommand) / 重置
   - 改动持久化到 localStorage（mountain.settings.v1）；Secret 不落盘，仅存「是否已配置」
   - 日志级别作为诊断类设置一并纳入保存
   ========================================================================== */

export type FieldType = 'text' | 'select' | 'toggle' | 'secret' | 'info'

/** 字段校验规则：专业配置页的核心——保存前拦截非法值 */
export interface ValidationRule {
  required?: boolean // 必填（空值即报错）
  pattern?: RegExp // 命中才通过
  message?: string // 自定义错误文案；缺省按规则自动生成
  hint?: string // 输入框下方的格式提示（非错误，常驻）
}

export interface SettingItem {
  key: string
  label: string
  type: FieldType
  value: string
  options?: string[]
  note?: string
  secret_ref?: string
  rule?: ValidationRule
  /* secret 专用 */
  configured?: boolean
  secretValue?: string // 用户输入的原始密钥，仅在提交时透传，不持久化
}

export interface SettingSection {
  key: string
  title: string
  items: SettingItem[]
}

interface FieldSeed {
  key: string
  label: string
  type: FieldType
  options?: string[]
  note?: string
  secret_ref?: string
  rule?: ValidationRule
}

/** 单字段校验：返回错误文案，空串代表通过 */
export function validateField(item: SettingItem): string {
  const r = item.rule
  if (!r) return ''
  // secret：未配置且非必填 → 通过；输入了值才校验格式
  if (item.type === 'secret') {
    const v = item.secretValue ?? ''
    if (!v) return r.required && !item.configured ? r.message ?? '此项为必填' : ''
    if (r.pattern && !r.pattern.test(v)) return r.message ?? '格式不正确'
    return ''
  }
  const v = item.value ?? ''
  if (r.required && v.trim() === '') return r.message ?? '此项为必填'
  if (r.pattern && v.trim() !== '' && !r.pattern.test(v)) return r.message ?? '格式不正确'
  return ''
}

/** 全量校验：返回 key 为 `${secKey}.${itemKey}` 的错误表 */
export function validateSections(sections: SettingSection[]): Record<string, string> {
  const errs: Record<string, string> = {}
  for (const s of sections) {
    for (const it of s.items) {
      const e = validateField(it)
      if (e) errs[`${s.key}.${it.key}`] = e
    }
  }
  return errs
}

interface SectionSeed {
  key: string
  title: string
  items: FieldSeed[]
}

/* 权威字段定义（类型与可选项在此控制，mock 仅提供初始值） */
const SEED: SectionSeed[] = [
  {
    key: 'models',
    title: '模型',
    items: [
      { key: 'text_profile', label: '文本模型 profile', type: 'select', options: ['profile-a（OpenAI 兼容）', 'profile-b（Azure OpenAI）', 'profile-c（本地 vLLM）'] },
      { key: 'image_profile', label: '图片模型 profile', type: 'select', options: ['profile-img-1（本地 SDXL）', 'profile-img-2（云端 Flux）'] },
      { key: 'api_key', label: '文本模型 API Key', type: 'secret', secret_ref: 'keyring://mountain/text-model', rule: { pattern: /^\S{16,}$/, message: '密钥长度至少 16 位且不能包含空格' } },
    ],
  },
  {
    key: 'speech',
    title: '语音与对齐',
    items: [
      { key: 'tts_node', label: '语音节点', type: 'select', options: ['tts-node-01', 'tts-node-02', 'tts-node-03'] },
      { key: 'whisper', label: 'Whisper 能力', type: 'info', note: 'whisper-large-v3（本地），用于 Voice 时长对齐，置信度阈值 0.62' },
      { key: 'fallback_policy', label: 'fallback 策略', type: 'select', options: ['低置信度自动平均切图，前端可见但不计为失败', '严格模式（低于阈值即记为失败）', '人工复核模式'] },
      { key: 'auto_retry', label: 'TTS 失败自动重试', type: 'toggle', note: '连续失败超过阈值后转人工，不阻断整条流水线' },
    ],
  },
  {
    key: 'toolchain',
    title: '工具链',
    items: [
      { key: 'renderer', label: '渲染环境', type: 'info' },
      { key: 'ffmpeg', label: 'FFmpeg', type: 'info' },
      { key: 'python', label: 'Python 工具链', type: 'info' },
    ],
  },
  {
    key: 'storage',
    title: '存储',
    items: [
      { key: 'workspace', label: '工作区（逻辑 key）', type: 'text', note: '逻辑 key 映射，UI 不显示物理路径', rule: { required: true, pattern: /^[a-z0-9][a-z0-9_-]{1,63}$/, message: '须以字母/数字开头，仅含小写字母/数字/连字符/下划线，长度 2-64' } },
      { key: 'retention', label: '保留策略', type: 'select', options: ['成片 90 天 / 中间产物 14 天', '成片 180 天 / 中间产物 30 天', '成片永久 / 中间产物 30 天'] },
      { key: 'quota', label: '剩余空间', type: 'info' },
    ],
  },
]

const KEY = 'mountain.settings.v1'

function maskSecret(v: string): string {
  if (v.length <= 8) return '••••••••'
  return v.slice(0, 3) + '••••••••' + v.slice(-4)
}

/* 用 mock 的真实初始值覆盖 seed 默认值 */
function buildInitial(): { sections: SettingSection[]; logLevel: string } {
  const mockByKey: Record<string, Record<string, { value: string; has_secret?: boolean; secret_ref?: string; note?: string }>> = {}
  for (const s of settingsSections) {
    mockByKey[s.key] = {}
    for (const it of s.items) mockByKey[s.key][it.key] = { value: it.value, has_secret: it.has_secret, secret_ref: it.secret_ref, note: it.note }
  }
  const sections: SettingSection[] = SEED.map((sec) => ({
    key: sec.key,
    title: sec.title,
    items: sec.items.map((f) => {
      const m = mockByKey[sec.key]?.[f.key]
      return {
        key: f.key,
        label: f.label,
        type: f.type,
        options: f.options,
        note: m?.note ?? f.note,
        secret_ref: f.secret_ref ?? m?.secret_ref,
        rule: f.rule,
        value: m?.value ?? '',
        configured: f.type === 'secret' ? (m?.has_secret ?? false) : undefined,
      }
    }),
  }))
  return { sections, logLevel: 'info' }
}

function load(): { sections: SettingSection[]; logLevel: string } {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const p = JSON.parse(raw)
      if (p && Array.isArray(p.sections)) {
        return {
          sections: p.sections as SettingSection[],
          logLevel: typeof p.logLevel === 'string' ? p.logLevel : 'info',
        }
      }
    }
  } catch {
    /* 解析失败回退种子 */
  }
  return buildInitial()
}

export function useSettingsStore() {
  const init = useRef(load())
  const [sections, setSections] = useState<SettingSection[]>(init.current.sections)
  const [saved, setSaved] = useState<SettingSection[]>(init.current.sections)
  const [logLevel, setLogLevel] = useState<string>(init.current.logLevel)
  const [savedLogLevel, setSavedLogLevel] = useState<string>(init.current.logLevel)

  const dirty = JSON.stringify(sections) !== JSON.stringify(saved) || logLevel !== savedLogLevel

  const updateValue = (secKey: string, itemKey: string, value: string) => {
    setSections((ss) =>
      ss.map((s) =>
        s.key !== secKey
          ? s
          : {
              ...s,
              items: s.items.map((it) => {
                if (it.key !== itemKey) return it
                if (it.type === 'secret') return { ...it, secretValue: value, configured: value.trim() !== '' }
                return { ...it, value }
              }),
            },
      ),
    )
  }

  const reset = () => {
    setSections(saved)
    setLogLevel(savedLogLevel)
  }

  const sanitize = (ss: SettingSection[]) =>
    ss.map((s) => ({ ...s, items: s.items.map(({ secretValue, ...rest }) => rest) }))

  const save = async () => {
    const payload: Record<string, unknown> = { log_level: logLevel }
    for (const s of sections) {
      const p: Record<string, unknown> = {}
      for (const it of s.items) {
        if (it.type === 'secret') {
          if (it.secretValue !== undefined && it.secretValue !== '') p[it.key] = { secret: it.secretValue }
          else if (it.configured === false && it.secret_ref) p[it.key] = { secret: '' }
        } else {
          p[it.key] = it.value
        }
      }
      payload[s.key] = p
    }
    const res = await submitCommand('update_settings', payload)
    if (!res.ok) return res

    const committed: SettingSection[] = sections.map((s) => ({
      ...s,
      items: s.items.map((it) => {
        if (it.type !== 'secret') return it
        if (it.secretValue && it.secretValue !== '') return { ...it, configured: true, value: maskSecret(it.secretValue), secretValue: undefined }
        if (it.configured === false) return { ...it, value: '', secretValue: undefined }
        return { ...it, secretValue: undefined }
      }),
    }))
    setSaved(committed)
    setSections(committed)
    setSavedLogLevel(logLevel)
    return res
  }

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify({ sections: sanitize(saved), logLevel: savedLogLevel }))
    } catch {
      /* 容量超限忽略 */
    }
  }, [saved, savedLogLevel])

  return { sections, dirty, updateValue, reset, save, logLevel, setLogLevel }
}

