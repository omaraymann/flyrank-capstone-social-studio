from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, history, posts, publishing, variants
from app.config import settings

app = FastAPI(title="Social Media Studio", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(variants.router)
app.include_router(publishing.router)
app.include_router(history.router)


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok"}
