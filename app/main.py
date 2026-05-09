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
from app.api.UserJournal import router as users_router

import logging


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



@app.get("/test")
def home():
    # Проверка RDKit: превращаем SMILES бензола в каноничный
    m = Chem.MolFromSmiles("c1ccccc1")
    canonical = Chem.MolToSmiles(m)
    logger.info("TEST")
    print("--- TEST PRINT: This should also appear in Loki ---")
    return {"status": "online", "rdkit_check": canonical}

@app.get("/version")
async def get_version():
    return {"version": __version__}

@app.get("/test-ip")
async def test_ip(request: Request):
    # 1. То, что определил FastAPI/Uvicorn
    internal_detected_ip = request.client.host

    # 2. То, что прислал Cloudflare (самый надежный вариант)
    cf_ip = request.headers.get("cf-connecting-ip")

    # 3. Весь список прокси
    forwarded_for = request.headers.get("x-forwarded-for")

    return {
        "fastapi_detected_ip": internal_detected_ip,
        "cloudflare_real_ip": cf_ip,
        "full_x_forwarded_for": forwarded_for
    }


def get_real_ip(request: Request) -> str:
    # Сначала ищем заголовок Cloudflare
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip

    # Если его нет (локальная разработка), берем обычный IP
    return request.client.host