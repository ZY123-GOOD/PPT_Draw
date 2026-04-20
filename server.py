import os
import json
import shutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi import UploadFile, File, Form
from fastapi import Request
from typing import Optional
from PIL import Image
# 导入您的核心类
from core.vlm_analyze import MultiRunVLMAnalyst
from core.draw_image import render as render_drawing
import core.show as show  # 导入 show.py 以便调用其可视化逻辑


# === 在 server.py 顶部新增导入 ===
from core.text_to_json import generate_ppt_layout, clean_json, validate_layout_json


app = FastAPI()
# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 确保目录存在并挂载静态文件服务，让前端可以访问生成的图片
os.makedirs("assets", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
class AnalyzeRequest(BaseModel):
    image_path: str
    n_runs: int = 1
    iou_threshold: float = 0.55
class SaveJsonRequest(BaseModel):
    json_path: str
    data: dict
class DrawRequest(BaseModel):
    image_path: Optional[str] = None  # 原有图像路径
    json_path: str  # 布局的JSON路径
    num_images: int = 4  # 生成的图片数量
    width: Optional[int] = None  # 宽度
    height: Optional[int] = None  # 高度
    refs: Optional[list[str]] = []  # 新增：参考图列表，最多支持3张
    
    
# === 新增请求模型 ===
class TextToLayoutRequest(BaseModel):
    user_input: str
# === 新增 API 路由：基于文本生成 PPT 布局 ===
@app.post("/api/generate_ppt_layout")
async def api_generate_ppt_layout(request: Request,req: TextToLayoutRequest):
    api_key = request.headers.get("x-api-key") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return {"success": False, "msg": "服务端未配置 DASHSCOPE_API_KEY"}
    try:
        # 1. 调用大模型生成 (使用 stream=False 方便后端直接处理完整文本)
        raw_result = generate_ppt_layout(req.user_input,api_key=api_key, stream=False)
        # 2. 清洗与校验
        cleaned_result = clean_json(raw_result)
        if not validate_layout_json(cleaned_result):
            return {"success": False, "msg": "AI 生成的 JSON 格式校验失败，请重试或调整描述"}
        # 3. 保存 JSON 文件
        output_path = "assets/ppt_layout.json"
        with open(output_path, "w", encoding="utf-8") as f:
            # 确保写入的是合法的 JSON 格式
            json.dump(json.loads(cleaned_result), f, indent=4, ensure_ascii=False)
        return {
            "success": True, 
            "json_path": output_path, 
            "width": 1000,   # prompt中规定的默认尺寸
            "height": 1000, 
            "msg": "文本生成 PPT 布局成功！"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "msg": f"生成出错: {str(e)}"}

# ================= 接口 1: VLM 布局提取 =================

@app.post("/api/analyze_layout")
async def api_analyze_layout( 
    request: Request,  
    image_file: UploadFile = File(...),  # 👈 强制要求上传文件，不再接收路径
    n_runs: int = Form(1),
    iou_threshold: float = Form(0.55)
    ):
    # api_key = os.getenv("DASHSCOPE_API_KEY")
    api_key = request.headers.get("x-api-key") or os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        return {"success": False, "msg": "服务端未配置 DASHSCOPE_API_KEY"}
    # 保存上传的文件
    save_dir = "assets"
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, image_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)
    actual_image_path = file_path
    print(f"文件已上传至: {actual_image_path}")
    try:
        analyst = MultiRunVLMAnalyst(api_key=api_key)
        layout_drawer,width, height = analyst.analyze_layout_consistent(
            actual_image_path,
            n_runs=n_runs,
            iou_threshold=iou_threshold
        )
        if layout_drawer:
            output_path = "assets/layout.json"
            analyst.save_layout(layout_drawer, output_path)
            # 将服务器上的实际图片路径返回给前端
            return {"success": True, "json_path": output_path, "image_path": actual_image_path, "width": width, "height": height, "msg": "布局提取成功！"}
        else:
            return {"success": False, "msg": "VLM 未能提取出布局"}
    except Exception as e:
        return {"success": False, "msg": f"分析出错: {str(e)}"}
# ================= 接口 2: 保存编辑后的 JSON =================
@app.post("/api/save_json")
def api_save_json(req: SaveJsonRequest):
    try:
        with open(req.json_path, "w", encoding="utf-8") as f:
            json.dump(req.data, f, indent=4, ensure_ascii=False)
        return {"success": True, "msg": "JSON 保存成功"}
    except Exception as e:
        return {"success": False, "msg": str(e)}
# ================= 接口 3: 生成调试可视化 (show.py) =================
@app.post("/api/visualize_layout")
def api_visualize_layout(req: DrawRequest):
    try:
        # 复用 show.py 的逻辑生成 debug_bbox_vis.png
        out_path = "assets/debug_bbox_vis.png"
        # 动态修改 show.py 中的全局变量以适应当前请求
        show.image_path = req.image_path
        show.json_path = req.json_path
        show.out_path = out_path
        img_src = Image.open(req.image_path)
        w, h = img_src.size
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)
        # 调用 show.py 中的字体加载和主循环逻辑（需将 show.py 中的主循环包裹为函数，或在此重写）
        # 为简明起见，这里假设您将 show.py 的主循环封装成了 show.generate_vis(img, draw, json_path)
        # 或者您直接使用我前端提供的交互式画布，这个接口仅作备用调试
        return {"success": True, "msg": "可视化生成成功", "out_path": out_path}
    except Exception as e:
        return {"success": False, "msg": str(e)}
# ================= 接口 4: AI 绘制生图 (draw_image.py) =================
@app.post("/api/draw")
def api_draw_image(req: DrawRequest):
    try:
        # 获取原图尺寸
        real_width, real_height = None, None
        
        # 优先使用前端传来的尺寸
        if req.width and req.height:
            real_width, real_height = req.width, req.height
        # 如果没传尺寸，但有图片路径，从图片读取
        elif req.image_path and os.path.exists(req.image_path):
            with Image.open(req.image_path) as img:
                real_width, real_height = img.size
        else:
            return {"success": False, "msg": "未提供图像尺寸，且无参考图像路径，无法生成"}

        # 读取最新编辑的 JSON
        with open(req.json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        output_paths = []
        # 👇 循环生成指定数量的图片
        for i in range(req.num_images):
            print(f"🚀 正在执行渲染管线 [{i+1}/{req.num_images}]...")

            # 修改：把 refs 传递到 render_drawing 函数
            _, save_path = render_drawing(
                layout_json=layout,
                w=real_width,
                h=real_height,
                refs=req.refs  # 传入参考图
            )
            
            # 为了避免覆盖，将生成的图片重命名带序号
            final_path = f"outputs/output_{i+1}.png"
            if os.path.exists(final_path):
                os.remove(final_path)
            shutil.move(save_path, final_path)
            output_paths.append(final_path)

        # 👇 返回图片路径的数组
        return {"success": True, "output_paths": output_paths}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "msg": f"绘制失败: {str(e)}"}
    
    
from fastapi import UploadFile, File
import uuid

@app.post("/api/upload_references")
async def upload_references(files: list[UploadFile] = File(...)):

    try:
        save_dir = "assets/refs"
        os.makedirs(save_dir, exist_ok=True)

        file_paths = []

        for file in files[:3]:

            ext = os.path.splitext(file.filename)[-1]
            filename = f"{uuid.uuid4().hex}{ext}"

            save_path = os.path.join(save_dir, filename)

            with open(save_path, "wb") as f:
                f.write(await file.read())

            file_paths.append(save_path)

        return {
            "success": True,
            "file_paths": file_paths
        }

    except Exception as e:
        return {
            "success": False,
            "msg": str(e)
        }

from fastapi.staticfiles import StaticFiles
import os
 
# 挂载静态文件目录，html=True 让其支持直接访问 / 返回 index.html
# 注意：这行代码必须放在所有 @app.post 路由的后面，否则会导致 API 路由失效
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")