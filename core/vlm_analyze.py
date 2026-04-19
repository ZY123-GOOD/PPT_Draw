import base64
import json
import os
import re
import mimetypes
import logging
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image
import numpy as np
from collections import Counter
from openai import OpenAI
# =========================
# 日志与配置
# =========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen3-vl-flash-2025-10-15"
# QWEN_MODEL = "qwen3-vl-flash-2026-01-22"
class VLMAnalyst:
    def __init__(self, api_key: str, base_url: str = QWEN_BASE_URL, model: str = QWEN_MODEL):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    def _get_image_metadata(self, image_path: str) -> Tuple[int, int]:
        with Image.open(image_path) as img:
            return img.size
    def _encode_image(self, image_path: str) -> Tuple[str, str]:
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type not in ("image/png", "image/jpeg", "image/webp"):
            mime_type = "image/png"
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8"), mime_type
    # ✅ 稳定 JSON 解析
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
        # 🚨 尝试修复截断 JSON
        if start is not None:
            partial = text[start:]
            missing = partial.count('{') - partial.count('}')
            if missing > 0:
                repaired = partial + ('}' * missing)
                try:
                    return json.loads(repaired)
                except Exception:
                    pass
        raise ValueError(f"JSON 解析失败。原始输出片段: {text[:200]}")
    # ✅ bbox 自动归一化
    def _normalize_bbox(self, bbox, width, height):
        x1, y1, x2, y2 = bbox
        if max(bbox) <= 1.5:
            return [int(x1 * 1000), int(y1 * 1000), int(x2 * 1000), int(y2 * 1000)]
        elif max(bbox) <= 1000:
            return bbox
        else:
            return [
                int(x1 / width * 1000),
                int(y1 / height * 1000),
                int(x2 / width * 1000),
                int(y2 / height * 1000),
            ]
    def analyze_layout(self, image_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(image_path):
            logger.error(f"找不到文件: {image_path}")
            return None
        width, height = self._get_image_metadata(image_path)
        base64_image, mime_type = self._encode_image(image_path)
        # ✅ Prompt（深度优化版：强化坐标系与表格整体性）
        prompt = f"""你是一个专业的学术论文插图分析专家。请分析这张 {width}x{height} 的图片，并解构为可编辑的“素材抽屉”。
### 素材分类定义
1. "box": 基础容器（矩形、圆形、数据库等），若文字在框内，请合并到 box 的 label 中。
2. "text": 框外的独立说明文字或标题。
3. "line": 带有方向的箭头或连接线。
4. "icon": 复杂的图标或图形。
5. "table": 表格结构，**必须作为单个整体识别，绝对禁止拆分为多个 box/line/text！**
6. "coordinate_chart": 散点坐标系区域（如右侧的 Conceptual Relationship）。**必须整体识别，绝对禁止拆分为表格！其内部的独立元素需通过 center 坐标定位。**
### 输出 JSON 结构
{{
    "elements": [
    {{
        "id": 1,
        "type": "box|text|line|icon|table|coordinate_chart",
        "bbox": [xmin, ymin, xmax, ymax],
        "label": "识别到的文字内容。如果是 table/chart，汇总所有文字",
        "center": [cx, cy], 
        "style": {{
        "shape": "rectangle|circle|cylinder|none",
        "fill_color": "#HEX代码",
        "text_alignment": "left|center|right", 
        "drawing_instruction": "如果是 icon 类型，请详细描述其组成；如果是 coordinate_chart，描述坐标轴含义（如：X轴=On/Off-policy，Y轴=Dense/Sparse）"
        }},
        "structure": {{
        "rows": "如果是 table，推测行数",
        "cols": "如果是 table，推测列数",
        "cells": "如果是 table，按行优先的二维数组，如 [[cell11, cell12], [cell21, cell22]]。单元格内换行用 \\n 表示",
        "axis_labels": "如果是 coordinate_chart，提取坐标轴旁的说明文字（如 top, bottom, left, right）",
        "scatter_items": "如果是 coordinate_chart，提取内部散落的元素名称列表（如 ['SFT', 'RLHF', 'DPO', 'GRPO', 'OPD']）"
        }},
        "description": "对该组件的功能简述"
    }}
    ]
}}
### 约束
- 坐标必须严格遵循 [xmin, ymin, xmax, ymax]，所有坐标基于原图像素尺寸。
- 所有 bbox 必须紧贴目标对象。
- **表格必须整体识别**，内部的文字和线不要单独输出。
- **坐标系必须整体识别**，不要误认为表格！坐标系内的文字（如 SFT, RLHF）不需要对齐，它们是散点分布的，请推算这些文字的 `center` 中心点坐标。
- 框内的文字必须合并到对应 box 或 table 的 label 中，不要在框外重复输出 text。
- text 必须推断其 text_alignment（长文本通常是 left，框内短标签通常是 center）。
### 输出要求
- 直接输出 JSON，不要任何开场白。"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }],
                temperature=0.1
            )
            result = self._extract_json(response.choices[0].message.content)
            # ✅ bbox 归一化
            for elem in result.get("elements", []):
                if "bbox" in elem:
                    elem["bbox"] = self._normalize_bbox(elem["bbox"], width, height)
                # 顺便归一化 center 坐标
                if "center" in elem and isinstance(elem["center"], list) and len(elem["center"]) == 2:
                    cx, cy = elem["center"]
                    if max([cx, cy]) <= 1.5:
                        elem["center"] = [int(cx * 1000), int(cy * 1000)]
                    elif max([cx, cy]) > 1000:
                        elem["center"] = [int(cx / width * 1000), int(cy / height * 1000)]
            return result,width, height
        except Exception as e:
            logger.error(f"VLM API 调用失败: {e}")
            return None,None,None
class MultiRunVLMAnalyst(VLMAnalyst):
    def _calculate_iou(self, boxA: List[int], boxB: List[int]) -> float:
        xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
        xB, yB = min(boxA[2], boxB[2]), min(boxB[3], boxA[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        return interArea / float(boxAArea + boxBArea - interArea + 1e-6)
    # ✅ 计算包容关系
    def _calculate_containment(self, parent_box, child_box) -> float:
        xA, yA = max(parent_box[0], child_box[0]), max(parent_box[1], child_box[1])
        xB, yB = min(parent_box[2], child_box[2]), min(parent_box[3], child_box[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        childArea = max(1, (child_box[2] - child_box[0]) * (child_box[3] - child_box[1]))
        return interArea / childArea
    # ✅ center 距离
    def _center_distance(self, a, b):
        ax = (a[0] + a[2]) / 2
        ay = (a[1] + a[3]) / 2
        bx = (b[0] + b[2]) / 2
        by = (b[1] + b[3]) / 2
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
    # ✅ 更稳取色
    def _sample_pixel_color(self, image_path: str, bbox: List[int]) -> str:
        try:
            with Image.open(image_path).convert("RGB") as img:
                w, h = img.size
                x1, y1, x2, y2 = bbox
                xs = np.linspace(x1, x2, 5)
                ys = np.linspace(y1, y2, 5)
                pixels = []
                for x in xs:
                    for y in ys:
                        px = int(x * w / 1000)
                        py = int(y * h / 1000)
                        px = max(0, min(w - 1, px))
                        py = max(0, min(h - 1, py))
                        pixels.append(img.getpixel((px, py)))
                most_common = Counter(pixels).most_common(1)[0][0]
                return '#{:02x}{:02x}{:02x}'.format(*most_common).upper()
        except Exception:
            return "#FFFFFF"
    # ✅ 更强 clustering
    def _cluster_elements(self, all_elements: List[Dict], iou_threshold: float = 0.6) -> List[List[Dict]]:
        clusters = []
        for elem in all_elements:
            placed = False
            for cluster in clusters:
                ref = cluster[0]
                if elem["type"] != ref["type"]:
                    continue
                iou = self._calculate_iou(elem["bbox"], ref["bbox"])
                center_dist = self._center_distance(elem["bbox"], ref["bbox"])
                if iou >= iou_threshold or center_dist < 50:
                    cluster.append(elem)
                    placed = True
                    break
            if not placed:
                clusters.append([elem])
        return clusters
    def _aggregate_cluster(self, cluster: List[Dict], image_path: str) -> Dict:
        bboxes = np.array([e["bbox"] for e in cluster])
        fused_bbox = np.median(bboxes, axis=0).astype(int).tolist()
        labels = [e.get("label", "") for e in cluster if e.get("label")]
        fused_label = Counter(labels).most_common(1)[0][0] if labels else ""
        instructions = [
            e.get("style", {}).get("drawing_instruction", "")
            for e in cluster
            if e.get("style", {}).get("drawing_instruction")
        ]
        best_instruction = max(instructions, key=len) if instructions else ""
        # ✅ 聚合文本对齐方式
        alignments = [
            e.get("style", {}).get("text_alignment", "")
            for e in cluster
            if e.get("style", {}).get("text_alignment")
        ]
        fused_alignment = Counter(alignments).most_common(1)[0][0] if alignments else "center"
        fused = cluster[0].copy()
        fused["bbox"] = fused_bbox
        fused["label"] = fused_label
        if "style" not in fused:
            fused["style"] = {}
        if fused["type"] == "icon":
            fused["style"]["drawing_instruction"] = best_instruction
        fused["style"]["text_alignment"] = fused_alignment
        fused["style"]["fill_color"] = self._sample_pixel_color(image_path, fused_bbox)
        fused["votes"] = len(cluster)
        return fused
    def analyze_layout_consistent(self, image_path: str, n_runs: int = 3, iou_threshold: float = 0.6) -> Optional[Dict[str, Any]]:
        all_elements = []
        metadata = {}
        for i in range(n_runs):
            logger.info(f"正在进行采样 {i+1}/{n_runs}...")
            res,width, height = self.analyze_layout(image_path)
            if res:
                metadata = res.get("metadata", {})
                for elem in res.get("elements", []):
                    elem["_run_id"] = i
                    all_elements.append(elem)
        if not all_elements:
            return None
        clusters = self._cluster_elements(all_elements, iou_threshold=iou_threshold)
        # ✅ 保留更多框的投票阈值设置
        vote_threshold = max(1, int(np.ceil(n_runs / 4)))
        final_elements = []
        for cluster in clusters:
            if len(set(e["_run_id"] for e in cluster)) >= vote_threshold:
                final_elements.append(self._aggregate_cluster(cluster, image_path))
        # ✅ 升级版空间包容性去重 (区分强弱容器)
        # 强包容容器：内部文字需要被合并吸收的（如普通 box）
        strong_container_types = {"box"} 
        # 弱包容容器：只画框架，内部元素需要独立存在的（如 table, coordinate_chart）
        weak_container_types = {"table", "coordinate_chart"} 
        child_types = {"text", "icon"}
        cleaned_elements = []
        # 先按面积降序排序，确保大容器优先
        final_elements.sort(key=lambda e: (e["bbox"][2]-e["bbox"][0]) * (e["bbox"][3]-e["bbox"][1]), reverse=True)
        for elem in final_elements:
            if elem["type"] in child_types:
                is_dominated = False
                for container in cleaned_elements:
                    containment_ratio = self._calculate_containment(container["bbox"], elem["bbox"])
                    # 1. 落入强包容容器：吞并文字，防止重叠
                    if container["type"] in strong_container_types and containment_ratio > 0.85:
                        is_dominated = True
                        if elem["type"] == "text" and elem.get("label"):
                            container["label"] = (container.get("label", "") + "\n" + elem["label"]).strip()
                        logger.info(f"去重: 丢弃被 {container['type']} 包含的 {elem['type']} '{str(elem.get('label', ''))[:20]}...'")
                        break
                    # 2. 落入弱包容容器：区分处理
                    elif container["type"] in weak_container_types and containment_ratio > 0.85:
                        # 如果是 table 内的 text，吞并（因为 table 有专门的 cells 渲染）
                        if container["type"] == "table":
                            is_dominated = True
                            logger.info(f"去重: 丢弃被 table 包含的 {elem['type']} '{str(elem.get('label', ''))[:20]}...'")
                            break
                        # 如果是 coordinate_chart 内的 text/icon，保留！让其独立渲染在坐标轴上
                        elif container["type"] == "coordinate_chart":
                            elem["_parent_type"] = container["type"]
                            # 不吞并，跳出内部循环，继续外部判断
                            break
                if not is_dominated:
                    cleaned_elements.append(elem)
            else:
                cleaned_elements.append(elem)
        # ✅ 统一 ID
        for i, elem in enumerate(cleaned_elements):
            elem["id"] = i + 1
        logger.info(f"分析完成。原始总元素: {len(all_elements)} -> 聚合后: {len(final_elements)} -> 空间去重后: {len(cleaned_elements)}")
        return {
            "metadata": metadata,
            "elements": cleaned_elements,
            "config": {"n_runs": n_runs, "model": self.model}
        },width, height
    def save_layout(self, data: Dict, output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
# =========================
# 运行逻辑
# =========================
# if __name__ == "__main__":
#     api_key = os.getenv("DASHSCOPE_API_KEY")
#     test_image = "test_figure.png"
#     if not api_key:
#         print("请通过环境变量设置 DASHSCOPE_API_KEY")
#     else:
#         analyst = MultiRunVLMAnalyst(api_key=api_key)
#         layout_drawer = analyst.analyze_layout_consistent(
#             test_image,
#             n_runs=5,
#             iou_threshold=0.55
#         )
#         if layout_drawer:
#             output_path = "assets/layout.json"
#             analyst.save_layout(layout_drawer, output_path)
#             print("-" * 30)
#             print(f"✅ 素材抽屉已构建完毕：{output_path}")