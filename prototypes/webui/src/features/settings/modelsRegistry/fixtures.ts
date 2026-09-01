import type { ModelRegistryView } from './types'

/* ==========================================================================
   模型服务注册表 · 原型 fixtures（明确命名，仅用于演示）
   全部为内存常量：无 localStorage/sessionStorage、无网络请求、无 Secret、无 apiKey。

   反映「当前能力事实」：
     - 本地 Codex Skills：插画生成（image.generate）
     - 本地 IndexTTS：语音合成 / 音色克隆（speech.synthesize）
     - 本地 Whisper：语音与文字时间对齐（audio.align）
     - 本地 FFmpeg：音画合成（media.compose）
     - 本地 白板渲染器：视觉渲染（video.render）
     - 外部图片 / 语音 / 音频 / 视频 API 为未来可加入的 Provider（未配置、未探测）
   ========================================================================== */

export const MODEL_REGISTRY_VIEW: ModelRegistryView = {
  services: [
    {
      id: 'codex-skills',
      name: 'Codex Skills',
      type: 'local',
      capabilities: ['image.generate'],
      modelOrMode: 'Codex Skills · 本地插画生成',
      configStatus: 'no-key-required',
      availability: 'available',
    },
    {
      id: 'indextts',
      name: 'IndexTTS',
      type: 'local',
      capabilities: ['speech.synthesize'],
      modelOrMode: 'IndexTTS · 本地推理',
      configStatus: 'no-key-required',
      availability: 'available',
    },
    {
      id: 'whisper',
      name: 'Whisper',
      type: 'local',
      capabilities: ['audio.align'],
      modelOrMode: 'whisper-large-v3 · 本地推理',
      configStatus: 'no-key-required',
      availability: 'available',
    },
    {
      id: 'ffmpeg',
      name: 'FFmpeg',
      type: 'local',
      capabilities: ['media.compose'],
      modelOrMode: 'FFmpeg 6.1.1',
      configStatus: 'no-key-required',
      availability: 'available',
    },
    {
      id: 'whiteboard-renderer',
      name: '白板渲染器',
      type: 'local',
      capabilities: ['video.render'],
      modelOrMode: 'Remotion 4.0 · 本地无头渲染',
      configStatus: 'no-key-required',
      availability: 'available',
    },
    {
      id: 'future-external-image',
      name: '未来外部图像 API（候选）',
      type: 'external-api',
      capabilities: ['image.generate'],
      baseUrl: '（待后端契约确认）',
      configStatus: 'unconfigured',
      availability: 'not-probed',
      suggestion:
        '外部 Provider 接入需经后端 API 与密钥库（SecretStore）支持；密钥不在此页存储或回显，仅在后端落库后立即清空。',
    },
  ],
}
