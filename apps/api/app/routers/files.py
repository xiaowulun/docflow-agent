"""
文件 API 路由

提供文件上传和下载接口。
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".docx", ".doc", ".xlsx", ".xls", ".pdf"}


@router.post("/upload")
async def upload_file(file: UploadFile):
    """
    上传文件。

    保存到 storage/files/uploads/ 目录。
    """
    # 检查文件类型
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # 保存文件
    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {
        "filename": file.filename,
        "file_path": str(file_path),
        "size_bytes": file_path.stat().st_size,
    }


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载输出文件。

    从 storage/files/outputs/ 目录读取。
    """
    file_path = settings.output_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )
