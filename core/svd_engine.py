import json
import os
import logging
import re
from typing import Dict, List, Any
from openai import OpenAI
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class SVGEngine:
    # 🎨 典型的 AI 学术海报配色方案 (极简蓝灰风，作为终极兜底)
    ACADEMIC_DESIGN_SYSTEM = {
        "background": "#FFFFFF",
        "primary_box_fill": "#E8F4FD",
        "secondary_box_fill": "#F4F6F8",
        "table_header_fill": "#EBF0F5",
        "text_color": "#1A202C",
        # ⭐ 优化1：升级学术字体栈，更现代、更专业
        "heading_font": "'Inter', 'Roboto', 'Helvetica Neue', Arial, sans-serif",
        "body_font": "'Inter', 'Roboto', 'Helvetica Neue', Arial, sans-serif",
    }
    def __init__(self, api_key: str, width: int = 1200, height: int = 900):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.width = width
        self.height = height
        self.scale = 1000
        # ✅ icon cache
        self.icon_cache = {}
        # ✅ 设计系统缓存 (全局生效)
        self.design_system = None
        # ⭐ 优化2：新增语义颜色缓存，用于散点图精准映射
        self.semantic_colors = {}
    # =========================
    # 🚨 稳定 JSON 解析 (供 LLM 设计系统使用)
    # =========================
    def _extract_json(self, text: str) -> Dict[str, Any]:
        stack = []
        start = None
        for i, ch in enumerate(text):
            if ch == '{':
                if start is None:
                    start = i
                stack.append(ch)
            elif ch == '}':
                if stack:
                    stack.pop()
                    if not stack:
                        try:
                            return json.loads(text[start:i+1])
                        except Exception:
                            continue
        if start is not None:
            partial = text[start:]
            missing = partial.count('{') - partial.count('}')
            if missing > 0:
                repaired = partial + ('}' * missing)
                try:
                    return json.loads(repaired)
                except Exception:
                    pass
        raise ValueError(f"设计系统 JSON 解析失败。原始输出: {text[:200]}")
    # =========================
    # 🎨 生成全局设计系统 (⭐ 优化3：弃用 LLM 幻觉，改为深度提取 JSON 原生色彩)
    # =========================
    def _generate_design_system(self, topic: str = "Technology", base_colors: List[str] = []) -> Dict:
        if self.design_system:
            return self.design_system
        # 不再依赖 LLM 生成不可控的配色，直接基于 JSON 原生颜色推导
        ds = self.ACADEMIC_DESIGN_SYSTEM.copy()
        # 智能提取背景和主色调
        valid_colors = [c for c in base_colors if c and c.startswith("#")]
        if valid_colors:
            # 寻找最浅的颜色作为背景色（如果不是纯白）
            light_colors = [c for c in valid_colors if self._color_luminance(c) > 0.9]
            if light_colors:
                ds["background"] = "#FFFFFF" # 保持纯白背景最安全
            # 寻找偏蓝/偏青的作为 primary_box_fill
            blue_ish = [c for c in valid_colors if self._is_blue_ish(c)]
            if blue_ish:
                ds["primary_box_fill"] = blue_ish[0]
            # 寻找偏灰的作为 secondary_box_fill
            gray_ish = [c for c in valid_colors if not self._is_blue_ish(c) and self._color_luminance(c) > 0.8]
            if gray_ish:
                ds["secondary_box_fill"] = gray_ish[0]
            # 表头颜色基于主色变暗
            ds["table_header_fill"] = self._darken_color(ds["primary_box_fill"], 0.92)
        self.design_system = ds
        logger.info(f"✅ 生成还原型设计系统 (基于JSON提取): {self.design_system}")
        return self.design_system
    # ⭐ 新增辅助：计算颜色亮度
    def _color_luminance(self, hex_color: str) -> float:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return 0.5
        r, g, b = int(hex_color[0:2], 16)/255.0, int(hex_color[2:4], 16)/255.0, int(hex_color[4:6], 16)/255.0
        return 0.299 * r + 0.587 * g + 0.114 * b
    # ⭐ 新增辅助：判断是否为蓝色系
    def _is_blue_ish(self, hex_color: str) -> bool:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return False
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return b > r and b > g
    # ⭐ 优化4：从 Chart 的 Label 中精准提取语义颜色映射
    def _extract_semantic_colors_from_chart(self, el):
        label = el.get("label", "")
        # 匹配类似 "Blue: Supervised methods, Orange: RL methods" 的模式
        matches = re.findall(r'(Blue|Red|Green|Orange|Purple|Yellow|Cyan|Magenta)\s*:\s*([A-Za-z\s]+?)(?:,\s*\w+:|$)', label, re.IGNORECASE)
        color_map = {
            "blue": "#3B82F6", "red": "#EF4444", "green": "#10B981", 
            "orange": "#F59E0B", "purple": "#8B5CF6", "yellow": "#EAB308", 
            "cyan": "#06B6D4", "magenta": "#EC4899"
        }
        for color_name, methods_str in matches:
            c_hex = color_map.get(color_name.lower())
            if not c_hex: continue
            # 提取方法名 (如 Supervised methods -> SFT, RL methods -> RLHF/GRPO)
            methods_lower = methods_str.lower()
            if "supervised" in methods_lower or "sft" in methods_lower:
                self.semantic_colors["SFT"] = c_hex
            if "rl" in methods_lower or "reinforcement" in methods_lower:
                self.semantic_colors["RLHF"] = c_hex
                self.semantic_colors["GRPO"] = c_hex
            if "distillation" in methods_lower or "opd" in methods_lower:
                self.semantic_colors["OPD"] = c_hex
            if "preference" in methods_lower or "dpo" in methods_lower:
                self.semantic_colors["DPO"] = c_hex
    # =========================
    # 🧠 语义排版：LLM 智能换行 (物理预判防切断)
    # =========================
    def _refine_text_wrapping(self, text: str, width: int, height: int, default_size: int = 12) -> str:
        if not text:
            return text
        # ✅ 核心修复1：物理预判。如果文本原本就不超宽，坚决不换行！
        estimated_single_line_width = len(text) * default_size * 0.65
        safe_width = width * 0.85 # 留出 15% 的边距
        if estimated_single_line_width <= safe_width:
            return text # 物理上放得下，不需要 LLM 切分
        # 如果已经有合理的换行，也不需要重新切分
        if text.count("\n") > 0:
            longest_line = max(text.split("\n"), key=len)
            if len(longest_line) * default_size * 0.65 <= safe_width:
                return text
        # ✅ 核心修复2：修改 Prompt，强调“克制换行”和“意群切分”
        prompt = f"""你是一个顶级的 SVG 排版专家。现在有一段文本需要在宽高比约为 {width/max(1,height):.1f} 的矩形框内显示。
由于单行文本过长会超出边界，必须进行换行切分。
请遵循以下原则：
1. **克制切分**：如果一句话或一个短语能在单行内显示，绝不要切断！
2. **意群切分**：在必须换行时，寻找最自然的语义停顿点（如逗号、标点符号、从句连接词之前，或意群之间）。
    - ✅ 好的切分：`Modern post-training methods mainly differ in` \n `reward modeling rather than optimization algorithms.`
    - ❌ 差的切分：`Modern post-training methods mainly differ in reward modeling` \n `rather than optimization algorithms.`
3. 仅输出切分后的文本，用 \\n 表示换行。
4. 不要修改、增删任何文字内容！
需要切分的文本：{text}"""
        try:
            response = self.client.chat.completions.create(
                model="qwen-max", 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            refined = response.choices[0].message.content.strip()
            # 去除 LLM 可能添加的多余引号
            if refined.startswith('"') and refined.endswith('"'):
                refined = refined[1:-1]
            return refined.replace("\\n", "\n")
        except Exception as e:
            logger.error(f"语义排版失败: {e}")
            return text
    # =========================
    # 📐 动态字号计算 (防溢出)
    # =========================
    def _calc_safe_font_size(self, text: str, box_width: float, default_size: int = 12) -> int:
        if not text:
            return default_size
        longest_line = max(text.split("\n"), key=len)
        safe_width = box_width * 0.85  
        estimated_width = len(longest_line) * default_size * 0.65
        if estimated_width > safe_width:
            return max(8, int(default_size * (safe_width / estimated_width)))
        return default_size
    def _scale_coord(self, coord: int, is_width: bool = True) -> float:
        base = self.width if is_width else self.height
        return (coord / self.scale) * base
    def _sanitize_svg(self, svg: str) -> str:
        svg = re.sub(r"<script.*?>.*?</script>", "", svg, flags=re.S | re.I)
        svg = re.sub(r" on\w+\s*=", " ", svg)
        svg = svg.replace("<?xml", "")
        return svg
    def _escape_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text
    # =========================
    # 🎯 核心文本渲染 (垂直居中修正 + 对齐分离)
    # =========================
    def _render_text(self, x: float, y: float, text: str,
                        font_size: int = 14, color: str = "#000000", 
                        alignment: str = "center", line_spacing: float = 1.3,
                        font_family: str = "Arial, sans-serif", 
                        font_weight: str = "normal") -> str:
        if not text:
            return ""
        # =========================
        # 🧠 数学公式智能识别与排版强化
        # =========================
        is_formula = False
        # ⭐ 优化5：扩充学术公式识别信号（增加 π, β, argmax, KL 等）
        formula_signals = r'[\^_]|π|β|α|γ|μ|σ|ω|∑|∫|∏|√|∞|→|≈|≤|≥|≠|∈|\bargmax\b|\bargmin\b|\b(max|min|log|exp|sin|cos|tan|lim|sup|inf)\b\s*[\(\^_\[]|KL\s*[\(\^_\[]'
        if re.search(formula_signals, text, re.IGNORECASE):
            is_formula = True
            font_family = "'Times New Roman', 'STIX Two Math', serif"
            font_style = "italic"
        else:
            font_style = "normal"
        lines = text.split("\n")
        safe_lines = [line for line in lines if line.strip()]
        if not safe_lines:
            return ""
        anchor = "middle" if alignment == "center" else ("end" if alignment == "right" else "start")
        line_height_px = font_size * line_spacing
        total_height = (len(safe_lines) - 1) * line_height_px
        start_y = y - total_height / 2 
        def parse_formula_line(line_str: str) -> str:
            """将包含上下标的文本转为精准偏移的SVG tspan组合"""
            parts = re.split(r'([a-zA-Z]\\?[\^_]\{.*?\}|[a-zA-Z]\\?[\^_][a-zA-Z0-9])', line_str)
            tspan_parts = []
            for part in parts:
                if not part: continue
                sup_sub_match = re.match(r'([a-zA-Z])\\?([\^_])\{?(.*?)\}?', part)
                if sup_sub_match and is_formula:
                    base_char = self._escape_text(sup_sub_match.group(1))
                    operator = sup_sub_match.group(2)
                    sub_content = self._escape_text(sup_sub_match.group(3))
                    sub_size = int(font_size * 0.65)
                    dy = f"-{font_size * 0.35}" if operator == '^' else f"{font_size * 0.15}"
                    tspan_parts.append(f'<tspan font-style="italic">{base_char}</tspan>')
                    is_num = sub_content.isdigit()
                    style_attr = "normal" if is_num else "italic"
                    tspan_parts.append(
                        f'<tspan dy="{dy}" font-size="{sub_size}" font-style="{style_attr}">{sub_content}</tspan>'
                    )
                    tspan_parts.append(f'<tspan dy="{-float(dy)}" font-size="{font_size}"></tspan>')
                else:
                    escaped_part = self._escape_text(part)
                    # 🎨 优化：公式行内的普通文本（如括号、等号、多字母算子）强制正体！
                    # 真正的变量斜体交给 base_char 那一层的 <tspan font-style="italic"> 去处理
                    tspan_parts.append(f'<tspan font-style="normal">{escaped_part}</tspan>')
            return "".join(tspan_parts)
        tspan_html = ""
        for i, line in enumerate(safe_lines):
            y_pos = start_y + i * line_height_px
            if is_formula:
                parsed_content = parse_formula_line(line)
                tspan_html += f'<tspan x="{x}" y="{y_pos}">{parsed_content}</tspan>'
            else:
                safe_content = self._escape_text(line)
                tspan_html += f'<tspan x="{x}" y="{y_pos}">{safe_content}</tspan>'
        return f'''
    <text x="{x}" y="{start_y}"
            font-family="{font_family}"
            font-size="{font_size}"
            font-weight="{font_weight}"
            fill="{color}"
            text-anchor="{anchor}"
            dominant-baseline="central">
        {tspan_html}
    </text>
    '''.strip()
    def _darken_color(self, hex_color: str, factor: float = 0.8) -> str:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = "".join([c*2 for c in hex_color])
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    # =========================
    # icon 生成
    # =========================
    def _generate_icon_element(self, element: Dict) -> str:
        instruction = element["style"].get("drawing_instruction", "")
        color = element["style"].get("fill_color", "#000000")
        label = element.get("label", "")
        key = f"{instruction}|||{color}|||{label}"
        if key in self.icon_cache:
            return self.icon_cache[key]
        prompt = f"""你是 SVG 专家。
请输出严格 SVG <g> 标签内容。
描述：{instruction}
主色调：{color}
文本：{label}
要求：
- 仅输出 <g>...</g>
- 不要 markdown
- 不要解释
- 100x100 坐标系
"""
        try:
            response = self.client.chat.completions.create(
                model="qwen-max",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            raw = response.choices[0].message.content.strip()
            raw = self._sanitize_svg(raw)
            self.icon_cache[key] = raw
            return raw
        except Exception as e:
            logger.error(f"icon生成失败: {e}")
            fallback = f'<circle cx="50" cy="50" r="40" fill="{color}" />' \
                        f'<text x="50" y="55" font-size="12" text-anchor="middle" fill="white">{label}</text>'
            return fallback
    # =========================
    # table 渲染
    # =========================
    def _render_table(self, el, xmin, ymin, w, h, svg_parts):
        structure = el.get("structure", {})
        raw_cells = structure.get("cells", [])
        rows, cols, cell_texts = 1, 1, []
        if isinstance(raw_cells, list) and raw_cells:
            if isinstance(raw_cells[0], list):
                rows = len(raw_cells)
                cols = max((len(row) for row in raw_cells), default=1)
                cell_texts = [str(item) for row in raw_cells for item in row]
            else:
                cols = max(1, int(structure.get("cols", 2) or 2))
                rows = max(1, -(-len(raw_cells) // cols)) 
                cell_texts = [str(c) for c in raw_cells]
        else:
            rows = max(1, int(structure.get("rows", 2) or 2))
            cols = max(1, int(structure.get("cols", 2) or 2))
        col_widths = []
        for c in range(cols):
            max_len = 0
            for r in range(rows):
                idx = r * cols + c
                if idx < len(cell_texts):
                    max_len = max(max_len, len(cell_texts[idx]))
            col_widths.append(max(0.15, max_len * 0.65))
        total_weight = sum(col_widths)
        col_widths_px = [(weight / total_weight) * w for weight in col_widths]
        header_height = min(35, h * 0.15)
        body_row_height = (h - header_height) / max(1, rows - 1) if rows > 1 else h
        header_fill = self.design_system.get("table_header_fill", "#F3F4F6")
        body_font = self.design_system.get("body_font", "Helvetica, sans-serif")
        HEADER_TEXT_COLOR = "#1A202C"
        BODY_TEXT_COLOR = "#333333"
        svg_parts.append(
            f'<rect x="{xmin}" y="{ymin}" width="{w}" height="{h}" '
            f'fill="none" stroke="#666" stroke-width="1.5"/>'
        )
        current_x = xmin
        for r in range(rows):
            current_x = xmin
            is_header = (r == 0)
            row_height = header_height if is_header else body_row_height
            y = ymin + (header_height if r > 0 else 0) + ((r - 1) * body_row_height if r > 0 else 0)
            for c in range(cols):
                cell_w = col_widths_px[c]
                fill_color = header_fill if is_header else "none"
                svg_parts.append(
                    f'<rect x="{current_x}" y="{y}" width="{cell_w}" height="{row_height}" '
                    f'fill="{fill_color}" stroke="#aaa" stroke-width="0.5"/>'
                )
                idx = r * cols + c
                if idx < len(cell_texts) and cell_texts[idx].strip():
                    safe_color = HEADER_TEXT_COLOR if is_header else BODY_TEXT_COLOR
                    font_weight = "bold" if is_header else "normal"
                    raw_text = cell_texts[idx]
                    safe_font_size = 11
                    max_chars = max(1, int((cell_w * 0.85) / (safe_font_size * 0.55)))
                    if len(raw_text) > max_chars:
                        words = raw_text.split(' ')
                        lines, current_line = [], ""
                        for word in words:
                            if len(current_line) + len(word) + 1 <= max_chars:
                                current_line = f"{current_line} {word}".strip()
                            else:
                                lines.append(current_line)
                                current_line = word
                        if current_line: lines.append(current_line)
                        wrapped_text = "\n".join(lines)
                    else:
                        wrapped_text = raw_text
                    svg_parts.append(
                        self._render_text(
                            current_x + cell_w / 2, y + row_height / 2, wrapped_text,
                            font_size=safe_font_size, alignment="center", 
                            color=safe_color, 
                            font_family=body_font,
                            font_weight=font_weight
                        )
                    )
                current_x += cell_w
    # =========================
    # 🚀 主渲染逻辑
    # =========================
    def create_svg(self, layout_data: Dict, output_path: str):
        elements = layout_data.get("elements", [])
        # 1. 收集原图的基色
        original_colors = [el.get("style", {}).get("fill_color", "") for el in elements if el.get("style", {}).get("fill_color")]
        # 2. 初始化设计系统 (结合原图基色，只调用一次)
        self._generate_design_system("Modern LLM Post-Training", base_colors=original_colors)
        ds = self.design_system
        # ⭐ 优化6：提前扫描散点图，提取语义颜色
        for el in elements:
            if el.get("type") == "coordinate_chart":
                self._extract_semantic_colors_from_chart(el)
        svg_parts = [
            f'<svg width="{self.width}" height="{self.height}" xmlns="http://www.w3.org/2000/svg">',
            f'<rect width="100%" height="100%" fill="{ds["background"]}"/>',
            '''<defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7"
                        refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#666"/>
                </marker>
            </defs>'''
        ]
        for el in elements:
            xmin = self._scale_coord(el["bbox"][0], True)
            ymin = self._scale_coord(el["bbox"][1], False)
            xmax = self._scale_coord(el["bbox"][2], True)
            ymax = self._scale_coord(el["bbox"][3], False)
            w, h = max(1, xmax - xmin), max(1, ymax - ymin)
            etype = el["type"]
            style = el.get("style", {})
            shape = style.get("shape", "rectangle")
            alignment = style.get("text_alignment", "center" if etype in ["box", "table"] else "left")
            # =========================
            # box (视觉与防溢出修复)
            # =========================
            if etype == "box":
                # ⭐ 优化7：直接使用 JSON 中的 fill_color，如果没有再回退到设计系统
                fill = style.get("fill_color") or (ds["primary_box_fill"] if "unified" in el.get("label", "").lower() or "optimization" in el.get("label", "").lower() else ds["secondary_box_fill"])
                box_parts = []
                if shape == "circle":
                    cx, cy = xmin + w / 2, ymin + h / 2
                    r = min(w, h) / 2
                    box_parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="#CCC"/>')
                elif shape == "cylinder":
                    ry = min(12, h / 4)
                    box_parts.append(f'<ellipse cx="{xmin + w/2}" cy="{ymax - ry/2}" rx="{w/2}" ry="{ry/2}" fill="{fill}" stroke="#CCC"/>')
                    box_parts.append(f'<rect x="{xmin}" y="{ymin + ry/2}" width="{w}" height="{h - ry/2}" fill="{fill}" stroke="none"/>')
                    box_parts.append(f'<line x1="{xmin}" y1="{ymin + ry/2}" x2="{xmin}" y2="{ymax - ry/2}" stroke="#CCC"/>')
                    box_parts.append(f'<line x1="{xmin + w}" y1="{ymin + ry/2}" x2="{xmin + w}" y2="{ymax - ry/2}" stroke="#CCC"/>')
                    box_parts.append(f'<ellipse cx="{xmin + w/2}" cy="{ymin + ry/2}" rx="{w/2}" ry="{ry/2}" fill="{fill}" stroke="#CCC"/>')
                else:
                    box_parts.append(f'<rect x="{xmin}" y="{ymin}" width="{w}" height="{h}" fill="{fill}" stroke="#CCC" rx="6"/>')
                svg_parts.append(f'<g>\n' + "\n".join(box_parts) + '\n</g>')
                if el.get("label"):
                    pre_calc_size = self._calc_safe_font_size(el["label"], w, default_size=12)
                    wrapped_text = self._refine_text_wrapping(el["label"], int(w), int(h), default_size=pre_calc_size)
                    safe_size = self._calc_safe_font_size(wrapped_text, w, default_size=12)
                    if alignment == "left":
                        text_x = xmin + 15
                    elif alignment == "right":
                        text_x = xmax - 15
                    else:
                        text_x = xmin + w/2
                    svg_parts.append(
                        self._render_text(text_x, ymin + h/2, wrapped_text, safe_size, 
                                            ds["text_color"], alignment, font_family=ds["body_font"])
                    )
            # =========================
            # text (标题/段落文本强化)
            # =========================
            elif etype == "text":
                is_title = "unified view" in el.get("label", "").lower() or "post-training" in el.get("label", "").lower()
                font_fam = ds["heading_font"] if is_title else ds["body_font"]
                default_fs = 18 if is_title else 14
                pre_calc_size = self._calc_safe_font_size(el["label"], w, default_size=default_fs)
                wrapped_text = self._refine_text_wrapping(el["label"], int(w), int(h), default_size=pre_calc_size)
                safe_size = self._calc_safe_font_size(wrapped_text, w, default_size=default_fs)
                # ⭐ 优化8：读取 JSON text 元素自身的 fill_color (如深蓝色标题)
                text_color = style.get("fill_color") or ds["text_color"]
                svg_parts.append(
                    self._render_text(xmin + w/2, ymin + h/2, wrapped_text, safe_size, 
                                        text_color, alignment, font_family=font_fam)
                )
            # =========================
            # line
            # =========================
            elif etype == "line":
                svg_parts.append(
                    f'<line x1="{xmin}" y1="{ymin}" x2="{xmax}" y2="{ymax}" '
                    f'stroke="#666" stroke-width="2" marker-end="url(#arrowhead)"/>'
                )
            # =========================
            # icon
            # =========================
            elif etype == "icon":
                icon_svg = self._generate_icon_element(el)
                sx, sy = w / 100, h / 100
                svg_parts.append(f'<g transform="translate({xmin},{ymin}) scale({sx},{sy})">{icon_svg}</g>')
            # =========================
            # table
            # =========================
            elif etype == "table":
                self._render_table(el, xmin, ymin, w, h, svg_parts)
            # =========================
            # coordinate_chart (⭐ 优化9：应用语义颜色映射)
            # =========================
            elif etype == "coordinate_chart":
                chart_parts = []
                structure = el.get("structure", {})
                fill = style.get("fill_color") or ds["secondary_box_fill"]
                stroke_color = self._darken_color(fill, 0.7)
                chart_parts.append(f'<rect x="{xmin}" y="{ymin}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke_color}" stroke-width="1.5" rx="8"/>')
                mid_x, mid_y = xmin + w / 2, ymin + h / 2
                chart_parts.append(f'<line x1="{xmin}" y1="{mid_y}" x2="{xmax}" y2="{mid_y}" stroke="#999" stroke-width="1" stroke-dasharray="4"/>')
                chart_parts.append(f'<line x1="{mid_x}" y1="{ymin}" x2="{mid_x}" y2="{ymax}" stroke="#999" stroke-width="1" stroke-dasharray="4"/>')
                axis_labels = structure.get("axis_labels", [])
                label_map = {}
                if isinstance(axis_labels, dict):
                    label_map = axis_labels
                elif isinstance(axis_labels, list):
                    for lbl in axis_labels:
                        if "top:" in lbl: label_map["top"] = lbl.split("top:")[1].strip()
                        elif "bottom:" in lbl: label_map["bottom"] = lbl.split("bottom:")[1].strip()
                        elif "left:" in lbl: label_map["left"] = lbl.split("left:")[1].strip()
                        elif "right:" in lbl: label_map["right"] = lbl.split("right:")[1].strip()
                if label_map.get("top"): chart_parts.append(self._render_text(mid_x, ymin + 15, label_map["top"], 10, ds["text_color"], "center", font_family=ds["body_font"]))
                if label_map.get("bottom"): chart_parts.append(self._render_text(mid_x, ymax - 15, label_map["bottom"], 10, ds["text_color"], "center", font_family=ds["body_font"]))
                if label_map.get("left"): chart_parts.append(self._render_text(xmin + 30, mid_y, label_map["left"], 10, ds["text_color"], "center", font_family=ds["body_font"]))
                if label_map.get("right"): chart_parts.append(self._render_text(xmax - 30, mid_y, label_map["right"], 10, ds["text_color"], "center", font_family=ds["body_font"]))
                scatter_items = structure.get("scatter_items", [])
                padding_x, padding_y = w * 0.15, h * 0.15
                available_w, available_h = w - 2 * padding_x, h - 2 * padding_y
                for idx, item in enumerate(scatter_items):
                    angle = (idx / max(1, len(scatter_items))) * 2 * 3.14159
                    radius_factor = 0.4 + (idx % 3) * 0.1
                    item_x = mid_x + available_w * radius_factor * (1 if angle > 3.14 else -1) * 0.4
                    item_y = mid_y + available_h * radius_factor * (1 if (angle % 3.14) > 1.57 else -1) * 0.4
                    # 🎨 使用解析出的语义颜色，回退到默认蓝色
                    item_color = self.semantic_colors.get(item, "#3B82F6")
                    chart_parts.append(f'<circle cx="{item_x}" cy="{item_y}" r="18" fill="{item_color}" stroke="#FFF" stroke-width="2"/>')
                    chart_parts.append(self._render_text(item_x, item_y, item, 11, "#FFFFFF", "center", font_weight="bold", font_family=ds["heading_font"]))
                svg_parts.append(f'<g>\n' + "\n".join(chart_parts) + '\n</g>')
        svg_parts.append("</svg>")
        # =========================
        # 保存
        # =========================
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        final_svg = "\n".join(svg_parts)
        final_svg = self._sanitize_svg(final_svg)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_svg)
        logger.info(f"✅ SVG 渲染完成 (原图配色还原+智能排版): {output_path}")
if __name__ == "__main__":
    api_key = os.getenv("DASHSCOPE_API_KEY")
    json_path = "assets/layout.json"
    image_path = "test_figure.png"
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        real_width, real_height = 1200, 900
        if os.path.exists(image_path):
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    real_width, real_height = img.size
                    print(f"检测到原图尺寸: {real_width}x{real_height}，已同步至SVG画布")
            except Exception as e:
                print(f"读取原图尺寸失败，使用默认值: {e}")
        engine = SVGEngine(api_key=api_key, width=real_width, height=real_height)
        engine.create_svg(data, "output_reconstructed.svg")
    else:
        print(f"找不到配置文件: {json_path}")