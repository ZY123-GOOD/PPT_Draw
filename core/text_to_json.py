from openai import OpenAI
import os
import json
import re

# 4. 保存 JSON 文件
# =========================
def save_to_file(data_str: str, filename="text_2_json.json"):
    try:
        data = json.loads(data_str)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 已保存到文件: {filename}")

    except Exception as e:
        print("\n❌ JSON 解析失败，未保存文件")
        print("错误信息：", str(e))
        print("\n原始输出如下：\n")
        print(data_str)

	# =========================
	# 1. Prompt Builder (v2 - 丰富布局版)
	# =========================
def build_prompt(user_input: str):
	    return f"""
	你是一个"PPT布局生成引擎（Layout Compiler）"。
	你的任务是：根据用户的自然语言描述，生成一个可渲染PPT页面的JSON结构。
	⚠️ 核心目标："视觉丰富 + 信息密集 + 构图多样 + 可直接绘制"。
	---
	# 🧠 核心原则
	## 1️⃣ 先选构图，再填内容
	你必须先决定本页使用哪种 layout_pattern，然后再放置元素。
	严禁每次都使用"标题+表格+图表+总结"的四段式默认布局。
	## 2️⃣ label 是"主要语义载体"（给绘图模型）
	- 信息完整、可读性强、可直接用于画图排版
	- 对 table/chart 进行"展开描述"
	- 对 card/timeline/flow 等类型也要展开语义
	## 3️⃣ structure 是"结构数据"（给程序）
	- table → cells
	- chart → axis + items
	- 其他类型按需填充
	## 4️⃣ drawing_instruction 是"视觉执行说明"
	必须描述：
	- 布局方式（居中 / 左右分栏 / 网格 / 放射 / 阶梯 / 流水线…）
	- 视觉层级（主标题 / 副标题 / 主内容 / 次要信息 / 装饰）
	- 风格（学术 / 极简 / 卡片式 / 杂志风 / 信息图…）
	- 留白策略（tight / breathable / generous）
	- 视觉动线（Z型 / F型 / 居中放射 / 从左到右流…）
	---
	# 📐 输出JSON结构
	{{
	  "page": {{
	    "layout_pattern": "title-body | split-2 | split-3 | quad-grid | timeline-horizontal | timeline-vertical | flow-pipeline | comparison-side | comparison-overlay | hero-center | card-grid | quote-focus | circle-radial | staircase | free-composition",
	    "visual_style": "academic | minimal | magazine | infographic | dark-tech | hand-drawn",
	    "whitespace_strategy": "tight | breathable | generous",
	    "visual_flow": "Z-pattern | F-pattern | center-radial | left-to-right | top-to-bottom"
	  }},
	  "elements": [
	    {{
	      "id": int,
	      "type": "heading | subtitle | text | quote | callout | card | badge | tag | timeline_node | flow_arrow | table | coordinate_chart | icon | illustration_placeholder | divider | highlight_box",
	      "bbox": [xmin, ymin, xmax, ymax],
	      "center": [cx, cy],
	      "label": "⚠️高信息密度语义描述（必须展开）",
	      "visual_weight": "dominant | primary | secondary | tertiary | decorative",
	      "z_index": int,
	      "style": {{
	        "shape": "rectangle | rounded-rect | circle | pill | diamond | hexagon | chevron | arrow | none",
	        "fill_color": "#HEX",
	        "border_color": "#HEX",
	        "border_width": int,
	        "text_alignment": "left | center | right",
	        "font_size_hint": "xs | sm | base | lg | xl | 2xl | 3xl",
	        "font_weight": "light | regular | medium | bold | black",
	        "drawing_instruction": "必须包含：布局方式 + 层级 + 风格 + 留白 + 动线"
	      }},
	      "structure": {{
	        "rows": "",
	        "cols": "",
	        "cells": "",
	        "axis_labels": "",
	        "scatter_items": "",
	        "flow_direction": "",
	        "timeline_date": "",
	        "timeline_event": ""
	      }},
	      "description": "该组件在PPT中的作用"
	    }}
	  ]
	}}
	---
	# 🎨 构图模板库（必须从中选择或组合）
	## 1. title-body
	标题占顶部窄条，主体内容占据下方大面积。最基础但不过时。
	## 2. split-2
	左右对半分栏。适合对比、因果、问题-方案。
	左栏放一个 type，右栏放另一个 type。
	## 3. split-3
	三等分纵向栏。适合三并列概念、三个案例、过去-现在-未来。
	## 4. quad-grid
	2×2 网格。适合四象限分析、四种分类、矩阵对比。
	## 5. timeline-horizontal
	横向时间轴。节点用 timeline_node，之间用 flow_arrow 连接。
	适合演进历史、里程碑、流程步骤。
	## 6. timeline-vertical
	纵向时间轴。同上但垂直排列，适合步骤多、每步有详细说明的场景。
	## 7. flow-pipeline
	从左到右的管道/漏斗。用 flow_arrow + card 组合。
	适合数据流水线、推理链、决策流程。
	## 8. comparison-side
	左右大块对比。中间可用 divider 分隔。
	两侧各放 card 或 highlight_box，底部可加一行总结。
	## 9. hero-center
	中心一个巨大的核心元素（大字/大图/大card），周围环绕小标注。
	适合核心概念展示、Key Message 页。
	## 10. card-grid
	多个 card 均匀排列成网格。每个 card 内部有标题+简短描述+可选icon。
	适合特性列表、方法概览、多维对比。
	## 11. quote-focus
	大号引言居中，下方小字注明出处。背景可用大色块。
	适合开篇定调、名人名言、核心观点强调。
	## 12. circle-radial
	中心一个核心概念，周围放射状排列 4-6 个子概念。
	用 icon + text 组合，连线暗示关系。
	## 13. staircase
	阶梯式从左下到右上排列 3-5 个步骤/层级。
	适合层级递进、成熟度模型、能力阶梯。
	## 14. free-composition
	以上模板都不合适时，自由组合。但必须明确描述视觉动线。
	---
	# 📊 特殊强化规则
	## ✅ table
	- 必须整体输出
	- structure.cells = 严格二维数组
	- ⚠️ label 必须"展开成完整表格描述"
	示例：
	Method Comparison Table:
	Columns: Method | Sampling | Reward | KL Ref | Key Property
	Rows:
	SFT - Teacher - Token target - Base - Imitation learning
	RLHF - Student - Reward model - Base - Human alignment
	## ✅ coordinate_chart
	- 必须整体输出
	- ⚠️ label 必须包含：坐标轴含义 + 分布方向 + 每个点位置/颜色/含义
	## ✅ card（新增重点）
	- 每个 card 是一个独立信息单元
	- label 必须包含：card标题 + 核心内容 + 可选标签
	- 适合替代"表格行"来做更生动的对比展示
	示例：
	Card: "DPO"
	- Core: Direct preference optimization, no reward model needed
	- Tags: #Offline #Simple #NoRM
	## ✅ timeline_node（新增重点）
	- label 必须包含：时间/阶段 + 事件名 + 简要描述
	- structure.timeline_date + structure.timeline_event
	## ✅ flow_arrow（新增重点）
	- label 描述这条箭头的语义（如"训练 → 推理"、"数据 → 模型"）
	- structure.flow_direction = "left-to-right" | "top-to-bottom"
	## ✅ quote（新增重点）
	- label = 完整引言文本
	- 适合开篇页或章节过渡页
	## ✅ callout / highlight_box
	- label = 需要强调的关键信息
	- 视觉上比普通 text 更醒目（边框/背景色/阴影暗示）
	---
	# 📐 页面规格
	- canvas size: 1000 x 1000
	---
	# 📏 布局规则
	1. 标题区在顶部（y < 120），可用 heading + subtitle 组合
	2. 主内容区根据 layout_pattern 分配空间
	3. bbox 必须合理且不重叠
	4. visual_weight = "dominant" 的元素应占据最大面积
	5. z_index: 背景装饰 < 内容卡片 < 标题 < 高亮标注
	6. 元素之间至少留 20px 间距（在 1000×1000 坐标系下）
	---
	# 🚫 禁止行为（非常重要！！！）
	1. ❌ 每页都用"标题 + 表格 + 图表 + 总结框"的四段式
	2. ❌ label 过于简短（如只写"DPO"三个字母）
	3. ❌ table 只写 cells 不写语义展开
	4. ❌ chart 没有空间描述
	5. ❌ drawing_instruction 模糊（如"画一个框"）
	6. ❌ 所有元素都是 table 或 coordinate_chart 类型
	7. ❌ 忽略 layout_pattern 的选择，随便堆砌
	8. ❌ 连续多页使用相同 layout_pattern
	---
	# ✅ 鼓励行为
	1. ✅ 根据内容性质选择最合适的 layout_pattern
	2. ✅ 对比信息优先考虑 split-2 / comparison-side / card-grid
	3. ✅ 流程/演进优先考虑 timeline / flow-pipeline / staircase
	4. ✅ 核心概念优先考虑 hero-center / circle-radial / quote-focus
	5. ✅ 多维度分析优先考虑 quad-grid / card-grid
	6. ✅ 混合使用多种 element type（card + icon + text + divider…）
	7. ✅ 用 visual_weight 区分主次，不要所有元素平铺
	8. ✅ 用 color 区分语义分组（如：方法A色系 vs 方法B色系）
	---
	# 输出要求
	- 只输出 JSON
	- 不要解释
	- 不要 markdown 代码块标记
	---
	用户需求：
	{user_input}
	""".strip()


# =========================
# 2. 核心生成函数
# =========================
def generate_ppt_layout(user_input: str, api_key:str, stream: bool = True):
    messages = [
        {"role": "user", "content": build_prompt(user_input)}
    ]
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    completion = client.chat.completions.create(
        model="qwen3.6-plus",
        messages=messages,
        stream=stream,
        extra_body={"enable_thinking": False},
    )

    result_text = ""

    if stream:
        print("\n===== Streaming Output =====\n")
        for chunk in completion:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                print(delta.content, end="", flush=True)
                result_text += delta.content
        print("\n")
    else:
        result_text = completion.choices[0].message.content

    return result_text


# =========================
# 3. JSON 校验函数（简单版）
# =========================
def validate_layout_json(text: str):
    try:
        data = json.loads(text)

        assert "elements" in data
        assert isinstance(data["elements"], list)

        for el in data["elements"]:
            assert "type" in el
            assert "bbox" in el
            assert len(el["bbox"]) == 4

        print("\n✅ JSON 格式校验通过")
        return True

    except Exception as e:
        print("\n❌ JSON 校验失败：", str(e))
        return False

def clean_json(text: str):
    text = text.strip()

    # 去掉 ```json
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    return text.strip()

# =========================
# 4. 测试函数
# =========================
def test():
    user_input = "做一个RLHF vs DPO vs GRPO的对比PPT，用表格+坐标系展示方法差异，并加一个总结框"

    result = generate_ppt_layout(user_input, stream=True)

    print("\n===== RAW RESULT =====\n")
    print(result)
    validate_layout_json(result)
    
    cleaned = clean_json(result)
    save_to_file(cleaned, "assets/text_2_json.json")

    


# =========================
# 5. main
# =========================
if __name__ == "__main__":
    test()