# PPT_Draw

[English](README.md) | 简体中文

> AI 驱动的 PPT 页面结构化解析、交互编辑与智能绘图系统

PPT_Draw 是一个结合 **多模态视觉模型（VLM）+ 大语言模型（LLM）+ AI 图像生成** 的智能设计平台。
支持从 **图片提取 PPT 布局**、**文本生成 PPT 页面结构**、**在线拖拽编辑版式**、**批量生成视觉设计稿** 的完整工作流。

---

# ✨ 项目特色

✅ 图片一键识别 PPT 页面布局
✅ 文本描述直接生成 PPT 页面结构
✅ 浏览器在线拖拽编辑布局元素
✅ 支持参考图控制视觉风格
✅ 一键批量生成多套设计方案
✅ 前后端分离，易部署，易扩展

---

# 🎯 项目定位

传统 PPT 制作存在以下痛点：

* 排版耗时
* 设计门槛高
* 风格统一困难
* 内容转视觉效率低

PPT_Draw 通过 AI 自动完成：

```text id="p0u7e4"
内容输入
   ↓
结构化布局生成
   ↓
可视化编辑
   ↓
AI 智能绘图
   ↓
高质量 PPT 页面产出
```

适用于：

* 商务汇报
* 产品发布会
* 教学课件
* 论文展示
* 数据分析汇报
* AI 内容创作平台

---

# 🧠 系统功能总览

# 1️⃣ 图片解析布局（Image → Layout）

上传 PPT 页面截图，系统自动识别：

* 标题区
* 文本块
* 图片区域
* 表格
* 坐标图
* 模块结构

输出标准 JSON：

```json id="w6jc2r"
{
  "elements":[
    {
      "id":1,
      "type":"text",
      "bbox":[80,60,920,180],
      "label":"标题区域"
    }
  ]
}
```

---

# 2️⃣ 文本生成布局（Text → Layout）

输入一句需求：

```text id="8lh3gk"
做一个 RLHF vs DPO 的对比 PPT，用表格+坐标图展示差异
```

系统自动生成结构化 PPT 页面布局。

---

# 3️⃣ 在线编辑布局（Layout Editor）

支持在浏览器中实时编辑布局：

### 元素交互能力：

✅ 拖拽移动
✅ 八方向缩放
✅ 修改文字内容
✅ 修改绘图提示词
✅ Delete 删除元素
✅ 上传本地 JSON
✅ 下载 JSON

---

# 4️⃣ AI 绘图生成（Layout → Design）

根据布局 JSON 自动生成 PPT 页面视觉稿。

支持：

* 批量生成 1～6 张方案
* 自定义尺寸
* 上传参考图（最多3张）
* 多方案对比选择

输出示例：

```text id="4w6g2s"
方案1.png
方案2.png
方案3.png
...
```

---

# 🏗️ 系统架构

```text id="9jv0q2"
                 ┌──────────────┐
                 │ 前端工作台 UI │
                 └──────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │ FastAPI 后端服务 │
                └──────┬────────┘
                       │
     ┌─────────────────┼─────────────────┐
     ▼                 ▼                 ▼
布局识别模块       文本生成模块       AI绘图模块
(VLM)             (LLM)             (Image Gen)
```

---

# 💻 技术栈

# 后端

* FastAPI
* Uvicorn
* Pydantic
* Pillow

# 前端

* HTML5
* CSS3
* JavaScript（原生）
* DOM 可视化编辑器

# AI 能力

* 多模态视觉识别模型（VLM）
* 大语言模型（Layout JSON Generation）
* 文生图模型（Image Generation）

---

# 📁 项目结构

```bash id="c0hv3r"
PPT_Draw/
│── server.py                 # FastAPI 主服务
│
├── core/
│   ├── vlm_analyze.py        # 图片布局识别
│   ├── text_to_json.py       # 文本生成布局
│   ├── draw_image.py         # AI 绘图
│   └── show.py              # 调试可视化
│
├── static/
│   └── index.html           # 前端工作台
│
├── assets/
│   ├── layout.json
│   ├── ppt_layout.json
│   └── refs/
│
├── outputs/
│   ├── output_1.png
│   ├── output_2.png
│   └── ...
│
├── requirements.txt
└── README.md
```

---

# 🚀 快速开始

# 1. 克隆项目

```bash id="n9wyiu"
git clone https://github.com/yourname/PPT_Draw.git
cd PPT_Draw
```

---

# 2. 安装依赖

```bash id="z4v4f4"
pip install -r requirements.txt
```

---

# 3. 配置 API Key

项目使用 DashScope / 模型服务：

```bash id="f4u4v7"
DASHSCOPE_API_KEY=your_api_key
```

Windows：

```bash id="4d5r8s"
set DASHSCOPE_API_KEY=your_api_key
```

Linux / macOS：

```bash id="o2z5d1"
export DASHSCOPE_API_KEY=your_api_key
```

---

# 4. 启动项目

```bash id="r7p6b2"
uvicorn server:app --reload
```

访问：

```bash id="w3u0c9"
http://127.0.0.1:8000
```

---

# 🖥️ 前端界面说明

系统采用左右双栏工作台设计。

---

# 左侧控制台

## Step 1：布局提取 / 生成

### 📷 图片识别布局

上传 PPT 页面图片，自动提取结构。

参数：

* n_runs（多次采样）
* iou_threshold（一致性阈值）

### 📝 文本生成布局

输入需求描述，自动生成 PPT 页面结构。

---

## Step 2：交互编辑器

### 支持：

* 加载布局 JSON
* 拖拽元素
* Resize 调整大小
* 修改标题文字
* 修改绘图提示词
* 删除元素
* 下载 JSON

---

## Step 3：绘图生成

参数：

* 图像宽度
* 图像高度
* 生成数量（1~6）
* 上传参考图（最多3张）

点击：

```text id="z9u4h2"
🎨 批量绘制图像
```

---

# 右侧结果区

展示 AI 输出多套方案画廊。

---

# 🔌 API 接口文档

FastAPI 自动生成文档：

```text id="f7w1q3"
http://127.0.0.1:8000/docs
```

---

# 核心接口

## 1. 图片提取布局

```http id="r9m8q4"
POST /api/analyze_layout
```

FormData：

* image_file
* n_runs
* iou_threshold

---

## 2. 文本生成布局

```http id="s1m7c4"
POST /api/generate_ppt_layout
```

```json id="v4n2h8"
{
  "user_input":"科技风融资路演首页"
}
```

---

## 3. 保存 JSON

```http id="j4r6x9"
POST /api/save_json
```

---

## 4. AI 绘图

```http id="p3x9k2"
POST /api/draw
```

```json id="t4y7v3"
{
  "json_path":"assets/layout.json",
  "width":1920,
  "height":1080,
  "num_images":4,
  "refs":[]
}
```

---

## 5. 上传参考图

```http id="q9f5b1"
POST /api/upload_references
```

---

# 📌 使用流程

# 方式一：参考图生成

```text id="f6k8v0"
上传 PPT 图片
→ 自动识别布局
→ 编辑优化
→ AI生成页面
```

---

# 方式二：文本生成

```text id="e1d9n5"
输入一句话需求
→ 自动生成结构
→ 编辑优化
→ 输出设计稿
```

---

# 🎨 JSON 布局说明

坐标系统一使用：

```text id="x6p0a3"
1000 × 1000
```

示例：

```json id="m2q7w4"
{
  "id":2,
  "type":"box",
  "bbox":[100,200,900,600],
  "label":"图片区"
}
```

---

# 📦 输出目录

生成图片保存在：

```bash id="u8r2z7"
outputs/output_1.png
outputs/output_2.png
outputs/output_3.png
```

---

# 🔒 安全说明

请妥善保管你的 API Key，建议通过环境变量配置，不要提交到 Git 仓库。

---

# 🛣️ 后续规划

* 导出 PPTX 文件
* 多页 PPT 自动生成
* 企业模板库
* 团队协同编辑
* 云端 SaaS 部署
* 品牌风格训练

---

# 🤝 贡献方式

欢迎提交：

* Issue
* Pull Request
* 功能建议
* UI 优化方案
* Prompt 优化

---

# 👨‍💻 作者

Yao Zhu  

>学术主页 https://scholar.google.com/citations?user=Te8bmo0AAAAJ&hl=zh-CN

---

# 📄 License

MIT License

---

# ⭐ 如果你喜欢这个项目

欢迎 Star 支持一下！
