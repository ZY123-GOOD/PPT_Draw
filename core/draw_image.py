import os
import json
import time
import requests
import dashscope
import base64
from dashscope import Generation, ImageSynthesis, MultiModalConversation
from dashscope.aigc.image_generation import ImageGeneration
import json
from dashscope.api_entities.dashscope_response import Message
# dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# =========================================================
# 1. Layout JSON → STRUCTURED SPEC（🔥保留 drawing_instruction）
# =========================================================
def layout_to_structured_spec(layout_json):
    system_prompt = """
You are a STRICT layout compiler.

CRITICAL RULES:
- DO NOT change bbox
- DO NOT merge elements
- DO NOT summarize away important info
- PRESERVE drawing_instruction EXACTLY
- KEEP label + drawing_instruction

OUTPUT FORMAT:

ELEMENT:
id: ...
type: ...
bbox: [x1,y1,x2,y2]

content:
(label text)

render_instruction:
(drawing_instruction original text)
"""

    resp = Generation.call(
        model="qwen3-max",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(layout_json, ensure_ascii=False)}
        ],
        result_format="message"
    )

    return resp.output.choices[0].message.content.strip()


# =========================================================
# 2. 🔥 注入“渲染执行规则”（关键层）
# =========================================================
def inject_rendering_rules(spec_text):
    return f"""
You MUST follow these rendering rules strictly:

GLOBAL LAYOUT RULES:
- Each ELEMENT corresponds to a fixed bounding box (bbox)
- NEVER move elements
- NEVER merge elements
- STRICT grid alignment
- NO overlap

ELEMENT RENDERING RULES:
- "render_instruction" is MANDATORY drawing logic
- Treat render_instruction as pseudo-code
- If render_instruction exists → it OVERRIDES generic style
- Must explicitly render:
    - axes (for charts)
    - arrows / edges
    - legends
    - table structure

VISUAL CONSISTENCY:
- All elements must look like part of the SAME infographic
- Maintain spacing consistency

===== LAYOUT SPEC =====
{spec_text}
"""


# =========================================================
# 3. STRUCTURE → IMAGE PROMPT（🔥强化版）
# =========================================================
def structured_spec_to_prompt(spec_text):
    system_prompt = """
    You are a precision-driven Infographic Prompt Engineer. 
    Your job is to translate a Structured Spec into a LITERALLY DESCRIPTIVE image prompt.

    CRITICAL RULES FOR CONTENT PRESERVATION:
    1. NO SUMMARIZATION: You are FORBIDDEN from using phrases like "as specified", "detailed earlier", or "rows as described". 
    2. FULL TEXT INCLUSION: Every single word found in the "content" field of the SPEC must be explicitly written out in the final prompt. 
    3. TABLE DATA INTEGRITY: For tables, you must explicitly describe every cell. (e.g., "Cell at Row 1, Column 1 contains text: 'RLHF'")
    4. VERBATIM RENDERING: Treat all text in "content" as sacred. If it's in the spec, it must be in your output.

    OUTPUT STYLE:
    - Use a "Layer-by-Layer" description.
    - For each element, specify: [BBOX] + [EXACT TEXT CONTENT] + [VISUAL STYLE].
    """
    resp = Generation.call(
        model="qwen3-max",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": spec_text}
        ],
        result_format="message"
    )

    base_prompt = resp.output.choices[0].message.content.strip()

    style = """

GLOBAL STYLE:
- AI research infographic
- flat design
- minimal
- white background
- blue / gray palette
- clean typography
- no 3D
- no photorealism
- sharp vector-like rendering
- high readability
"""

    return base_prompt + style


# =========================================================
# 4. Qwen-Image 生成（🔥 sketch 强约束）
# =========================================================
import urllib.request
def generate_image(prompt, save_path="output.png",w=None,h=None):
    size = f"{w}*{h}" if w and h else "1024*768"
    
    messages = [
        {
            "role": "user",
            "content": [
                {"text": prompt}
            ]
        }
    ]
    response = MultiModalConversation.call(
        model="qwen-image-2.0-pro-2026-03-03",
        messages=messages,
        result_format="message",
        size=size
    )
    content = response.output.choices[0].message.content
    image_url = None
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and "image" in item:
                image_url = item["image"]
                break
    if image_url is None:
        raise ValueError("No image returned")
    import requests
    img = requests.get(image_url, timeout=60).content
    with open(save_path, "wb") as f:
        f.write(img)
    print(f"[IMAGE SAVED] → {save_path}")
    return image_url, save_path
    


# =========================================================
# 6. 主流程（🔥完整闭环）
# =========================================================
def render(layout_json, w=None, h=None):
    print("\n[1] JSON → STRUCTURED SPEC")
    spec = layout_to_structured_spec(layout_json)

    print("\n[RAW SPEC]")
    print(spec)

    # 🔥注入 rendering rules
    spec_with_rules = inject_rendering_rules(spec)
    
    print(f"\n[2] BUILD PROMPT WITH RENDERING RULES INJECTED]")
    print(spec_with_rules)

    # prompt = structured_spec_to_prompt(spec_with_rules)
    prompt = spec_with_rules
    # print("\n[PROMPT]")
    # print(prompt[:])  # 防止太长刷屏

    print("\n[3] GENERATE IMAGE")
    image_url, path = generate_image(
        prompt,
        w=w,
        h=h
    )

    return image_url, path


# # =========================================================
# # 7. ENTRY
# # =========================================================
# if __name__ == "__main__":
#     from PIL import Image

#     image_path = "test_figure.png"

#     with Image.open(image_path) as img:
#         real_width, real_height = img.size

#     print(f"Canvas size: {real_width} x {real_height}")
#     with open("assets/layout.json", "r", encoding="utf-8") as f:
#         layout = json.load(f)

#     render(
#         layout_json=layout,
#         w=real_width,
#         h=real_height
#     )