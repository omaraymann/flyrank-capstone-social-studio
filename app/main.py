from fastapi import FastAPI

from app.api import auth, posts, variants

app = FastAPI(title="Social Media Studio", version="0.1.0")
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(variants.router)


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok"}
