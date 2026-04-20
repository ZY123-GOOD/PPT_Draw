# PPT_Draw

[简体中文](README_CN.md) | English

> AI-powered PPT page structure parsing, interactive editing, and intelligent design generation system

PPT_Draw is an intelligent design platform powered by **Vision-Language Models (VLMs)**, **Large Language Models (LLMs)**, and **AI image generation models**.

It provides a complete workflow for:

* Extracting PPT layouts from images
* Generating PPT page structures from text prompts
* Editing layouts interactively in the browser
* Batch generating polished visual slide designs

---

# ✨ Features

✅ One-click PPT layout extraction from images
✅ Generate slide structure directly from text prompts
✅ Drag-and-drop layout editor in browser
✅ Reference-image guided style control
✅ Batch generation of multiple design candidates
✅ Frontend/backend decoupled architecture, easy to deploy and extend

---

# 🎯 Why PPT_Draw?

Traditional PPT creation often suffers from:

* Time-consuming layout work
* High design barrier
* Inconsistent visual style
* Low efficiency turning ideas into slides

PPT_Draw automates the process:

```text
Content Input
     ↓
Structured Layout Generation
     ↓
Visual Editing
     ↓
AI Design Rendering
     ↓
High-quality PPT Output
```

Use cases:

* Business presentations
* Product launches
* Educational slides
* Academic presentations
* Data reports
* AI content creation platforms

---

# 🧠 Core Functions

# 1️⃣ Image → Layout

Upload a PPT screenshot or slide image. The system automatically detects:

* Title area
* Text blocks
* Image regions
* Tables
* Charts / coordinate systems
* Overall modular structure

Outputs standardized JSON:

```json
{
  "elements":[
    {
      "id":1,
      "type":"text",
      "bbox":[80,60,920,180],
      "label":"Title Area"
    }
  ]
}
```

---

# 2️⃣ Text → Layout

Input a requirement such as:

```text
Create a comparison slide for RLHF vs DPO using a table and coordinate chart.
```

The system automatically generates a structured PPT page layout.

---

# 3️⃣ Interactive Layout Editor

Edit layouts directly in the browser.

### Supported interactions:

✅ Drag and move elements
✅ 8-direction resize handles
✅ Edit labels/text
✅ Edit drawing instructions
✅ Delete elements
✅ Upload local JSON
✅ Download current JSON

---

# 4️⃣ Layout → Design

Generate visual slide designs automatically based on layout JSON.

Supports:

* Batch generation of 1–6 results
* Custom width / height
* Upload up to 3 reference images
* Compare multiple generated options

Example outputs:

```text
design_1.png
design_2.png
design_3.png
...
```

---

# 🏗️ Architecture

```text
                ┌────────────────────┐
                │ Frontend Workspace │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ FastAPI Backend    │
                └─────────┬──────────┘
                          │
     ┌────────────────────┼────────────────────┐
     ▼                    ▼                    ▼
Layout Parsing       Text Generation      AI Rendering
(VLM)                (LLM)               (Image Gen)
```

---

# 💻 Tech Stack

## Backend

* FastAPI
* Uvicorn
* Pydantic
* Pillow

## Frontend

* HTML5
* CSS3
* Vanilla JavaScript
* DOM-based visual editor

## AI Modules

* Vision-Language Models (VLM)
* Large Language Models (Layout JSON generation)
* Text-to-Image Models

---

# 📁 Project Structure

```bash
PPT_Draw/
│── server.py                 # FastAPI main server
│
├── core/
│   ├── vlm_analyze.py        # Image layout extraction
│   ├── text_to_json.py      # Text-to-layout generation
│   ├── draw_image.py        # AI rendering
│   └── show.py             # Debug visualization
│
├── static/
│   └── index.html          # Frontend workspace
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

# 🚀 Quick Start

## 1. Clone Repository

```bash
git clone https://github.com/yourname/PPT_Draw.git
cd PPT_Draw
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure API Key

This project uses DashScope / model services:

```bash
DASHSCOPE_API_KEY=your_api_key
```

Windows:

```bash
set DASHSCOPE_API_KEY=your_api_key
```

Linux / macOS:

```bash
export DASHSCOPE_API_KEY=your_api_key
```

---

## 4. Run the Project

```bash
uvicorn server:app --reload
```

Visit:

```text
http://127.0.0.1:8000
```

---

# 🖥️ Frontend Interface

The UI uses a dual-panel workspace layout.

---

# Left Panel

## Step 1: Layout Extraction / Generation

### 📷 Extract from Image

Upload a slide image and detect page structure automatically.

Parameters:

* `n_runs` (multi-run sampling)
* `iou_threshold` (consistency threshold)

### 📝 Generate from Text

Enter your slide requirement and generate layout automatically.

---

## Step 2: Interactive Editor

Supports:

* Load JSON layout
* Drag elements
* Resize elements
* Edit labels
* Edit drawing prompts
* Delete elements
* Download JSON

---

## Step 3: Design Generation

Parameters:

* Width
* Height
* Number of outputs (1–6)
* Upload reference images (up to 3)

Click:

```text
🎨 Generate Designs
```

---

# Right Panel

Displays generated design gallery.

---

# 🔌 API Documentation

FastAPI auto-generated docs:

```text
http://127.0.0.1:8000/docs
```

---

# Main APIs

## 1. Analyze Layout

```http
POST /api/analyze_layout
```

FormData:

* image_file
* n_runs
* iou_threshold

---

## 2. Generate PPT Layout

```http
POST /api/generate_ppt_layout
```

```json
{
  "user_input":"Create a futuristic startup pitch deck cover slide"
}
```

---

## 3. Save JSON

```http
POST /api/save_json
```

---

## 4. Draw Designs

```http
POST /api/draw
```

```json
{
  "json_path":"assets/layout.json",
  "width":1920,
  "height":1080,
  "num_images":4,
  "refs":[]
}
```

---

## 5. Upload Reference Images

```http
POST /api/upload_references
```

---

# 📌 Workflow

## Method 1: From Reference Slide

```text
Upload PPT Image
→ Detect Layout
→ Edit Structure
→ Generate Designs
```

---

## Method 2: From Text Prompt

```text
Enter Requirement
→ Generate Layout
→ Edit Structure
→ Output Final Designs
```

---

# 🎨 Layout JSON Coordinate System

All coordinates use:

```text
1000 × 1000
```

Example:

```json
{
  "id":2,
  "type":"box",
  "bbox":[100,200,900,600],
  "label":"Image Area"
}
```

---

# 📦 Output Directory

Generated images are saved in:

```bash
outputs/output_1.png
outputs/output_2.png
outputs/output_3.png
```

---

# 🔒 Security Notes

Please keep your API key secure.
Use environment variables and do not commit secrets to Git repositories.

---

# 🛣️ Roadmap

* Export to PPTX
* Multi-page PPT generation
* Enterprise template library
* Team collaboration
* Cloud SaaS deployment
* Brand-style fine-tuning

---

# 🤝 Contributing

Contributions are welcome via:

* Issues
* Pull Requests
* Feature requests
* UI improvements
* Prompt engineering ideas

---

# 👨‍💻 Author

Yao Zhu

Academic Profile:
[https://scholar.google.com/citations?user=Te8bmo0AAAAJ&hl=zh-CN](https://scholar.google.com/citations?user=Te8bmo0AAAAJ&hl=zh-CN)

---

# 📄 License

MIT License

---

# ⭐ If You Like This Project

Please consider giving it a Star!
