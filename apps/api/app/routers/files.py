"""
文件 API 路由

提供文件上传、下载、列表和删除接口。
支持图片（png/jpg/jpeg/gif/webp/bmp）和文档（word/excel/pdf/ppt/txt/md/csv/json/xml/html）。
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from apps.api.app.services.file_extractor import ALL_ALLOWED, IMAGE_EXTENSIONS
from apps.api.app.services.file_store import get_file_store

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile):
    """
    上传文件。

    支持图片和文档，文档会自动提取文本内容供 LLM 使用。
    返回文件 ID 和提取的文本内容。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALL_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {suffix}。支持: {sorted(ALL_ALLOWED)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 限制文件大小（10MB）
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

    store = get_file_store()
    record = store.save_file(file.filename, content)

    return {
        "id": record.id,
        "filename": record.original_name,
        "file_type": record.file_type,
        "extension": record.extension,
        "file_path": record.file_path,
        "size_bytes": record.size_bytes,
        "extracted_text": record.extracted_text,
    }


@router.get("/list")
async def list_files():
    """列出所有已上传文件"""
    store = get_file_store()
    files = store.list_files()
    return [
        {
            "id": f.id,
            "filename": f.original_name,
            "file_type": f.file_type,
            "extension": f.extension,
            "size_bytes": f.size_bytes,
            "created_at": f.created_at.isoformat(),
        }
        for f in files
    ]


@router.get("/download/{file_id}")
async def download_file(file_id: str):
    """下载文件"""
    store = get_file_store()
    record = store.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    media_type = "image/png" if record.file_type == "image" else "application/octet-stream"
    return FileResponse(
        path=str(file_path),
        filename=record.original_name,
        media_type=media_type,
    )


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """删除文件"""
    store = get_file_store()
    deleted = store.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"deleted": True}
