"""Seed Style Presets — 从 server.py STYLE_PRESETS 迁移到资产目录。

一次性迁移脚本，将硬编码的风格预设写入 assets/styles/templates.json。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 预设风格数据（从 webapp/server.py STYLE_PRESETS 提取）
STYLE_PRESETS = {
    "国风动态信息图": (
        "暖米白宣纸背景，深灰正文与朱红重点，低饱和靛青辅助色；"
        "固定总标题和章节标题，以知识卡片、关系线、时间轴、层级或对比结构组织观点，"
        "搭配克制的国风淡彩插画，大量留白，成人知识内容，禁止摄影写实和儿童卡通。"
    ),
    "极简粗线简笔白板风": (
        "暖白色纯净背景，圆润有亲和力的粗黑马克笔轮廓，人物和物体高度概括，"
        "只使用橙色与钴蓝色做少量平涂点缀；几乎没有阴影、纹理和细碎结构，留白充足，"
        "像现场快速画出的清爽白板简笔画。"
    ),
    "极简商务涂鸦风": (
        "冷白至极浅灰背景，深海军蓝的精准几何轮廓，钴蓝与青绿色作为强调色；"
        "用整齐的卡片、流程箭头、图表和图标组织信息，线条克制利落、间距规整，"
        "呈现专业的商业演示和科技产品解说感，禁止暖黄纸张与随意手绘笔触。"
    ),
    "暖米黄素描白板风": (
        "温暖米黄色纸张底色，真实石墨铅笔线条，轻柔排线、交叉线和深浅笔压，"
        "辅以低饱和赭石色与灰蓝色；保留手工速写的纸张颗粒和结构细节，"
        "像一本质感细腻的编辑手账，不能画成粗线扁平图标。"
    ),
    "粗线扁平国风卡通": (
        "温暖宣纸色背景，深棕色粗轮廓，朱红、玉绿与靛青的饱和平涂色块；"
        "人物比例生动简化，少量使用祥云、笔触和中式构图节奏，"
        "形成现代国风科普动画效果，禁止写实素描和欧美商务信息图观感。"
    ),
    "爆款高热吸睛风": (
        "明亮黄色高能背景，超粗黑色外轮廓，热烈橙红与电光钴蓝的大色块，"
        "夸张但友好的人物表情和动作，配合放射爆炸形、速度线与强烈斜向构图；"
        "主体要大、对比要强、第一眼就能看懂，具有热门短视频封面般的冲击力，"
        "但保持轮廓干净，不能堆满琐碎元素。"
    ),
    "黑金科技发布会风": (
        "深黑与炭灰背景，金属金色作为主轮廓和高光，少量电光青色点缀；"
        "使用精致的环形界面、几何数据结构和舞台式光影，主体高级、权威、科技感强，"
        "像高端科技产品发布会，禁止暖白纸张和可爱手绘效果。"
    ),
    "清新治愈手账风": (
        "奶油白纸张背景，圆润轻柔的手绘线条，鼠尾草绿、蜜桃粉、奶油黄和天蓝色的低饱和水彩；"
        "少量加入胶带、贴纸与植物点缀，整体通透、温暖、治愈、生活化，"
        "保持留白，禁止强烈黑线和高对比商务图表。"
    ),
    "复古报纸拼贴风": (
        "暖灰新闻纸底色，黑色油墨主体、复古红色强调块、半色调网点、丝网印刷颗粒与撕纸边缘；"
        "人物和物体像剪下后重新拼贴的编辑视觉，层次大胆、粗粝、有文化杂志感，"
        "禁止光滑渐变和现代扁平信息图。"
    ),
    "纸感隐喻拼贴风": (
        "暖米白手工纸背景，清晰纸纤维、撕边、轻微褶皱与手工裁切痕迹；人物和物体由剪纸拼贴叠层构成，"
        "带柔和浅浮雕投影，成人卡通比例、圆白眼与小黑瞳、细线鼻口。主色仅使用米杏、炭黑、深灰、暖灰、"
        "珊瑚红和灰粉，金黄只用于希望、价值或关键转折。每张图只选择定义、流程、对比、层级、因果、清单、"
        "时间或矩阵中的一个主结构，用单一具体隐喻表达观点；留白占 25%–45%，主视觉不超过 3 组，辅助符号不超过 5 类。"
        "禁止摄影写实、光滑塑料 3D、扁平矢量图标、儿童贴纸、霓虹科技 UI、文字、Logo、水印和图标堆砌。"
    ),
    "漫画墨线解释风": (
        "暖灰米白纸张背景，使用自信、粗细有变化的黑色漫画墨线；灰面和阴影只用经典圆点半色调，不用柔和渐变。"
        "黑白灰为主体，固定暖黄色只用于边牧或关键物件，每张图最多再使用两种低饱和语义色：蓝色表示输入或内容，"
        "橙色表示行动、警告或成本，紫色表示过程，绿色表示成功或完成。关系必须用具体物件、路径、状态变化和重复材料证明，"
        "不能靠装饰图标凑数。原文需要通用角色时才使用戴细圆框眼镜的圆头极简线人，胖胖的暖黄边牧只作合适的陪伴角色；"
        "抽象机制页优先画物件和状态，不强塞人物。禁止 3D、摄影写实、光滑渐变、通用卡片网格、仪表盘、杂乱装饰、Logo 和水印。"
    ),
    "3D黏土趣味风": (
        "可爱的三维黏土动画场景，圆润玩具化比例，可见细微手作指纹，"
        "珊瑚橙、青绿色、亮黄色和奶油色的柔和配色，温暖棚拍光与轻柔投影，"
        "像精致的定格动画小剧场，主体清楚，禁止二维线稿和写实摄影材质。"
    ),
    "赛博霓虹漫画风": (
        "深靛蓝至黑色背景，青色与洋红色霓虹边缘光，紫色渐变和粗黑漫画轮廓；"
        "加入克制的速度线、全息几何形与未来创作者工作室氛围，构图动感、戏剧性强，"
        "同时确保人物面部和关键物体清楚可读。"
    ),
}


def seed(data_dir: Path) -> dict:
    """将 STYLE_PRESETS 写入 assets/styles/templates.json。"""
    styles_dir = data_dir / "assets" / "styles"
    styles_dir.mkdir(parents=True, exist_ok=True)
    templates_path = styles_dir / "templates.json"

    # 读取现有模板
    existing = []
    if templates_path.exists():
        try:
            existing = json.loads(templates_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []

    # 检查是否已有 seed 数据
    existing_ids = {t.get("template_id") for t in existing}
    seed_ids = {f"seed-{i:03d}" for i in range(len(STYLE_PRESETS))}
    if existing_ids & seed_ids:
        return {"ok": True, "message": "seed 数据已存在，跳过", "count": 0}

    # 生成 seed 模板
    now = "2026-08-31T00:00:00Z"
    templates = []
    for i, (name, prompt) in enumerate(STYLE_PRESETS.items()):
        templates.append({
            "template_id": f"seed-{i:03d}",
            "revision": 1,
            "name": name,
            "kind": "preset",
            "prompt_text": prompt,
            "negative_prompt": "",
            "reference_images": [],
            "tags": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })

    # 合并写入
    all_templates = existing + templates
    templates_path.write_text(
        json.dumps(all_templates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {"ok": True, "message": "seed 完成", "count": len(templates)}


def main() -> int:
    data_dir = ROOT / ".webapp"
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    result = seed(data_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
