from fastapi import APIRouter

from backend.api.routes import auth, chat, documents, museum, sessions

router = APIRouter()
router.include_router(auth.router)
router.include_router(sessions.router)
router.include_router(chat.router)
router.include_router(documents.router)
router.include_router(museum.router)
