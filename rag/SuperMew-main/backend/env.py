"""从项目根目录加载分层 .env；由应用入口或独立脚本在 import 其它 backend 模块前调用一次。"""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOADED = False


def _candidate_env_files() -> list[Path]:
    files: list[Path] = [PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"]
    app_env = os.getenv("APP_ENV", "").strip()
    if app_env:
        files.append(PROJECT_ROOT / f".env.{app_env}")
        files.append(PROJECT_ROOT / f".env.{app_env}.local")
    return files


def load_env() -> None:
    global _LOADED
    if _LOADED:
        return
    for env_file in _candidate_env_files():
        if env_file.exists():
            load_dotenv(env_file, override=True)
    _LOADED = True
