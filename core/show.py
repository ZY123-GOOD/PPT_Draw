import json
import os
from PIL import Image, ImageDraw, ImageFont

# # =========================
# # 配置路径
# # =========================
# image_path = "test_figure.png"
# json_path = "assets/layout.json"
# out_path = "debug_bbox_vis.png"

# # =========================
# # 初始化画布（不使用原图）
# # =========================
# if not os.path.exists(image_path):
#     print(f"Error: {image_path} not found.")
#     exit()

# img_src = Image.open(image_path)
# w, h = img_src.size

# # 白色背景
# img = Image.new("RGB", (w, h), "white")
# draw = ImageDraw.Draw(img)

# =========================
# 字体（优先中文字体）
# =========================
def load_font(size):
    try:
        # Windows（推荐）
        return ImageFont.truetype("msyh.ttc", size)
    except:
        try:
            # Mac
            return ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", size)
        except:
            try:
                # Linux Noto
                return ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size)
            except:
                # fallback
                return ImageFont.load_default()

# font_size = max(12, int(h * 0.02))
# font = load_font(font_size)

# # =========================
# # JSON 读取
# # =========================
# with open(json_path, "r", encoding="utf-8") as f:
#     data = json.load(f)

# items = data.get("elements", []) if isinstance(data, dict) else data

COLOR_MAP = {
    "box": "#FF3B30",
    "text": "#34C759",
    "line": "#007AFF",
    "default": "#AF52DE"
}

# print(f"Processing {len(items)} elements...")

# =========================
# 精确换行函数（核心）
# =========================
def wrap_text(text, font, draw, max_width):
    lines = []
    for paragraph in text.split("\n"):
        if paragraph == "":
            lines.append("")
            continue

        line = ""
        for ch in paragraph:
            test_line = line + ch
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]

            if width > max_width:
                lines.append(line)
                line = ch
            else:
                line = test_line

        if line:
            lines.append(line)

    return lines

# # =========================
# # 主循环
# # =========================
# for i, item in enumerate(items):
#     bbox = item.get("bbox")
#     if not bbox or len(bbox) != 4:
#         continue

#     x1, y1, x2, y2 = bbox

#     left   = x1 * w / 1000
#     top    = y1 * h / 1000
#     right  = x2 * w / 1000
#     bottom = y2 * h / 1000

#     rect = [
#         min(left, right),
#         min(top, bottom),
#         max(left, right),
#         max(top, bottom)
#     ]

#     elem_type = item.get("type", "default")
#     color = COLOR_MAP.get(elem_type, COLOR_MAP["default"])

#     # =========================
#     # 画 bbox
#     # =========================
#     draw.rectangle(rect, outline=color, width=2)

#     # =========================
#     # 文本内容（结构化分段）
#     # =========================
#     label = str(item.get("label", ""))
#     instruction = str(item.get("style", ""))

#     text = f"Label:\n{label}\n\nInstruction:\n{instruction}"

#     # =========================
#     # 文本区域限制
#     # =========================
#     max_width = rect[2] - rect[0] - 10

#     lines = wrap_text(text, font, draw, max_width)
#     final_text = "\n".join(lines)

#     # =========================
#     # 计算高度（防溢出）
#     # =========================
#     line_height = font_size + 4
#     text_h = min(line_height * len(lines) + 6, rect[3] - rect[1])

#     # =========================
#     # 背景框（避免遮挡）
#     # =========================
#     draw.rectangle(
#         [
#             rect[0],
#             rect[1],
#             rect[0] + max_width,
#             rect[1] + text_h
#         ],
#         fill="white"
#     )

#     # =========================
#     # 写文字
#     # =========================
#     draw.multiline_text(
#         (rect[0] + 4, rect[1] + 4),
#         final_text,
#         fill="black",
#         font=font
#     )

# # =========================
# # 保存结果
# # =========================
# img.save(out_path)
# print(f"Saved to: {out_path}")