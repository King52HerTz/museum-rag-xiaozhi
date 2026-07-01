"""文本向量化服务 - 只支持密集向量（由 Milvus 2.5+ 原生支持中文分词与 BM25 全文检索）"""
import logging
import os
from threading import Lock

from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


def _create_dense_embedder() -> HuggingFaceEmbeddings:
    model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    device = os.getenv("EMBEDDING_DEVICE", "cpu")
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )


class EmbeddingService:
    """文本向量化服务 - 密集向量本地模型"""

    def __init__(self, state_path=None):
        # 模型改为懒加载，避免服务启动阶段阻塞端口监听。
        self._embedder = None
        self._embedder_lock = Lock()

    def _get_embedder(self) -> HuggingFaceEmbeddings:
        if self._embedder is not None:
            return self._embedder

        with self._embedder_lock:
            if self._embedder is None:
                model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
                device = os.getenv("EMBEDDING_DEVICE", "cpu")
                logger.info("loading embedding model lazily | model=%s | device=%s", model_name, device)
                self._embedder = _create_dense_embedder()
                logger.info("embedding model loaded | model=%s | device=%s", model_name, device)
        return self._embedder

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return self._get_embedder().embed_documents(texts)
        except Exception as e:
            raise Exception(f"本地密集嵌入模型调用失败: {str(e)}") from e


# 全进程唯一实例
embedding_service = EmbeddingService()
