import json
import os
from PIL import Image, ImageDraw

def generate_sketch_with_original_size(image_reference_path, json_path, out_path="original_size_sketch.png", fill_mode=False):
    """
    基于原图尺寸生成引导草图
    :param image_reference_path: 参考原图的路径，用于获取准确的 Width 和 Height
    :param json_path: 布局 JSON 路径
    :param out_path: 输出路径
    :param fill_mode: False 为线框模式（推荐用于 Sketch），True 为色块模式（推荐用于 Layout）
    """
    
    # 1. 获取原图尺寸
    if not os.path.exists(image_reference_path):
        print(f"Error: 找不到参考原图 {image_reference_path}")
        return
    
    with Image.open(image_reference_path) as ref_img:
        orig_w, orig_h = ref_img.size
    
    print(f"检测到原图尺寸: {orig_w}x{orig_h}，正在创建画布...")

    # 2. 创建与原图等大的空白画布 (白底)
    img = Image.new("RGB", (orig_w, orig_h), "white")
    draw = ImageDraw.Draw(img)

    # 3. 加载 JSON 数据
    if not os.path.exists(json_path):
        print(f"Error: 找不到 JSON 文件 {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("elements", []) if isinstance(data, dict) else data

    # 4. 定义色彩语义 (保持高对比度)
    COLOR_MAP = {
        "box": "#FF0000",    # 红色
        "text": "#00FF00",   # 绿色
        "line": "#0000FF",   # 蓝色
        "button": "#FFFF00", # 黄色
        "default": "#000000" # 黑色
    }

    # 5. 绘制逻辑
    for item in items:
        bbox = item.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        
        # 坐标映射 (基于 0-1000 的相对比例还原到原图绝对像素)
        x1, y1, x2, y2 = bbox
        left   = x1 * orig_w / 1000
        top    = y1 * orig_h / 1000
        right  = x2 * orig_w / 1000
        bottom = y2 * orig_h / 1000

        rect = [min(left, right), min(top, bottom), max(left, right), max(top, bottom)]
        elem_type = item.get("type", "default")
        color = COLOR_MAP.get(elem_type, COLOR_MAP["default"])

        if fill_mode:
            # 实心填充模式
            draw.rectangle(rect, fill=color)
        else:
            # 动态线宽：根据图片长边计算线宽，确保大图下线条依然清晰
            line_width = max(3, int(max(orig_w, orig_h) * 0.005))
            draw.rectangle(rect, outline=color, width=line_width)

    # 6. 保存
    img.save(out_path)
    print(f"成功！草图已按原尺寸保存至: {out_path}")

# =========================
# 调用示例
# =========================
if __name__ == "__main__":
    generate_sketch_with_original_size(
        image_reference_path="test_figure.png", # 传入你的原图路径
        json_path="assets/layout.json", 
        out_path="layout_to_sketch_fixed.png",
        fill_mode=False # Qwen-Image 建议先用 False (线框) 尝试
    )