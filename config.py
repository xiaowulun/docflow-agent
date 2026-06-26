"""
全局配置

从 .env 文件读取环境变量，提供统一的配置访问入口。
使用方式：from config import settings
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，所有值从环境变量或 .env 文件读取"""

    # LLM 配置（兼容 OpenAI 接口）
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # 存储路径
    storage_dir: Path = Path("storage/files")
    sqlite_path: Path = Path("storage/db/office_agent.db")

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 便捷属性
    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def output_dir(self) -> Path:
        return self.storage_dir / "outputs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局单例
settings = Settings()
