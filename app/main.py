from fastapi import FastAPI

from app.api import auth, history, posts, publishing, variants

app = FastAPI(title="Social Media Studio", version="0.1.0")
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(variants.router)
app.include_router(publishing.router)
app.include_router(history.router)


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok"}
