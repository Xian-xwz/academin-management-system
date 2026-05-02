# -*- coding: utf-8 -*-
"""
Dify 代码节点：知识卡片模板获取

输入（Dify 建议只接一个变量）：
- content：上游整段文本或 JSON 字符串。若为 JSON，优先读取字段「图片编号」或 image_number；
  否则按整段字符串解析编号（兼容 1～7、「图片1」、template_3 等）。

输出（单一变量，便于后续引用）：
- result：String，JSON 字符串，UTF-8。结构为：
  { "图片编号", "示例", "模板" }
  其中「模板」为 id/name/definition/style_rules/reference_prompt 的对象，与内容图节点的 template_info 形态一致。
"""
import json


LAYOUT_RULE = (
    "Layout containment: All illustrations, stickers, icons, small photos, and cutouts must remain fully inside "
    "the single layout section they are assigned to; do not cross section boundaries, bleed into adjacent sections, "
    "or overlap neighboring titles/body text. Do not use one image spanning multiple sections—large motifs must be "
    "shrunk to one section or split into small local icons. Layout labels, section names, percentages, guide lines, "
    "bounding boxes, or any layout instruction text must not be rendered in the final image. No platform logo, "
    "no Xiaohongshu watermark, no app corner mark, no @account handle, no signature, no creator credit, "
    "no footer brand strip."
)


TEMPLATES = {
    "1": {
        "template": {
            "id": "knowledge_card_framework_six_zone_v1",
            "name": "知识卡片-六段方法论信息图",
            "definition": "可爱手绘教育信息图：浅奶油格纸背景 + 纵向六段式布局，依次呈现标题/定义/多卡片展开/关系图/步骤流/小总结，适合框架、模型、方法论类知识点。",
            "style_rules": (
                "Cute hand-drawn educational infographic on a light cream grid paper background. Soft pastel palette: "
                "mint green, pale yellow, soft pink. Vertical six-section structure with bold title, small diagram, "
                "definition box, multiple pastel cards, central logic diagram, horizontal process flow, checklist and "
                "summary box. Stationery decoration, dotted arrows, paper texture, subtle shadows, warm organized "
                "atmosphere. No platform logo, no watermark, no @handle, no signature. Do not render layout labels, "
                "section names, or percentages."
            ),
            "reference_prompt": (
                "Format: Vertical 3:4 social media knowledge card. Cute hand-drawn educational infographic on a "
                "light cream grid paper background. Use the six-section structure shown in the example. Layout "
                "containment and no-watermark rules must be preserved. (此处填入上方完整提示词)"
            ),
        },
        "example": """Format: Vertical 3:4 social media knowledge card.

Style & Vibe:
Cute hand-drawn educational infographic on a light cream grid paper background. Soft pastel colors (mint green, pale yellow, soft pink).

Composition Structure:
Area 1 (Top 15%): Large bold hand-drawn title '麦肯锡金字塔原理' with a 4-layer pyramid diagram on the right and a lightbulb icon on the left.
Area 2 (15-30%): A rounded green border box titled '01 什么是金字塔原理?' containing bullet points and 4 small illustrated icons.
Area 3 (30-50%): Four vertical cards (A, B, C, D) in different pastel colors, each with a title, description, and a tiny icon.
Area 4 (50-70%): A logic flow section with a central tree diagram and two blue text boxes on the sides labeled '纵向逻辑' and '横向逻辑'.
Area 5 (70-85%): A 4-step horizontal process flow with numbered circles and connecting arrows.
Area 6 (Bottom 15%): A summary section with a checklist on the left and a highlighted '小总结' box on the right with a heart sticker.

{layout_rule}

Visual Elements Assembly:
1. Decorative elements: Washi tape textures, paper clips, hand-drawn stars, and small plants.
2. Lines: Dotted lines and hand-drawn arrows for flow.

Details & Texture:
Paper texture background, subtle drop shadows on cards, ink-pen stroke feel, warm and organized atmosphere.""",
    },
    "2": {
        "template": {
            "id": "knowledge_card_humanities_scrapbook_v1",
            "name": "知识卡片-人文剪贴簿",
            "definition": "手账剪贴簿式教育信息图：奶油格纸背景、活页螺旋、胶带与回形针，采用左侧大笔记区、右侧情感/脉络流线、底部特色与总结卡片，适合文学、历史人物、作品赏析等人文叙事类知识点。",
            "style_rules": (
                "Creative hand-drawn educational infographic, scrapbook style on cream grid paper. Warm academic but "
                "approachable. Asymmetric five-section layout: title, spiral notebook section, flowing narrative "
                "section, checklist box, summary sticky note. Washi tape, spiral rings, metal paper clips, thematic "
                "doodles. Fine ink lines, watercolor fills, paper texture. No platform logo, no watermark, no "
                "@handle, no signature. Do not render layout labels, section names, or percentages."
            ),
            "reference_prompt": (
                "Format: Vertical 3:4 social media knowledge card. Hand-drawn scrapbook layout on cream grid paper "
                "for humanities or narrative knowledge. Layout containment and no-watermark rules must be preserved. "
                "(此处填入上方完整提示词)"
            ),
        },
        "example": """Format: Vertical 3:4 social media knowledge card.

Style & Vibe:
Creative hand-drawn educational infographic, scrapbook style on cream grid paper. Warm and academic yet approachable.

Composition Structure:
Area 1 (Top 15%): Large bold title '月是故乡明：苏轼的中秋独白' with decorative washi tape and music note icons.
Area 2 (Left Middle 45%): A large section styled like a spiral notebook page titled '创作背景', containing bullet points and small character doodles.
Area 3 (Right Middle 40%): A flowing section titled '情感脉络' with a curved arrow path and small illustrative icons.
Area 4 (Bottom Left 40%): A checklist-style box titled '艺术特色' with hand-drawn icons.
Area 5 (Bottom Right 40%): A summary card titled '总结卡片' held by a heart-shaped paper clip.

{layout_rule}

Visual Elements Assembly:
1. Decorative elements: Washi tape at corners, spiral rings on the left, metal paper clips.
2. Small hand-drawn icons: moon, stars, ancient characters, and simple maps.

Details & Texture:
Fine ink lines, watercolor-style fills, paper texture background, high legibility.""",
    },
    "3": {
        "template": {
            "id": "knowledge_card_timeline_journal_v1",
            "name": "知识卡片-阶段沿革手帐",
            "definition": "手帐分篇式教育信息图：米绿点阵纸背景，顶部标题卡片，中部按起源/发展拆分，底部用进阶图谱或隐喻插图收束，适合制度沿革、历史专题、时间线清晰的知识点。",
            "style_rules": (
                "Cute hand-drawn educational infographic, journaling style with soft beige and mint green tones. "
                "Clean organized scrapbook on dot-grid paper. Four-section structure: main title in rounded rectangle, "
                "origin section, split development section with flow arrows, bottom summary/process block with metaphor "
                "illustration. Washi tape, paperclips, simple historical icons, clean hierarchy. No platform logo, "
                "no watermark, no @handle, no signature. Do not render layout labels, section names, or percentages."
            ),
            "reference_prompt": (
                "Format: Vertical 3:4 social media knowledge card. Journaling-style staged timeline layout for "
                "historical evolution or system development knowledge. Layout containment and no-watermark rules must "
                "be preserved. (此处填入上方完整提示词)"
            ),
        },
        "example": """Format: Vertical 3:4 social media knowledge card.

Style & Vibe:
Cute hand-drawn educational infographic, journaling style with soft beige and mint green tones. The overall look is a clean, organized scrapbook on a dot-grid paper background.

Composition Structure:
Area 1 (Top 15%): Main title '千年选官路' in a large white rounded rectangle with a green dashed border, decorated with washi tape at the corners.
Area 2 (Upper Middle 25%): A horizontal block titled '起源篇' with a paperclip icon. Bullet points on the left describe the Sui Dynasty, and cute cartoon officials are illustrated on the right.
Area 3 (Center 30%): A split section for '发展篇'. Left side covers Tang Dynasty with a small desk icon; right side covers Song Dynasty with a clock and map icon, connected by a flow arrow.
Area 4 (Bottom 30%): A large final section titled '进阶图谱'. It features a numbered list (1-5) on the left and a visual metaphor of a scholar climbing a staircase toward a 'Golden List' (Jinbang) on the right.

{layout_rule}

Visual Elements Assembly:
1. Decorative elements: Colorful washi tape, metal paperclips, small flowers, and music notes scattered around.
2. Background: Pale cream paper with a subtle light gray dot grid.
3. Icons: Hand-drawn scrolls, ink brushes, cages, and traditional Chinese architecture.

Details & Texture:
Soft watercolor textures, clean ink outlines for characters, highly organized layout with clear hierarchy.""",
    },
    "4": {
        "template": {
            "id": "knowledge_card_science_formula_v1",
            "name": "知识卡片-理科公式手账",
            "definition": "理科手账式教育信息图：奶油点阵背景、顶部标题、左侧公式/定义框、右侧三概念气泡、底部应用情景与注意事项，适合公式、定律、三要素关系和易错点讲解。",
            "style_rules": (
                "Educational infographic in a cute hand-drawn notebook style. Cream dot-grid background, pastel "
                "accents in yellow, green and pink. Five-section structure: centered title, theory/formula frame, "
                "three circular concept bubbles, practical scenario panels, notes section with sticky note. Washi tape, "
                "paper clips, sparkles, clean handwritten-style typography. No platform logo, no watermark, no @handle, "
                "no signature. Do not render layout labels, section names, or percentages."
            ),
            "reference_prompt": (
                "Format: Vertical 3:4 social media knowledge card. Hand-drawn bullet journal layout for science "
                "formulas, laws, variables, applications and common mistakes. Layout containment and no-watermark "
                "rules must be preserved. (此处填入上方完整提示词)"
            ),
        },
        "example": """Format: Vertical 3:4 social media knowledge card.

Style & Vibe:
Educational infographic in a cute hand-drawn notebook style. Cream background with a subtle dot grid. Soft pastel accents in yellow, green, and pink.

Composition Structure:
Area 1 (Top 15%): Large bold title '牛顿第二定律' centered, with a quote underneath flanked by cute apple icons.
Area 2 (Mid-Left 35%): A spiral notebook box containing the formula 'F=ma' and definitions.
Area 3 (Mid-Right 35%): Three circular bubbles (green, purple, pink) representing Force, Mass, and Acceleration with cute animal icons (elephant, rabbit).
Area 4 (Bottom-Left 40%): Two horizontal panels showing 'Shopping Cart' scenarios with simple line-art illustrations.
Area 5 (Bottom-Right 40%): A 'Precautions' list with small icons and a 'Key Takeaways' sticky note held by paper clips.

{layout_rule}

Visual Elements Assembly:
1. Decorative elements: Washi tape, paper clips, music notes, and sparkles.
2. Handwritten-style typography for body text.

Details & Texture:
Fine liner ink texture, matte paper feel, clean white borders around text boxes.""",
    },
    "5": {
        "template": {
            "id": "knowledge_card_ai_workflow_storyboard_v1",
            "name": "知识卡片-AI工具工作流手绘海报",
            "definition": "手绘创意工作流海报：格纸背景 + 角色主视觉 + 多面板流程 + 箭头连接 + 图标化产出矩阵，适合 AI 工具、软件能力、研究创作流程、项目工作流等全链路知识点。",
            "style_rules": (
                "Hand-drawn creative notebook style on beige grid paper. Cozy educational workflow poster. "
                "Character-led multi-panel layout: title and subtitles, hero researcher character with floating idea "
                "bubbles, middle process panels, bottom automation flowchart and output cards. Warm earthy palette, "
                "washi tape corners, dashed arrows, document icons, screens, gears, rocket, coffee cups and small "
                "stationery details. No platform logo, no watermark, no @handle, no signature. Do not render layout "
                "labels, section names, or percentages."
            ),
            "reference_prompt": (
                "Format: Vertical 3:4 social media knowledge card. Hand-drawn creative workflow storyboard for AI "
                "tools, software abilities, research process or project pipeline. Layout containment and no-watermark "
                "rules must be preserved. (此处填入上方完整提示词)"
            ),
        },
        "example": """Format: Vertical 3:4 social media knowledge card.

Style & Vibe:
Hand-drawn creative notebook style, cozy and educational. Muted earthy tones with a beige grid paper background. The layout feels like an illustrated research and creation workflow board.

Composition Structure:
Area 1 (Top Left): Large bold title 'Nano Banana Pro' with short descriptive subtitles such as all-in-one creative and research companion.
Area 2 (Top Right): A cute girl with glasses holding a tablet, surrounded by floating speech bubbles containing keywords like 'Manga', 'Research', 'Poster', 'Notes', and 'Sketches'.
Area 3 (Middle): Three process panels showing brainstorming, structuring, and visual creation. Panels are connected by hand-drawn arrows and dashed lines, with small document, JSON, flowchart, and screen icons.
Area 4 (Bottom): A workflow automation flowchart with icons of a rocket, document, gears, book, poster, and digital screens, ending with an excited character and several output cards.

{layout_rule}

Visual Elements Assembly:
1. Background: Cream-colored graph paper with realistic washi tape at the corners.
2. Decorative elements: Coffee cups, small stars, potted plants, document sheets, dashed arrows, and small hand-drawn tech icons.
3. Character consistency: The same cute researcher character appears across panels, wearing glasses and a cozy sweater.

Details & Texture:
Warm paper texture, hand-drawn ink outlines, soft watercolor fills, tidy multi-panel hierarchy, clear readable typography.""",
    },
    "6": {
        "template": {
            "id": "knowledge_card_vintage_science_encyclopedia_v1",
            "name": "知识卡片-复古科学百科图鉴",
            "definition": "复古科学百科图鉴：旧纸质感 + 墨线水彩 + 主体大插图 + 局部放大镜 + 生命周期/分布/状态/尺寸对比面板，适合生物、地理、自然科学与物种百科类知识点。",
            "style_rules": (
                "Vintage scientific encyclopedia illustration. Hand-drawn ink lines with soft watercolor washes on "
                "aged parchment paper. Muted indigo, teal, and earthy brown palette. Large primary subject "
                "illustration, circular detail insets, magnifying glass annotations, side process flow, bottom data "
                "panels for map/status/size comparison. Coffee stains, paper creases, stippling, fine linework. "
                "No platform logo, no watermark, no @handle, no signature. Do not render layout labels, section "
                "names, or percentages."
            ),
            "reference_prompt": (
                "Format: Vertical 3:4 social media knowledge card. Vintage encyclopedia page for biology, geography, "
                "natural science or species explanation. Layout containment and no-watermark rules must be preserved. "
                "(此处填入上方完整提示词)"
            ),
        },
        "example": """Format: Vertical 3:4 social media knowledge card.

Style & Vibe:
Vintage scientific encyclopedia illustration. Hand-drawn ink lines with soft watercolor washes. Muted tones of indigo, teal, and earthy brown on stained, aged parchment paper.

Composition Structure:
Area 1 (Top Center): Bold black calligraphy title '鲸鲨' with decorative flourishes.
Area 2 (Center Left): A large whale shark swimming diagonally, showing its spotted skin pattern.
Area 3 (Center Circular Inset): A large circular view showing the shark's open mouth filtering plankton.
Area 4 (Right Column): A vertical flow of circular icons showing life cycle or growth stages.
Area 5 (Bottom Row): Three horizontal panels containing a world distribution map, conservation status badge, and size comparison chart.

{layout_rule}

Visual Elements Assembly:
1. Multiple magnifying glass insets showing skin textures, gill structures, or anatomical details.
2. Thin black arrows pointing from details to annotations.
3. A small skeletal or structure diagram in a lower corner.

Details & Texture:
Coffee stains, paper creases, stippling shading, fine line work, handwritten-style Chinese annotations, aged encyclopedia page atmosphere.""",
    },
    "7": {
        "template": {
            "id": "knowledge_card_doodle_mindmap_v1",
            "name": "知识卡片-涂鸦思维导图",
            "definition": "彩铅涂鸦思维导图：白纸背景 + 中心主物体 + 四向有机分支 + 小图标与人物互动，适合概念网络、提示词工程、学习策略、工具使用指南等中心主题向多分支展开的知识点。",
            "style_rules": (
                "Friendly hand-drawn doodle infographic on clean white paper. Soft colored pencil strokes and crayon-like "
                "textures. Central hero object or mascot as hub, four organic colored branches extending to quadrants, "
                "thematic icons, small characters, arrows, dotted lines, stars, leaves and hearts. Playful educational "
                "mind map, clear handwritten labels, high readability. No platform logo, no watermark, no @handle, "
                "no signature. Do not render layout labels, section names, or percentages."
            ),
            "reference_prompt": (
                "Format: Vertical 3:4 social media knowledge card. Hand-drawn doodle mind map for concept networks, "
                "prompt engineering, learning strategies, or tool guides. Layout containment and no-watermark rules "
                "must be preserved. (此处填入上方完整提示词)"
            ),
        },
        "example": """Format: Vertical 3:4 social media knowledge card.

Style & Vibe:
Friendly hand-drawn doodle infographic. Soft colored pencil strokes and crayon-like textures on a clean white paper background. Playful and educational vibe.

Composition Structure:
Area 1 (Top 15%): Main title 'Gemini 3' in large blue bubbly font, followed by black subtitle '提示词工程指南', flanked by a cute lightbulb and exclamation mark icon.
Area 2 (Center 20%): A cute small silver robot with a friendly face, acting as the central hub.
Area 3 (Mid-Section): Four thick organic branches in blue, orange, red, and green extending from the robot to the four corners, creating a mind map structure.
Area 4 (Peripheral): Various small icons such as magnifying glass, books, charts, lightbulbs, and small human characters interacting with tech, placed along the branches with descriptive text.

{layout_rule}

Visual Elements Assembly:
1. Hand-drawn arrows and dotted lines showing flow.
2. Small decorative elements like stars, leaves, and hearts scattered throughout.
3. Text labels next to each branch node in a clean handwritten-style font.

Details & Texture:
Visible pencil shading, slightly irregular lines for a human touch, high-resolution scan of a drawing, clean and organized layout.""",
    },
}


def _normalize_image_number(value):
    """把图片编号统一成 1～7 字符串。"""
    if value is None:
        return "1"
    text = str(value).strip()
    if not text:
        return "1"
    for token in ("图片", "template_", "template", "图", "#"):
        text = text.replace(token, "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits or "1"


def _extract_number_from_content(raw):
    """
    从 content 解析出用于规范化的编号来源。
    - dict：取「图片编号」或 image_number
    - str：尝试 json.loads；成功且为 dict 则同上，否则整串交给 _normalize_image_number
    """
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw.get("图片编号", raw.get("image_number"))
    s = str(raw).strip()
    if not s:
        return None
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj.get("图片编号", obj.get("image_number"))
        return obj
    except (json.JSONDecodeError, TypeError, ValueError):
        return s


def _format_example(raw):
    return raw.format(layout_rule=LAYOUT_RULE)


def main(content=None, 图片编号=None, image_id=None):
    """
    根据 content（或兼容旧入参 图片编号 / image_id）返回单一 result（JSON 字符串）。
    与内容图节点类似：示例 + 模板信息合并在一个对象里，便于 Dify 只声明一个 String 输出。
    """
    raw = content
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raw = 图片编号 if 图片编号 is not None else image_id

    extracted = _extract_number_from_content(raw)
    number = _normalize_image_number(extracted)

    if number not in TEMPLATES:
        number = "1"

    entry = TEMPLATES[number]
    # 与内容图 to_out 中 template_info 一致：扁平模板字段，不含 cover_config 拆分
    template_obj = dict(entry["template"])
    example_text = _format_example(entry["example"])

    payload = {
        "图片编号": number,
        "示例": example_text,
        "模板": template_obj,
    }
    return {"result": json.dumps(payload, ensure_ascii=False)}
