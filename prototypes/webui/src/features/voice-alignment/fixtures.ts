import type { VoiceAlignmentView } from './types'

/* ==========================================================================
   语音与对齐 · 原型 fixtures（明确命名，仅用于演示）
   四个演示视图：正常可用 / TTS 不可用 / Whisper 不可用 / 加载中。
   全部为内存常量：无 localStorage/sessionStorage、无网络请求、无 Secret。
   ========================================================================== */

/** 正常可用：两服务均已配置且 available */
export const VA_VIEW_AVAILABLE: VoiceAlignmentView = {
  state: 'ready',
  tts: {
    id: 'indextts',
    name: 'IndexTTS 语音克隆',
    description: '基于参考音色的零样本语音合成，负责把每个 Voice Unit 生成为语音。',
    category: '语音',
    config_status: 'configured',
    availability: { state: 'available' },
    config: {
      服务URL: 'http://127.0.0.1:7860',
      运行模式: 'FP16 · 本地推理',
    },
    configure_hint: '在「模型服务」中维护 IndexTTS 对应的服务商条目',
  },
  alignment: {
    id: 'whisper',
    name: 'Whisper 语音对齐',
    description: '对合成语音做字级时间戳对齐，驱动画面在正确的时间点切换。',
    category: '工具链 · 对齐',
    config_status: 'configured',
    availability: { state: 'available' },
    config: {
      运行模式: 'local · 本地推理',
    },
    configure_hint: 'Whisper 对齐随运行环境提供，无需单独接入服务地址',
  },
}

/** TTS 不可用：服务进程未响应 */
export const VA_VIEW_TTS_UNAVAILABLE: VoiceAlignmentView = {
  state: 'ready',
  tts: {
    ...VA_VIEW_AVAILABLE.tts,
    config_status: 'configured',
    availability: {
      state: 'unavailable',
      error_code: 'E-TTS-CONNECTION-REFUSED',
      suggestion:
        '无法连接 IndexTTS 服务。请确认本地服务已启动（默认端口 7860），或检查防火墙/端口配置后重试。',
    },
  },
  alignment: VA_VIEW_AVAILABLE.alignment,
}

/** Whisper 不可用：对齐组件缺失 */
export const VA_VIEW_WHISPER_UNAVAILABLE: VoiceAlignmentView = {
  state: 'ready',
  tts: VA_VIEW_AVAILABLE.tts,
  alignment: {
    ...VA_VIEW_AVAILABLE.alignment,
    config_status: 'unconfigured',
    availability: {
      state: 'unavailable',
      error_code: 'E-ALIGN-TOOLCHAIN-MISSING',
      suggestion:
        'Whisper 对齐组件未检测到。请安装对齐工具链后由运行环境重新探测；安装前任务将使用等比例分配的可见降级。',
    },
  },
}

/** 加载中：整页骨架 */
export const VA_VIEW_LOADING: VoiceAlignmentView = {
  state: 'loading',
  tts: VA_VIEW_AVAILABLE.tts,
  alignment: VA_VIEW_AVAILABLE.alignment,
}

/** 原型演示切换器使用的全部演示项 */
export const VA_DEMO_VIEWS: { key: string; label: string; view: VoiceAlignmentView }[] = [
  { key: 'available', label: '正常可用', view: VA_VIEW_AVAILABLE },
  { key: 'tts-unavailable', label: 'TTS 不可用', view: VA_VIEW_TTS_UNAVAILABLE },
  { key: 'whisper-unavailable', label: 'Whisper 不可用', view: VA_VIEW_WHISPER_UNAVAILABLE },
  { key: 'loading', label: '加载中', view: VA_VIEW_LOADING },
]
