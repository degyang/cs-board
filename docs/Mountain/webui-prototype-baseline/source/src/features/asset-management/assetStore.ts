import { useEffect, useRef, useState } from 'react'

/* ==========================================================================
   资产管理 · 数据模型与持久化
   三类资产：预设风格 / 自定义风格 / 音色库。
   全部通过 localStorage 持久化（key: mountain.assets.v3），首次运行注入种子数据；
   之后所有 新增 / 修改 / 删除 都会落盘，刷新不丢。图片以 dataURL / 路径 / URL 存储。

   预设风格种子来自 cs-board/webapp/server.py:49-120 的 STYLE_PRESETS：
     - 12 个具体画面风格（极简粗线/极简商务/暖米黄素描…赛博霓虹）
     - 1 个默认「国风动态信息图」
   字段含义：
     - id          唯一 ID
     - name        风格中文名（用于页面定位与搜索）
     - image       预览图（路径/URL/dataURL，缺失时退化为渐变占位）
     - intro       视觉配方（来自 server.py 的中文 prompt 完整版）
     - shortDesc   4 字简短口诀（截图副标题「粗黑线 · 少量配色 · 清爽留白」）
     - tags        关键字数组（用于搜索，与 cs-board keyword 路由一致）
     - badge       卡片左上角小标签（'热门'/'新增'/null）
     - refImages   参考图数组（来自 paper-metaphor / oil-visual 目录，
                    用于路由到具体参考图，paper-metaphor 风格有多张）
     - source      出处说明，便于追溯

   旧版本 v1（mountain.assets.v1）和 v2（mountain.assets.v2）会自动迁移并按 name 去重；
   迁移时会用最新 SEED 回填"用户没编辑过"的字段（如新加的 webp 预览图），保证种子升级能传播。
   ========================================================================== */

export interface PresetStyle {
  id: string
  name: string
  image: string | null
  intro: string
  shortDesc?: string
  tags?: string[]
  badge?: string | null
  refImages?: string[]
  source?: string
  prompt?: string // 英文 prompt（留空则以 intro 作为最终指令）
}

export interface Character {
  id: string
  name: string
  intro: string
  refImage: string | null
}

export interface CustomStyle {
  id: string
  name: string
  styleImage: string | null
  characters: Character[]
}

export interface VoiceAsset {
  id: string
  name: string
  filePath: string
  durationSec: number
  /* —— 以下字段来自 index-tts/examples/registry.jsonl —— */
  langCode?: string // ZH / EN / ES / AR / JA
  engine?: string // indextts-2 / indextts-2.5
  emotionMode?: string // speaker | reference_audio | vector | text
  emotionRefPath?: string // 情感参考音频路径（reference_audio 模式专用）
  emotionWeight?: number // 情感权重 0~1
  sampleText?: string // 示例朗读文本（WebUI examples 展示语）
  tags?: string[] // 关键字（用于搜索）
  status?: string // available（可用）| verified（已验证）| limited（受限）
  statusNote?: string // 兼容性/受限原因说明
  source?: string // 出处说明
}

interface AssetStore {
  presets: PresetStyle[]
  customs: CustomStyle[]
  voices: VoiceAsset[]
}

const KEY_V3 = 'mountain.assets.v3'
const KEY_V2 = 'mountain.assets.v2'
const KEY_V1 = 'mountain.assets.v1'

/* ---------------- 种子：cs-board STYLE_PRESETS 提炼 ---------------- */

/** 纸感隐喻拼贴风的本地参考图（来自 cs-board/assets/style-references/paper-metaphor） */
const PAPER_REFS = [
  '/styles/previews/paper-metaphor.png',
  '/styles/paper-metaphor/01-cause-heart-vs-wound.png',
  '/styles/paper-metaphor/02-balance-many-forces.png',
  '/styles/paper-metaphor/03-process-machine.png',
  '/styles/paper-metaphor/04-overload-pushback.png',
  '/styles/paper-metaphor/05-choice-black-white.png',
  '/styles/paper-metaphor/06-work-stress.png',
  '/styles/paper-metaphor/07-scale-values.png',
  '/styles/paper-metaphor/08-dual-boxes.png',
  '/styles/paper-metaphor/09-road-between-extremes.png',
  '/styles/paper-metaphor/10-boundary-two-crowds.png',
]

/** 漫画墨线解释风的本地参考图（来自 cs-board/assets/style-references/oil-visual） */
const OIL_REFS = [
  '/styles/previews/oil-visual.png',
  '/styles/oil-visual/explainer-cost-comparison.png',
  '/styles/oil-visual/feedback-loop.png',
  '/styles/oil-visual/from-complex-to-clear.png',
  '/styles/oil-visual/pipeline-bottleneck.png',
  '/styles/oil-visual/transparent-illustration.png',
]

const SEED_PRESETS: PresetStyle[] = [
  {
    id: 'ps-cs-1',
    name: '极简粗线简笔白板风',
    image: '/styles/previews/minimal-whiteboard.webp',
    shortDesc: '粗黑线 · 少量配色 · 清爽留白',
    tags: ['白板', '粗线', '马克笔', '知识科普', '讲解', '清爽'],
    badge: null,
    intro:
      '暖白色纯净背景，圆润有亲和力的粗黑马克笔轮廓，人物和物体高度概括，只使用橙色与钴蓝色做少量平涂点缀；几乎没有阴影、纹理和细碎结构，留白充足，像现场快速画出的清爽白板简笔画。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-2',
    name: '极简商务涂鸦风',
    image: '/styles/previews/business-doodle.webp',
    shortDesc: '几何图表 · 蓝绿配色 · 专业克制',
    tags: ['商务', '蓝绿', '图表', '产品', '科技', '克制'],
    badge: null,
    intro:
      '冷白至极浅灰背景，深海军蓝的精准几何轮廓，钴蓝与青绿色作为强调色；用整齐的卡片、流程箭头、图表和图标组织信息，线条克制利落、间距规整，呈现专业的商业演示和科技产品解说感，禁止暖黄纸张与随意手绘笔触。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-3',
    name: '暖米黄素描白板风',
    image: '/styles/previews/warm-pencil.webp',
    shortDesc: '铅笔排线 · 纸张质感 · 温暖细腻',
    tags: ['素描', '铅笔', '米黄', '手账', '编辑', '温柔'],
    badge: null,
    intro:
      '温暖米黄色纸张底色，真实石墨铅笔线条，轻柔排线、交叉线和深浅笔压，辅以低饱和赭石色与灰蓝色；保留手工速写的纸张颗粒和结构细节，像一本质感细腻的编辑手账，不能画成粗线扁平图标。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-4',
    name: '粗线扁平国风卡通',
    image: '/styles/previews/guofeng-flat.webp',
    shortDesc: '朱红玉绿 · 国风纹样 · 生动平涂',
    tags: ['国风', '卡通', '朱红', '玉绿', '科普', '平涂'],
    badge: null,
    intro:
      '温暖宣纸色背景，深棕色粗轮廓，朱红、玉绿与靛青的饱和平涂色块；人物比例生动简化，少量使用祥云、笔触和中式构图节奏，形成现代国风科普动画效果，禁止写实素描和欧美商务信息图观感。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-5',
    name: '爆款高热吸睛风',
    image: '/styles/previews/viral-pop.webp',
    shortDesc: '高饱和 · 强对比 · 短视频冲击力',
    tags: ['短视频', '封面', '高饱和', '冲击', '热门'],
    badge: '热门',
    intro:
      '明亮黄色高能背景，超粗黑色外轮廓，热烈橙红与电光钴蓝的大色块，夸张但友好的人物表情和动作，配合放射爆炸形、速度线与强烈斜向构图；主体要大、对比要强、第一眼就能看懂，具有热门短视频封面般的冲击力，但保持轮廓干净，不能堆满琐碎元素。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-6',
    name: '黑金科技发布会风',
    image: '/styles/previews/black-gold-tech.webp',
    shortDesc: '黑金光效 · 科技舞台 · 高级权威',
    tags: ['黑金', '科技', '高端', '舞台', '权威', '发布'],
    badge: null,
    intro:
      '深黑与炭灰背景，金属金色作为主轮廓和高光，少量电光青色点缀；使用精致的环形界面、几何数据结构和舞台式光影，主体高级、权威、科技感强，像高端科技产品发布会，禁止暖白纸张和可爱手绘效果。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-7',
    name: '清新治愈手账风',
    image: '/styles/previews/healing-journal.webp',
    shortDesc: '柔和水彩 · 治愈配色 · 生活手账',
    tags: ['水彩', '治愈', '手账', '生活', '亲子', '温暖'],
    badge: null,
    intro:
      '奶油白纸张背景，圆润轻柔的手绘线条，鼠尾草绿、蜜桃粉、奶油黄和天蓝色的低饱和水彩；少量加入胶带、贴纸与植物点缀，整体通透、温暖、治愈、生活化，保持留白，禁止强烈黑线和高对比商务图表。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-8',
    name: '复古报纸拼贴风',
    image: '/styles/previews/retro-collage.webp',
    shortDesc: '撕纸拼贴 · 半色调 · 编辑视觉',
    tags: ['复古', '报纸', '拼贴', '编辑', '撕纸', '半色调'],
    badge: null,
    intro:
      '暖灰新闻纸底色，黑色油墨主体、复古红色强调块、半色调网点、丝网印刷颗粒与撕纸边缘；人物和物体像剪下后重新拼贴的编辑视觉，层次大胆、粗粝、有文化杂志感，禁止光滑渐变和现代扁平信息图。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-9',
    name: '纸感隐喻拼贴风',
    image: '/styles/paper-metaphor/01-cause-heart-vs-wound.png',
    shortDesc: '手工剪纸 · 观点隐喻 · 高级克制',
    tags: [
      '剪纸',
      '隐喻',
      '观点',
      '流程',
      '对比',
      '因果',
      '层级',
      '清单',
      '矩阵',
      '高级',
    ],
    badge: '新增',
    refImages: PAPER_REFS,
    intro:
      '暖米白手工纸背景，清晰纸纤维、撕边、轻微褶皱与手工裁切痕迹；人物和物体由剪纸拼贴叠层构成，带柔和浅浮雕投影，成人卡通比例、圆白眼与小黑瞳、细线鼻口。主色仅使用米杏、炭黑、深灰、暖灰、珊瑚红和灰粉，金黄只用于希望、价值或关键转折。每张图只选择定义、流程、对比、层级、因果、清单、时间或矩阵中的一个主结构，用单一具体隐喻表达观点；留白占 25%–45%，主视觉不超过 3 组，辅助符号不超过 5 类。禁止摄影写实、光滑塑料 3D、扁平矢量图标、儿童贴纸、霓虹科技 UI、文字、Logo、水印和图标堆砌。\n\n参考图路由规则（按文案关键字选图）：\n· 流程｜系统｜自动化｜生产｜步骤｜机器｜效率 → 03-process-machine.png\n· 对比｜选择｜判断｜黑白｜两种｜不是｜而是 → 05-choice-black-white.png / 09-road-between-extremes.png\n· 因果｜原因｜结果｜影响｜关系 → 01-cause-heart-vs-wound.png\n· 层级｜成长｜方向｜阶段｜进阶 → 09-road-between-extremes.png\n· 清单｜资源｜经验｜多个｜要素 → 08-dual-boxes.png\n· 矩阵｜四象限｜双维度 → 02-balance-many-forces.png\n· 价值｜权衡｜平衡｜责任｜收益 → 07-scale-values.png\n· 压力｜过载｜诱惑｜信息 → 04-overload-pushback.png / 06-work-stress.png\n· 边界｜群体｜立场｜冲突 → 10-boundary-two-crowds.png',
    source: 'cs-board STYLE_PRESETS + paper-metaphor 路由',
  },
  {
    id: 'ps-cs-10',
    name: '漫画墨线解释风',
    image: '/styles/oil-visual/from-complex-to-clear.png',
    shortDesc: '漫画墨线 · 半调网点 · 概念机制',
    tags: [
      '漫画',
      '墨线',
      '半调',
      '对比',
      '循环',
      '流程',
      '角色',
      '概念',
      '机制',
      '插画',
    ],
    badge: '新增',
    refImages: OIL_REFS,
    intro:
      '暖灰米白纸张背景，使用自信、粗细有变化的黑色漫画墨线；灰面和阴影只用经典圆点半色调，不用柔和渐变。黑白灰为主体，固定暖黄色只用于边牧或关键物件，每张图最多再使用两种低饱和语义色：蓝色表示输入或内容，橙色表示行动、警告或成本，紫色表示过程，绿色表示成功或完成。关系必须用具体物件、路径、状态变化和重复材料证明，不能靠装饰图标凑数。原文需要通用角色时才使用戴细圆框眼镜的圆头极简线人，胖胖的暖黄边牧只作合适的陪伴角色；抽象机制页优先画物件和状态，不强塞人物。禁止 3D、摄影写实、光滑渐变、通用卡片网格、仪表盘、杂乱装饰、Logo 和水印。\n\n参考图路由规则（按文案布局类型选图）：\n· 对比｜差异｜两种｜成本｜取舍 → 机制对比 explainer-cost-comparison.png\n· 循环｜反馈｜闭环 → 机制循环 feedback-loop.png\n· 流程｜步骤｜瓶颈｜管线｜机制 → 机制流程 pipeline-bottleneck.png\n· 人物｜角色｜讲解者｜陪伴｜团队｜主人公 → 角色场景 transparent-illustration.png\n· 其它 → 概念解释 from-complex-to-clear.png',
    source: 'cs-board STYLE_PRESETS + oil-visual 路由',
  },
  {
    id: 'ps-cs-11',
    name: '3D黏土趣味风',
    image: '/styles/previews/clay-3d.webp',
    shortDesc: '黏土材质 · 玩具比例 · 温暖可爱',
    tags: ['3D', '黏土', '可爱', '玩具', '童趣', '温暖'],
    badge: null,
    intro:
      '可爱的三维黏土动画场景，圆润玩具化比例，可见细微手作指纹，珊瑚橙、青绿色、亮黄色和奶油色的柔和配色，温暖棚拍光与轻柔投影，像精致的定格动画小剧场，主体清楚，禁止二维线稿和写实摄影材质。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-12',
    name: '赛博霓虹漫画风',
    image: '/styles/previews/cyber-neon.webp',
    shortDesc: '霓虹青紫 · 漫画速度线 · 未来感',
    tags: ['赛博', '霓虹', '未来', '漫画', '速度线', '戏剧'],
    badge: null,
    intro:
      '深靛蓝至黑色背景，青色与洋红色霓虹边缘光，紫色渐变和粗黑漫画轮廓；加入克制的速度线、全息几何形与未来创作者工作室氛围，构图动感、戏剧性强，同时确保人物面部和关键物体清楚可读。',
    source: 'cs-board STYLE_PRESETS',
  },
  {
    id: 'ps-cs-13',
    name: '国风动态信息图',
    image: null,
    shortDesc: '暖米宣纸 · 朱红重点 · 国风淡彩',
    tags: ['国风', '信息图', '淡彩', '宣纸', '知识', '留白'],
    badge: null,
    intro:
      '暖米白宣纸背景，深灰正文与朱红重点，低饱和靛青辅助色；固定总标题和章节标题，以知识卡片、关系线、时间轴、层级或对比结构组织观点，搭配克制的国风淡彩插画，大量留白，成人知识内容，禁止摄影写实和儿童卡通。',
    source: 'cs-board STYLE_PRESETS (INFOGRAPHIC_STYLE 默认)',
  },
]

const SEED_CUSTOMS: CustomStyle[] = [
  {
    id: 'cs-1',
    name: '我的科普风',
    styleImage: null,
    characters: [
      { id: 'ch-1', name: '主讲人 · 小林', intro: '理性、语速平稳，承担主要讲解，画面常居中。', refImage: null },
      { id: 'ch-2', name: '助手 · 喵', intro: '俏皮活泼，负责举例与互动，画面偏右下角。', refImage: null },
    ],
  },
  {
    id: 'cs-2',
    name: '复古漫画风',
    styleImage: null,
    characters: [{ id: 'ch-3', name: '旁白', intro: '统一旁白音色，承接转场与总结。', refImage: null }],
  },
]

/* ---------------- 种子：index-tts/examples/registry.jsonl 提炼 ----------------
 * 音色样例与情感参考音频已复制到 public/voices/（wav 原件来自
 * D:\Workstation\Developments\platforms\index-tts\examples，与本地 WebUI 7860 的
 * examples 页展示一致）。字段对应 registry.jsonl：
 *   - status    available→'available' / verified→'verified' / requires_v25 /
 *               requires_qwen_emotion→'limited'（当前 8GB 低显存档受限）
 *   - emotion   mode: speaker→音色自带 / reference_audio→情感参考音频 /
 *               vector→情绪向量 / text→情绪文本
 */
const SEED_VOICES: VoiceAsset[] = [
  {
    id: 'vc-01',
    name: '纪念品介绍 · 中文自然',
    filePath: '/voices/voice_03.wav',
    durationSec: 2.1,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'speaker',
    sampleText: '这个呀，就是我们精心制作准备的纪念品，大家可以看到这个色泽和这个材质啊，哎呀多么的光彩照人。',
    tags: ['中文', '自然', '介绍', '热情'],
    status: 'available',
    statusNote: 'IndexTTS-2 在 FP16 下支持中文音色自带情感。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-02',
    name: '专业人士语气 · 中文自然',
    filePath: '/voices/voice_04.wav',
    durationSec: 2.3,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'speaker',
    sampleText: '你就需要我这种专业人士的帮助，就像手无缚鸡之力的人进入雪山狩猎，一定需要最老练的猎人指导。',
    tags: ['中文', '自信', '叙述', '专业'],
    status: 'available',
    statusNote: 'IndexTTS-2 在 FP16 下支持中文音色自带情感。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-03',
    name: '英文自然 · 惊讶疑问',
    filePath: '/voices/voice_01.wav',
    durationSec: 2.4,
    langCode: 'EN',
    engine: 'indextts-2',
    emotionMode: 'speaker',
    sampleText: 'Translate for me, what is a surprise!',
    tags: ['英文', '惊讶', '疑问'],
    status: 'available',
    statusNote: 'IndexTTS-2 在 FP16 下支持英文音色自带情感。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-04',
    name: '英文自然 · 责问质询',
    filePath: '/voices/voice_02.wav',
    durationSec: 2.9,
    langCode: 'EN',
    engine: 'indextts-2',
    emotionMode: 'speaker',
    sampleText: 'If you’d ever treated me like a human being, would they have dared to do this?',
    tags: ['英文', '责问', '缩读'],
    status: 'available',
    statusNote: '英文标点与缩读覆盖样例。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-08',
    name: '剑道叙述 · 中文长段落',
    filePath: '/voices/voice_05.wav',
    durationSec: 8.4,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'speaker',
    sampleText:
      '在真正的日本剑道中，格斗过程极其短暂，常常短至半秒，最长也不超过两秒，利剑相击的转瞬间，已有一方倒在血泊中。但在这电光石火的对决之前，双方都要以一个石雕般凝固的姿势站定，长时间的逼视对方，这一过程可能长达十分钟！',
    tags: ['中文', '长文本', '叙述', '分段'],
    status: 'available',
    statusNote: '长文本分段示例；8GB 显存建议按自然段落粒度送合成。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-09',
    name: '诗句转折 · 中文风趣',
    filePath: '/voices/voice_06.wav',
    durationSec: 6.2,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'speaker',
    sampleText: '床前明月光，疑是地上霜，举头望明月，我叫郭德纲。',
    tags: ['中文', '诗句', '韵律', '风趣'],
    status: 'available',
    statusNote: '短中文韵律样例。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-10',
    name: '情感参考 · 不满与厌恶',
    filePath: '/voices/voice_07.wav',
    durationSec: 2.0,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'reference_audio',
    emotionRefPath: '/voices/emo_hate.wav',
    emotionWeight: 0.65,
    sampleText: '你看看你，对我还有没有一点父子之间的信任了。',
    tags: ['中文', '情感参考', '厌恶', '责备'],
    status: 'available',
    statusNote: '情感参考音频无需 QwenEmotion 即可支持；参考片段极短，适合作为官方行为样例。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-11',
    name: '情感参考 · 悲伤与孤独',
    filePath: '/voices/voice_08.wav',
    durationSec: 1.5,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'reference_audio',
    emotionRefPath: '/voices/emo_sad.wav',
    emotionWeight: 0.8,
    sampleText: '我站在人海中，却感觉比任何时候都要孤独。',
    tags: ['中文', '情感参考', '悲伤', '孤独'],
    status: 'verified',
    statusNote: '用户已在 GTX 1070 Ti 本地生成成功（2026-08-22）。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-12',
    name: '情绪向量 · 撒娇式悲伤',
    filePath: '/voices/voice_09.wav',
    durationSec: 10.2,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'vector',
    emotionWeight: 0.8,
    sampleText: '对不起嘛！我的记性真的不太好，但是和你在一起的事情，我都会努力记住的~',
    tags: ['中文', '情绪向量', '悲伤', '撒娇'],
    status: 'available',
    statusNote: '悲伤维度的 WebUI 折算系数为 1.0，源向量与 CLI 向量一致。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-13',
    name: '情绪文本 · 极度悲伤',
    filePath: '/voices/voice_11.wav',
    durationSec: 7.9,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'text',
    emotionWeight: 1.0,
    sampleText: '这些年的时光终究是错付了...',
    tags: ['中文', '情绪文本', '悲伤'],
    status: 'limited',
    statusNote: '情绪文本依赖 QwenEmotion；8GB 低显存档不加载，建议改用显式情绪向量。',
    source: 'index-tts examples · webui-demo',
  },
  {
    id: 'vc-14',
    name: '情绪文本 · 惊恐',
    filePath: '/voices/voice_12.wav',
    durationSec: 2.7,
    langCode: 'ZH',
    engine: 'indextts-2',
    emotionMode: 'text',
    emotionWeight: 1.0,
    sampleText: '快躲起来！是他要来了！他要来抓我们了！',
    tags: ['中文', '情绪文本', '惊恐'],
    status: 'limited',
    statusNote: '情绪文本依赖 QwenEmotion；8GB 低显存档不加载，建议改用显式情绪向量。',
    source: 'index-tts examples · webui-demo',
  },
]

/* -------- 按 name 去重合并（种子在前，用户已有 custom 在后） -------- */
function uniqByName<T extends { name?: string }>(items: T[]): T[] {
  const seen = new Set<string>()
  const out: T[] = []
  for (const it of items) {
    const k = (it?.name ?? '').trim()
    if (!k || seen.has(k)) continue
    seen.add(k)
    out.push(it)
  }
  return out
}

/* ------------------------------------------------------------------ */
/* 回填辅助：把"种子字段"回填进旧数据中为 null/空 的位置                 */
/*  - 用户编辑过的字段（值非空）保留                                       */
/*  - 用户没动过的字段（null/空数组/空串）从最新种子拉新值                    */
/*  这样种子升级（如新增 webp 预览）就能真正生效                            */
/* ------------------------------------------------------------------ */
function backfillPreset(stored: PresetStyle, seed: PresetStyle | undefined): PresetStyle {
  if (!seed) return stored
  const has = <T>(v: T | null | undefined): v is T =>
    v !== null && v !== undefined && (Array.isArray(v) ? v.length > 0 : String(v).trim() !== '')
  return {
    ...stored,
    image: has(stored.image) ? stored.image : (seed.image ?? null),
    shortDesc: has(stored.shortDesc) ? stored.shortDesc : (seed.shortDesc ?? ''),
    tags: has(stored.tags) ? stored.tags : (seed.tags ?? []),
    badge: stored.badge ?? seed.badge ?? null,
    refImages: has(stored.refImages) ? stored.refImages : seed.refImages,
    source: has(stored.source) ? stored.source : (seed.source ?? ''),
    intro: has(stored.intro) ? stored.intro : (seed.intro ?? ''),
    prompt: has(stored.prompt) ? stored.prompt : (seed.prompt ?? ''),
  }
}

/* 合并 SEED 与 用户数据：按 name 对齐；种子在前保证顺序 */
function mergeWithSeed(storedList: PresetStyle[]): PresetStyle[] {
  const byName = new Map<string, PresetStyle>()
  for (const s of storedList) {
    if (s?.name) byName.set(s.name.trim(), s)
  }
  const out: PresetStyle[] = []
  const seen = new Set<string>()
  // 种子在前 → 系统预设按种子顺序排，用户编辑过的同名条目回填后覆盖
  for (const seed of SEED_PRESETS) {
    const k = (seed.name ?? '').trim()
    if (!k || seen.has(k)) continue
    seen.add(k)
    const stored = byName.get(k)
    out.push(stored ? backfillPreset(stored, seed) : seed)
  }
  // 用户独有的自定义（不在种子里的）
  for (const s of storedList) {
    const k = (s?.name ?? '').trim()
    if (!k || seen.has(k)) continue
    seen.add(k)
    out.push(s)
  }
  return out
}

/* ---------------- 音色库 · 展示字典（资产管理与新建任务共用） ---------------- */
export const VOICE_LANG_LABEL: Record<string, string> = {
  ZH: '中文',
  EN: '英文',
  ES: '西班牙语',
  AR: '阿拉伯语',
  JA: '日语',
}
export const VOICE_EMO_LABEL: Record<string, string> = {
  speaker: '音色自带情感',
  reference_audio: '情感参考音频',
  vector: '情绪向量',
  text: '情绪文本',
}
export const VOICE_STATUS_LABEL: Record<string, string> = {
  available: '可用',
  verified: '已验证',
  limited: '受限',
}

/* ---------------- 音色库合并 ----------------
 * 旧版 v3 的音色种子（va-1~va-3，assets/voices/*.wav 假路径）被
 * index-tts/examples 的 14 条真实样例替换。规则：
 *  1) 丢弃「未被用户编辑过」的旧种子（id 与假路径同时命中才丢弃）；
 *  2) 其余条目按 name 与新种子对齐：空字段用种子回填，非空保留用户编辑；
 *  3) 种子在前、用户独有条目在后。
 */
const OLD_VOICE_IDS = new Set(['va-1', 'va-2', 'va-3'])
const OLD_VOICE_PATHS = new Set([
  'assets/voices/std-female.wav',
  'assets/voices/warm-male.wav',
  'assets/voices/soft-kid.wav',
])
/* 已下线的种子：非中/英文的多语种样例（西语/阿语/日语），从 localStorage 一并清除 */
const REMOVED_VOICE_IDS = new Set(['vc-05', 'vc-06', 'vc-07'])

function backfillVoice(stored: VoiceAsset, seed: VoiceAsset | undefined): VoiceAsset {
  if (!seed) return stored
  const has = <T>(v: T | null | undefined): v is T =>
    v !== null && v !== undefined && (Array.isArray(v) ? v.length > 0 : String(v).trim() !== '')
  return {
    ...stored,
    filePath: has(stored.filePath) ? stored.filePath : (seed.filePath ?? ''),
    langCode: has(stored.langCode) ? stored.langCode : seed.langCode,
    engine: has(stored.engine) ? stored.engine : seed.engine,
    emotionMode: has(stored.emotionMode) ? stored.emotionMode : seed.emotionMode,
    emotionRefPath: has(stored.emotionRefPath) ? stored.emotionRefPath : seed.emotionRefPath,
    emotionWeight: stored.emotionWeight ?? seed.emotionWeight,
    sampleText: has(stored.sampleText) ? stored.sampleText : seed.sampleText,
    tags: has(stored.tags) ? stored.tags : seed.tags,
    status: has(stored.status) ? stored.status : seed.status,
    statusNote: has(stored.statusNote) ? stored.statusNote : seed.statusNote,
    source: has(stored.source) ? stored.source : seed.source,
  }
}

function mergeVoices(storedList: VoiceAsset[] | undefined): VoiceAsset[] {
  const kept = (storedList ?? []).filter(
    (v) =>
      !REMOVED_VOICE_IDS.has(v.id) &&
      !(OLD_VOICE_IDS.has(v.id) && OLD_VOICE_PATHS.has(v.filePath)),
  )
  const byName = new Map<string, VoiceAsset>()
  for (const v of kept) {
    if (v?.name) byName.set(v.name.trim(), v)
  }
  const out: VoiceAsset[] = []
  const seen = new Set<string>()
  for (const seed of SEED_VOICES) {
    const k = (seed.name ?? '').trim()
    if (!k || seen.has(k)) continue
    seen.add(k)
    const stored = byName.get(k)
    out.push(stored ? backfillVoice(stored, seed) : seed)
  }
  for (const v of kept) {
    const k = (v?.name ?? '').trim()
    if (!k || seen.has(k)) continue
    seen.add(k)
    out.push(v)
  }
  return out
}

function load(): AssetStore {
  /* 策略：每次读取都先按"种子 + 用户数据"走一次 mergeWithSeed
   * 这样无论 localStorage 里 image 字段是什么状态（包括 v3 中旧的 null），
   * 也会强制用种子的最新值回填空字段（保留用户非空编辑）。
   * 副作用：用户故意"清空的 image=null"会被回填成种子 webp 路径——
   * 因为空 null 和"未填 null"无法区分，倾向后者（种子优先）。 */

  // 1) 收集已有数据：v3 → v2 → v1（任一存在就用）
  const fromKeys: PresetStyle[] = []
  let customsFromKeys: CustomStyle[] | undefined
  let voicesFromKeys: VoiceAsset[] | undefined
  let hadV3 = false
  for (const k of [KEY_V3, KEY_V2, KEY_V1]) {
    let raw: string | null = null
    try {
      raw = localStorage.getItem(k)
    } catch {
      raw = null
    }
    if (!raw) continue
    try {
      const parsed = JSON.parse(raw) as Partial<AssetStore>
      if (Array.isArray(parsed.presets)) {
        if (k === KEY_V3) hadV3 = true
        fromKeys.push(...parsed.presets)
      }
      if (Array.isArray(parsed.customs) && !customsFromKeys) customsFromKeys = parsed.customs
      if (Array.isArray(parsed.voices) && !voicesFromKeys) voicesFromKeys = parsed.voices
    } catch {
      /* 单 key 解析失败不影响其它 */
    }
  }

  // 2) 用种子对齐回填（用户编辑过的字段保留；空字段拉新）
  const presets = mergeWithSeed(uniqByName(fromKeys))
  const voices = mergeVoices(voicesFromKeys)

  // 3) 把回填结果写回 v3（让单条 image=null 的旧条目被纠正）
  try {
    localStorage.setItem(
      KEY_V3,
      JSON.stringify({
        presets,
        customs: customsFromKeys ?? SEED_CUSTOMS,
        voices,
      }),
    )
  } catch {
    /* 容量超限等忽略 */
  }

  // 仅在用户从 v1/v2 升级首次进入 v3 时提示一次
  if (!hadV3 && typeof console !== 'undefined') {
    // eslint-disable-next-line no-console
    console.info('[assetStore] 已从 v1/v2 升级到 v3；种子预设已合并')
  }

  return {
    presets,
    customs: customsFromKeys ?? SEED_CUSTOMS,
    voices,
  }
}

let _seq = 0
function uid(prefix: string): string {
  _seq += 1
  return `${prefix}-${Date.now().toString(36)}-${_seq}`
}

export function useAssetStore() {
  const init = useRef(load())
  const [presets, setPresets] = useState<PresetStyle[]>(init.current.presets)
  const [customs, setCustoms] = useState<CustomStyle[]>(init.current.customs)
  const [voices, setVoices] = useState<VoiceAsset[]>(init.current.voices)

  useEffect(() => {
    try {
      localStorage.setItem(
        KEY_V3,
        JSON.stringify({ presets, customs, voices }),
      )
    } catch {
      /* 容量超限等忽略 */
    }
  }, [presets, customs, voices])

  return {
    presets,
    customs,
    voices,
    addPreset: (p: PresetStyle) => setPresets((s) => [...s, p]),
    updatePreset: (p: PresetStyle) => setPresets((s) => s.map((x) => (x.id === p.id ? p : x))),
    removePreset: (id: string) => setPresets((s) => s.filter((x) => x.id !== id)),

    addCustom: (c: CustomStyle) => setCustoms((s) => [...s, c]),
    updateCustom: (c: CustomStyle) => setCustoms((s) => s.map((x) => (x.id === c.id ? c : x))),
    removeCustom: (id: string) => setCustoms((s) => s.filter((x) => x.id !== id)),

    addVoice: (v: VoiceAsset) => setVoices((s) => [...s, v]),
    updateVoice: (v: VoiceAsset) => setVoices((s) => s.map((x) => (x.id === v.id ? v : x))),
    removeVoice: (id: string) => setVoices((s) => s.filter((x) => x.id !== id)),

    uid,
  }
}
