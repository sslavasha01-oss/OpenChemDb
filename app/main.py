from fastapi import FastAPI, Request
from rdkit import Chem

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.reactions import router as reactions_router
from app.api.books import router as books_router
from app.api.files import router as files_router
from app.api.evaluations import router as evaluations_router
from app.api.comments import router as comments_router
from app.api.comment_reactions import router as comment_reactions_router
from app.api.register import router as register_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.user_journal import router as users_router
from app.api.journal_attachment import router as journal_attachment

import logging

from app.core.settings import settings

logger = logging.getLogger("uvicorn.error")

__version__ = "0.0.0"
app = FastAPI(title="OpenChemDB",
              version=__version__,
              swagger_ui_parameters={
                  "docExpansion": "list",
                  "tryItOutEnabled": True,
                  "cacheControl": "no-cache",
                  "persistAuthorization": True
              },
              root_path="/api"
              )


# 1. Сначала инициализируем состояние

# 2. Добавляем CORS (она будет "внешним" слоем)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://openchemdb.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
#
app.include_router(reactions_router)
app.include_router(books_router)
app.include_router(files_router)
#
app.include_router(evaluations_router)
#
app.include_router(comments_router)

app.include_router(comment_reactions_router)

app.include_router(register_router, tags=["Register"])

app.include_router(users_router)

app.include_router(journal_attachment)


@app.get("/version")
async def get_version():
    return {"version": __version__}


@app.get("/status")
async def get_status(request: Request):
    return {
        "local_mode": settings.LOCAL_MODE,
        "no_password_login": settings.NO_PASSWORD_LOGIN
    }
