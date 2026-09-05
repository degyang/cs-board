# 有温度出品｜白板声画工坊

> 把你的表达，做成一支会说话的视频。

白板声画工坊是一个本地运行的 AI 视频制作工作台。上传一段参考音频、粘贴中文文案，选择视觉模板或提供人物与风格参考，系统会自动完成音色克隆、内容拆解、插画、手绘笔迹、字幕与音画合成，并导出 MP4。

素材、密钥、任务历史和成片默认都保留在本机；同一局域网内的团队也可以共用一条制作队列。

## 你可以用它做什么

```text
参考音频 + 中文文案 +（可选）风格 / 人物参考
                    ↓
音色克隆 → 内容拆解 → 统一画面 → 动画渲染 → 字幕与音画合成
                    ↓
                 MP4 成片
```

| 制作模式 | 适合什么 | 你得到什么 |
| --- | --- | --- |
| 标准制作 | 知识讲解、故事口播、课程宣传 | 自动拆分分镜，生成插画并绘制白板动画。 |
| 自定义参考 | 固定 IP、品牌视频、系列内容 | 上传一张风格图和人物参考，让画风与角色贯穿全片。 |
| 动态信息图 | 观点表达、商业分析、课程内容 | 根据真实旁白时间生成随讲解展开的动态知识卡片。 |

## 核心能力

| 能力 | 说明 |
| --- | --- |
| 本地音色克隆 | 接入自己的 IndexTTS Gradio 或 FastAPI 服务，参考音频不离开本机。 |
| 12 个视觉模板 | 从极简白板、国风、手账到赛博霓虹；每个模板都有对应的画面特征和内容建议。 |
| 自定义人物与画风 | 支持 1 张风格参考图，以及最多 5 个角色、每人 1–3 张参考图。 |
| 动态信息图 | 先将旁白对齐为短语时间表，再按真实说话时间逐项呈现内容，避免画面抢跑。 |
| 中文重点词 | 可本地叠加 4–10 字重点短语，避开图片模型生成中文容易乱码的问题；支持一键关闭。 |
| 可控成片节奏 | 支持字幕开关、笔身账号名、4 档线条绘制量，以及每张图承载 1–4 个分镜。 |
| 任务复用与恢复 | 配音、分镜、图片、分段视频与成片均有检查点；调整本地渲染设置时无需重复调用模型。 |
| 局域网协作 | 多台电脑可查看共享队列、进度和历史；个人制作偏好保留在各自浏览器。 |

## 视觉模板

选择模板会同时影响插画的配色、线条、材质与构图。预览图展示的是视觉方向；实际人物、物体和场景会随文案变化。

| 模板 | 画面特征 | 推荐内容 |
| --- | --- | --- |
| 极简粗线简笔白板风 | 粗黑线、少量配色、清爽留白 | 知识讲解、个人表达、复盘总结 |
| 极简商务涂鸦风 | 几何图表、蓝绿配色、专业克制 | 产品介绍、商业分析、任务汇报 |
| 暖米黄素描白板风 | 铅笔排线、纸张质感、温暖细腻 | 人物故事、个人成长、品牌叙事 |
| 粗线扁平国风卡通 | 朱红玉绿、国风纹样、生动平涂 | 传统文化、国风品牌、中文创意 |
| 爆款高热吸睛风 | 高饱和、强对比、夸张动势 | 短视频开场、强观点、热点表达 |
| 黑金科技发布会风 | 黑金光效、科技舞台、高级权威 | AI、科技产品、发布会 |
| 清新治愈手账风 | 柔和水彩、低饱和配色、生活手账感 | 情感、生活方式、自我成长 |
| 复古报纸拼贴风 | 撕纸拼贴、半色调、编辑杂志感 | 深度观点、文化内容、案例复盘 |
| 纸感隐喻拼贴风 | 手工剪纸、观点隐喻、高级克制 | 价值观、关系、流程、复杂观点 |
| 漫画墨线解释风 | 漫画墨线、半调网点、概念机制 | 原理讲解、机制拆解、商业洞察 |
| 3D黏土趣味风 | 黏土材质、玩具比例、温暖可爱 | 亲子教育、轻量品牌、趣味科普 |
| 赛博霓虹漫画风 | 霓虹青紫、漫画速度线、未来感 | AI 趋势、数码科技、年轻化观点 |

## 5 分钟启动

### 环境要求

- Windows 10/11、WSL 2（Ubuntu 等）或 macOS
- Python 3.11+
- Node.js 22.13+
- FFmpeg 与 FFprobe，且已加入系统 `PATH`
- 可访问的 IndexTTS 2.5 服务（Gradio 或 FastAPI）
- OpenLux API Key，并有文本模型与图片模型的调用权限

先确认音视频依赖可用：

```powershell
ffmpeg -version
ffprobe -version
```

所有运行时依赖必须安装在实际启动任务的系统中。例如在 WSL 中启动时，Python、Node、FFmpeg 和字体都应安装在该 WSL 发行版中；不要混用 Windows 的 `.venv` 或 `node_modules`。**推荐每个系统使用各自的 Git 克隆目录**；若必须共用目录，在切换系统前删除 `.venv`、`web/node_modules` 与 `video_renderer/node_modules` 后重新安装，避免原生依赖互相污染。

### Windows

在任务根目录执行一次安装：

```powershell
python scripts/prepare_env.py
.\.venv\Scripts\python.exe -m pip install -r webapp\requirements.txt
Push-Location web
npm ci
Pop-Location
Push-Location video_renderer
npm ci
Pop-Location
```

双击 `启动白板工坊.bat`，或执行：

```powershell
.\start-webapp.ps1
```

### WSL 2 / Linux

在 WSL 终端进入任务目录后执行（Ubuntu/Debian 的字体包名如下）：

```bash
sudo apt update
sudo apt install -y ffmpeg fonts-noto-cjk
python3 scripts/prepare_env.py
.venv/bin/python -m pip install -r webapp/requirements.txt
(cd web && npm ci)
(cd video_renderer && npm ci)
./start-webapp.sh
```

如果任务当前位于 `/mnt/c/...`，可以运行，但视频渲染涉及大量小文件，建议将任务放到 WSL 的 Linux 文件系统（如 `~/Tasks/cs-board`）以获得更稳定、更快的 I/O。WSL 启动后可直接在 Windows 浏览器打开 `http://127.0.0.1:13000/`；局域网访问还需按你的 WSL 网络模式或 Windows 防火墙规则放行端口。

### macOS

先安装 [Homebrew](https://brew.sh/)，再执行：

```bash
brew install python@3.11 node ffmpeg
python3 scripts/prepare_env.py
.venv/bin/python -m pip install -r webapp/requirements.txt
(cd web && npm ci)
(cd video_renderer && npm ci)
chmod +x start-webapp.sh
./start-webapp.sh
```

macOS 自带苹方字体；Linux 请安装 `fonts-noto-cjk`，否则图片中的中文重点词可能无法正确绘制。启动器会启动前后端并打开 [http://127.0.0.1:13000/](http://127.0.0.1:13000/)。同一局域网设备可通过启动器输出的地址访问。

### 首次配置

打开右上角的 **API 设置**，填写并测试以下内容：

1. **OpenLux API Key**：只保存在本机 `.webapp/config.json`，页面不会回显完整密钥。
2. **文本模型**：默认 `gpt-5`，用于拆解文案、生成分镜或信息图结构。
3. **图片模型**：默认 `gpt-image-2`，用于生成插画。
4. **IndexTTS 地址与接口类型**：Gradio 通常为 `http://127.0.0.1:7860`，FastAPI 通常为 `8000` 端口。

测试连接成功后，上传 10–30 秒、单人且噪声较少的参考音频，粘贴至少 10 个字的中文文案，选择制作模式和视觉模板即可开始。

## 使用建议

### 标准制作

适合先快速验证一个内容方向：选择模板，上传音频和文案，系统会将内容拆成场景、生成统一画面并合成白板动画。

### 自定义参考

适合固定 IP 或品牌化内容：上传一张风格参考图，再添加 1–5 个角色。每个角色可上传 1–3 张不同角度的参考图；系统会按文案安排角色，不会直接复制参考图中的人物。

### 动态信息图

适合需要“边讲边理解”的内容。系统先依据真实旁白生成短语时间表，再生成章节、核心观点和图文结构；内容元素只会在对应的语音开始后出现。详细原则见 [动态信息图语义时间契约](docs/semantic-timing-contract.md)。

## 运行与数据

所有本地配置、任务文件和成片均保存在 `.webapp/`：

```text
.webapp/
├── config.json          # 本机 API 与语音配置
├── preferences.json     # 兼容旧版偏好
└── jobs/<任务 ID>/       # 音频、分镜、图片、检查点、成片与任务元数据
```

`.webapp/`、`.env*`、虚拟环境、`node_modules` 与视频产物都已被 Git 忽略。不要在 Issue、日志、截图或提交记录中公开 API Key、参考音频和任务目录；安全问题请按 [SECURITY.md](SECURITY.md) 中的方式私下报告。

## 开发验证

```bash
# 首次运行完整测试时安装开发依赖（包括 Mountain JSON Schema 校验器）
.venv/bin/python -m pip install -r requirements-dev.txt

# 前端构建与页面验证
(cd web && npm test)

# 后端任务队列、断点恢复、时间线与 Mountain 契约测试
.venv/bin/python -m unittest discover -s tests -v
```

Windows PowerShell 请将最后一行替换为：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 任务结构

```text
├── assets/               # 画笔、视觉风格与参考素材
├── docs/                 # 动态信息图与工作流文档
├── scripts/              # 白板渲染、时间线与维护脚本
├── schemas/mountain/     # Mountain Task、Artifact、Event、Log 与 Audit JSON Schema
├── tests/                # 队列、恢复、语义时间与 Mountain 契约测试
├── video_renderer/       # Remotion 动态信息图渲染器
├── web-v2/               # Mountain 新 React/Vite 前端（独立目录，M07 实现）
├── webapp/               # FastAPI 后端
├── start-webapp.py       # 跨平台启动逻辑
├── start-webapp.sh       # WSL / Linux / macOS 入口
└── start-webapp.ps1      # Windows PowerShell 入口
```

## 贡献

欢迎提交 Issue 或 Pull Request。涉及渲染逻辑的改动，请同时说明真实素材下的时序、遮罩保护和最终成片验证结果。

## 许可证

本任务采用 [MIT License](LICENSE)。
