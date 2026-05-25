"""WriteWords API — 手写渲染服务。"""

import io
import sys
from pathlib import Path
from typing import Dict, List

# 确保项目根目录在模块搜索路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

from PIL import Image

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.engine.renderer import render_handwriting, RenderOptions
from backend.engine.warper import render_custom_background, render_with_template, load_template_config

app = FastAPI(title="WriteWords", version="0.1.0")

# CORS — 生产环境替换为实际域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 前端构建产物（生产环境）
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend_index():
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")


# 添加 favicon.ico（避免 404）
@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
PRESETS_DIR = Path(__file__).resolve().parent / "presets"


def _get_available_fonts() -> List[Dict[str, str]]:
    """扫描 fonts 目录，返回可用字体列表。"""
    if not FONTS_DIR.exists():
        return []
    fonts = []
    for f in sorted(FONTS_DIR.glob("*.ttf")):
        name = f.stem  # 去掉 .ttf 后缀
        fonts.append({"name": name, "file": f.name})
    return fonts


def _resolve_font_path(font_name: str) -> str:
    """根据字体名称解析完整路径。"""
    fonts = _get_available_fonts()
    if not fonts:
        raise HTTPException(status_code=500, detail="未在 backend/fonts/ 下找到 .ttf 字体文件")

    if font_name:
        for f in fonts:
            if f["name"] == font_name:
                return str(FONTS_DIR / f["file"])
        raise HTTPException(status_code=400, detail=f"字体 '{font_name}' 不存在")

    # 默认返回第一个字体
    return str(FONTS_DIR / fonts[0]["file"])


class RenderRequest(BaseModel):
    """渲染请求体。"""
    text: str = Field(..., min_length=1, max_length=5000, description="待渲染的文本")
    font_name: str = Field("", description="字体名称（空字符串使用默认字体）")
    font_size: int = Field(32, ge=12, le=100)
    line_spacing: float = Field(1.8, ge=-1.0, le=3.0)
    image_width: int = Field(800, ge=200, le=2000)
    image_height: int = Field(600, ge=200, le=2000)
    baseline_drift: int = Field(2, ge=0, le=5)
    kerning_jitter: int = Field(1, ge=0, le=3)
    error_rate: float = Field(0.05, ge=0.0, le=1.0, description="单词错误触发率")
    ink_variation: int = Field(15, ge=0, le=30)


class RenderWithTemplateRequest(BaseModel):
    """模板渲染请求体。"""
    text: str = Field(..., min_length=1, max_length=5000, description="待渲染的文本")
    font_name: str = Field("", description="字体名称（空字符串使用默认字体）")
    font_size: int = Field(48, ge=24, le=200)
    letter_spacing: int = Field(0, ge=-10, le=20, description="字符间距，负值重叠")
    line_spacing: float = Field(1.5, ge=-1.0, le=3.0)
    template_id: str = Field("template_v1", description="模板标识")
    baseline_drift: int = Field(2, ge=0, le=5)
    ink_variation: int = Field(15, ge=0, le=30)
    error_rate: float = Field(0.05, ge=0.0, le=1.0, description="单词错误触发率")
    kerning_jitter: int = Field(1, ge=0, le=3, description="字距随机抖动")


class FontInfo(BaseModel):
    """字体信息。"""
    name: str
    file: str


class HealthResponse(BaseModel):
    """健康检查响应。"""
    status: str = "ok"
    version: str = "0.1.0"


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """健康检查接口。"""
    return HealthResponse()


@app.get("/api/fonts", response_model=List[FontInfo])
async def list_fonts():
    """返回可用字体列表。"""
    return _get_available_fonts()


@app.get("/fonts/{font_name:path}")
async def serve_font(font_name: str):
    """提供字体文件下载。"""
    # 防止路径穿越
    safe_name = Path(font_name).name
    font_path = FONTS_DIR / safe_name
    if not font_path.exists():
        raise HTTPException(status_code=404, detail="字体文件不存在")
    return FileResponse(font_path, media_type="font/ttf")


@app.post("/api/render")
async def render(req: RenderRequest):
    """渲染手写文本图像。

    接受文本和渲染选项，返回 PNG 图像。
    """
    font_path = _resolve_font_path(req.font_name)

    try:
        opts = RenderOptions(
            font_path=font_path,
            font_size=req.font_size,
            line_spacing=req.line_spacing,
            image_width=req.image_width,
            image_height=req.image_height,
            baseline_drift_amplitude=req.baseline_drift,
            kerning_jitter=req.kerning_jitter,
            error_rate=req.error_rate,
            ink_variation=req.ink_variation,
        )
        png_data = render_handwriting(req.text, opts)
        return Response(content=png_data, media_type="image/png")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"字体文件错误: {e}")


@app.get("/api/templates")
async def list_templates():
    """返回可用模板列表。"""
    templates_dir = Path(__file__).resolve().parent / "assets"
    images = list(templates_dir.glob("*.jpg")) + list(templates_dir.glob("*.png"))
    return [{"id": "template_v1", "description": "带标题的照片模板", "image": f.name} for f in images[:1]]


@app.get("/api/presets")
async def list_presets():
    """返回预设背景图片列表。"""
    if not PRESETS_DIR.exists():
        return []
    presets = []
    for f in sorted(PRESETS_DIR.glob("*.jpg")) + sorted(PRESETS_DIR.glob("*.png")):
        presets.append({"name": f.stem, "file": f.name})
    return presets


@app.get("/presets/{file_name:path}")
async def serve_preset(file_name: str):
    """提供预设背景图片。"""
    safe_name = Path(file_name).name
    preset_path = PRESETS_DIR / safe_name
    if not preset_path.exists():
        raise HTTPException(status_code=404, detail="预设图片不存在")
    return FileResponse(preset_path)


@app.post("/api/render/template")
async def render_template(req: RenderWithTemplateRequest):
    """透视变换 + 正片叠底合成渲染。

    在模板背景照片的指定区域渲染手写文本。
    """
    font_path = _resolve_font_path(req.font_name)

    # 查找背景照片
    assets_dir = Path(__file__).resolve().parent / "assets"
    bg_images = list(assets_dir.glob("*.jpg")) + list(assets_dir.glob("*.png"))
    if not bg_images:
        raise HTTPException(status_code=500, detail="未在 backend/assets/ 下找到背景图片")
    background_path = str(bg_images[0])

    try:
        result = render_with_template(
            text=req.text,
            font_path=font_path,
            background_path=background_path,
            template_id=req.template_id,
            font_size=req.font_size,
            letter_spacing=req.letter_spacing,
            line_spacing=req.line_spacing,
            baseline_drift_amplitude=req.baseline_drift,
            ink_variation=req.ink_variation,
            kerning_jitter=req.kerning_jitter,
            error_rate=req.error_rate,
        )
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模板渲染失败: {e}")


@app.post("/api/render/custom")
async def render_custom(
    file: UploadFile = File(..., description="背景图片"),
    text: str = Form(..., min_length=1, max_length=5000),
    font_name: str = Form(""),
    font_size: int = Form(48),
    letter_spacing: int = Form(0),
    line_spacing: float = Form(1.5),
    dst_points: str = Form(None, description="四点坐标 JSON 字符串"),
    baseline_drift: int = Form(2),
    ink_variation: int = Form(15),
    error_rate: float = Form(0.05),
    kerning_jitter: int = Form(1),
    spacing_randomness: float = Form(2.0),
):
    """使用用户上传的背景图进行透视渲染。

    接受 multipart/form-data：图片文件 + 文本参数。
    可选 dst_points 参数（JSON 格式的四点坐标数组）。
    """
    font_path = _resolve_font_path(font_name)

    # 读取上传图片
    image_data = await file.read()
    bg = Image.open(io.BytesIO(image_data)).convert("RGB")

    # 解析自定义 dst_points
    parsed_dst = None
    if dst_points:
        try:
            parsed_dst = json.loads(dst_points)
            if not isinstance(parsed_dst, list) or len(parsed_dst) != 4:
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=400, detail="dst_points 格式无效，应为 [[x,y],[x,y],[x,y],[x,y]]")

    try:
        result = render_custom_background(
            text=text,
            font_path=font_path,
            background=bg,
            dst_points=parsed_dst,
            font_size=font_size,
            letter_spacing=letter_spacing,
            line_spacing=line_spacing,
            baseline_drift_amplitude=baseline_drift,
            ink_variation=ink_variation,
            kerning_jitter=kerning_jitter,
            error_rate=error_rate,
            spacing_randomness=spacing_randomness,
        )
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"自定义渲染失败: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
