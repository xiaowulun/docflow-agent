"""
全局配置

从 .env 文件读取环境变量，提供统一的配置访问入口。
使用方式：from config import settings
"""

from pathlib import Path

from pydantic_settings import BaseSettings

# 项目根目录（config.py 所在目录）
_PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """应用配置，所有值从环境变量或 .env 文件读取"""

    # LLM 配置（兼容 OpenAI 接口）
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # Agnes 视觉模型配置（用于图片生成和分析）
    agnes_api_key: str = ""
    agnes_base_url: str = "https://api.agnes-ai.com/v1"
    agnes_image_model: str = "agnes-image-2.1-flash"
    agnes_vision_model: str = "agnes-vision-1.0"

    # 存储路径（使用绝对路径，避免 cwd 变化导致找不到文件）
    storage_dir: Path = _PROJECT_ROOT / "storage/files"
    sqlite_path: Path = _PROJECT_ROOT / "storage/db/office_agent.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Tavily 搜索
    tavily_api_key: str = ""

    # 飞书配置
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""

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
