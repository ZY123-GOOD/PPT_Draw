import base64
import json
import os
import re
import mimetypes
import logging
from typing import Dict, List, Optional, Any
from PIL import Image
from openai import OpenAI

logger = logging.getLogger(__name__)

# 配置常量
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen3-vl-flash-2025-10-15" 

class VLMAnalyst:
    def __init__(self, api_key: str, base_url: str = QWEN_BASE_URL, model: str = QWEN_MODEL):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def _get_image_metadata(self, image_path: str) -> tuple[int, int]:
        """获取图片的物理尺寸 (width, height)"""
        with Image.open(image_path) as img:
            return img.size

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type not in ("image/png", "image/jpeg", "image/webp"):
            mime_type = "image/png"
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8"), mime_type

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """增强版 JSON 提取，处理非贪婪匹配和转义字符"""
        # 模式1：标准 Markdown JSON 块
        json_block = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if json_block:
            return json.loads(json_block.group(1))
        
        # 模式2：查找最外层的花括号
        outer_json = re.search(r"(\{[\s\S]*\})", text)
        if outer_json:
            return json.loads(outer_json.group(1))
            
        raise ValueError(f"Failed to parse JSON from VLM output: {text[:100]}...")

    def analyze_layout(self, image_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(image_path):
            logger.error(f"File not found: {image_path}")
            return None

        # 1. 获取元数据
        width, height = self._get_image_metadata(image_path)
        base64_image, mime_type = self._encode_image(image_path)

        # 2. 精细化 Prompt
        # 强制要求像素坐标，并要求对组件进行描述以辅助后续的 SAM 分割
        prompt = f"""你是一个专业的学术论文插图分析专家。请分析这张 {width}x{height} 的图片，并将其解构为可编辑的“素材抽屉”。

### 任务目标
识别图中所有独立元素，并提取其几何属性和语义信息。

### 严格坐标规范
- 采用归一化坐标系 [0, 1000]。
- bbox 格式：[xmin, ymin, xmax, ymax]。
- x 轴对应 Width，y 轴对应 Height。

### 素材分类定义
1. "box": 矩形框、圆形等封闭容器。
2. "text": 框外的独立说明文字。
3. "line": 连接线或箭头。如果是箭头，请在 description 中注明指向。

### 输出 JSON 结构要求
{{
  "elements": [
    {{
      "id": 1,
      "type": "box",
      "bbox": [xmin, ymin, xmax, ymax],
      "label": "框内的完整文字",
      "style": {{
        "shape": "rectangle|circle|cylinder",
        "fill_color": "颜色描述",
        "border_style": "solid|dashed"
      }},
      "description": "例如：基础编码器模块"
    }},
    {{
      "id": 2,
      "type": "line",
      "bbox": [xmin, ymin, xmax, ymax],
      "label": "线上文字(如果有)",
      "direction": "from_id_A_to_id_B",
      "description": "带箭头的实线"
    }}
  ]
}}

### 注意事项
1. **原子化**：如果一个大框包含小框，请分别识别，并在 description 中标注层级关系。
2. **文字关联**：如果文字在框内，请将其合并到该 box 的 "label" 中，不要拆分为独立的 text。
3. **忽略背景**：不要把纯白色的大背景识别为一个 box。

请直接输出 JSON，不要带有任何解释。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                temperature=0.1, # 低采样随机性保证坐标稳定
            )

            raw_content = response.choices[0].message.content
            result = self._extract_json(raw_content)
            
            # 注入元数据以防模型漏掉
            result["metadata"] = {"width": width, "height": height}
            
            logger.info(f"Successfully analyzed {len(result.get('elements', []))} elements.")
            return result

        except Exception as e:
            logger.error(f"VLM Analysis critical error: {e}")
            return None

    def save_layout(self, layout_data: Dict[str, Any], output_path: str):
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(layout_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

# if __name__ == "__main__":
#     # 示例运行逻辑
#     logging.basicConfig(level=logging.INFO)
#     api_key = os.getenv("DASHSCOPE_API_KEY")
#     if not api_key:
#         print("Please set DASHSCOPE_API_KEY env var.")
#     else:
#         analyst = VLMAnalyst(api_key=api_key)
#         res = analyst.analyze_layout("test_figure.png")
#         if res:
#             analyst.save_layout(res, "assets/session_test/layout.json")

import numpy as np

class MultiRunVLMAnalyst(VLMAnalyst):
    def _calculate_iou(self, boxA: List[int], boxB: List[int]) -> float:
        """计算两个归一化 bbox 的交并比 (IoU)"""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        
        # 防止除零
        if float(boxAArea + boxBArea - interArea) <= 0: return 0
        return interArea / float(boxAArea + boxBArea - interArea)

    def analyze_layout_consistent(self, image_path: str, n_runs: int = 3) -> Optional[Dict[str, Any]]:
        """运行多次并聚合结果"""
        all_runs_data = []
        
        for i in range(n_runs):
            logger.info(f">>> 正在进行第 {i+1}/{n_runs} 次视觉分析采样...")
            res = self.analyze_layout(image_path)
            if res and "elements" in res:
                all_runs_data.append(res)
        
        if not all_runs_data:
            return None

        # 聚合逻辑
        logger.info(f"采样完成，开始聚合 {len(all_runs_data)} 组数据...")
        
        # 以第一组结果为种子
        final_elements = []
        # 记录已经被匹配过的元素，防止重复统计
        # 简单起见：我们使用“贪婪匹配”策略
        base_res = all_runs_data[0]
        seeds = base_res.get("elements", [])
        
        for seed in seeds:
            matched_bboxes = [seed["bbox"]]
            labels = [seed.get("label", "")]
            
            # 在后续的 runs 中寻找它的分身
            for other_run in all_runs_data[1:]:
                for other_item in other_run.get("elements", []):
                    # 如果 IoU > 0.7，认为是同一个物体
                    if self._calculate_iou(seed["bbox"], other_item["bbox"]) > 0.7:
                        matched_bboxes.append(other_item["bbox"])
                        if other_item.get("label"):
                            labels.append(other_item["label"])
                        break 
            
            # 聚合策略：计算坐标平均值
            if len(matched_bboxes) >= 1: # 只要出现就保留，也可以设为 > n_runs/2
                avg_bbox = np.mean(matched_bboxes, axis=0).astype(int).tolist()
                new_item = seed.copy()
                new_item["bbox"] = avg_bbox
                # 取最长的 label 作为最终文字（防止某次 OCR 截断）
                new_item["label"] = max(labels, key=len) if labels else ""
                final_elements.append(new_item)

        return {
            "metadata": base_res.get("metadata"),
            "elements": final_elements,
            "info": f"Aggregated from {len(all_runs_data)} runs"
        }

# =========================
# 示例运行逻辑 (Main)
# =========================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    test_image = "test_figure.png" # 你的测试图
    
    if not api_key:
        print("错误: 请先设置环境变量 DASHSCOPE_API_KEY")
    else:
        # 使用增强版 Analyst
        analyst = MultiRunVLMAnalyst(api_key=api_key)
        
        # 设定运行 3 次以获取最稳定的“素材抽屉”
        final_layout = analyst.analyze_layout_consistent(test_image, n_runs=3)
        
        if final_layout:
            output_file = "assets/session_test/layout.json"
            analyst.save_layout(final_layout, output_file)
            print("-" * 30)
            print(f"✅ 分析完成！")
            print(f"原始识别元素数: {len(final_layout['elements'])}")
            print(f"素材抽屉已保存至: {output_file}")
            print("提示: 现在你可以运行可视化脚本查看平均后的 bbox 是否更准了。")
        else:
            print("❌ 分析失败，请检查网络或 API Key。")