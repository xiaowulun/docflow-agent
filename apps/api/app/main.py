"""
FastAPI 应用入口

启动命令：
    uvicorn apps.api.app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.routers import chat, files, tasks
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时确保目录存在
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    yield
    # 关闭时清理（如有需要）


app = FastAPI(
    title="DocFlow Agent",
    description="Office document processing agent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置（前端 Next.js 需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/")
async def root():
    return {"message": "DocFlow Agent API", "version": "0.1.0"}
