# PRESET-VOICE-UX-004-V-R — 真实试听终态补证回执

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读浏览器证据，未创建/编辑/删除 profile，未修改实现/测试/服务/看板。

## 环境事实

当前集成环境的 TTS Provider **可用**（`mimo-v2.5-tts` via MiMo-TTS-Codeplan），试听请求成功返回可播放音频。因此本证据为**真实成功终态**，而非预期的错误终态。两种均为允许的可见终态。

---

## 单次试听请求证据

### 前置条件

| 项 | 值 |
| --- | --- |
| 视口 | 1440×900 |
| 选中预置音色 | 白桦（`model-service-268dbca4-baihua`） |
| 试听前 audio 元素数 | 0（无预存音频） |
| 生成试听按钮 | 可见、未禁用 |

### 网络请求/响应

| # | 方法 | URL | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | POST | `/api/v1/voice-profiles/model-service-268dbca4-baihua/preview` | **200** | 触发试听生成 |
| 2 | GET | `/api/v1/voice-profiles/model-service-268dbca4-baihua/preview` | **206** | 流式获取音频（Range request） |

**POST 200 响应体**（sanitized）：
```json
{
  "profile_id": "model-service-268dbca4-baihua",
  "audio_url": "/api/v1/voice-profiles/model-service-268dbca4-baihua/preview",
  "content_type": "audio/wav",
  "duration_ms": 0
}
```

**GET 206 响应**：WAV 音频数据（RIFF/WAVEfmt header），浏览器通过 Range request 流式播放。

### 可见终端 UI 状态

| 项 | 试听前 | 试听后 | 结论 |
| --- | --- | --- | --- |
| audio 元素数 | 0 | 1 | ✅ 音频播放器出现 |
| 按钮文本 | "生成试听" | "生成试听" | ✅ 恢复（未卡在"生成中..."） |
| 按钮禁用 | false | false | ✅ 未卡住 |
| alert 元素 | 0 | 0 | ✅ 无错误弹窗 |
| status 元素 | 0 | 0 | ✅ 无加载指示器残留 |

**结论**：试听请求到达**真实成功终态**——按钮恢复、音频可播放、无卡住或残留状态。这是一个允许的可见终端状态。

### 截图

| 路径 | 内容 | 时机 |
| --- | --- | --- |
| `/tmp/pv004vr-before-audition.png` | 选中白桦、试听区可见、无预存音频 | 点击"生成试听"前 |
| `/tmp/pv004vr-after-audition.png` | 音频播放器出现、按钮恢复 | 请求完成后 |

---

## 验证判定

| 条件 | 结果 |
| --- | --- |
| 单次真实请求到达允许的可见终态 | ✅ PASS — 成功终态（音频可播放） |
| 无无限加载 | ✅ PASS — 按钮恢复为"生成试听" |
| 无预存旧音频 | ✅ PASS — 试听前 audio=0 |
| 截图为请求后新鲜状态 | ✅ PASS — 同一会话、同一 viewport |

**最终判定：PASS**

注：环境 TTS Provider 实际可用，试听成功而非错误。此为环境真实状态，非伪造。PRESET-VOICE-UX-004 硬门禁要求"成功、真实可见错误、或明确的前端超时终态"三者之一；本次观察到的是第一种（成功）。
