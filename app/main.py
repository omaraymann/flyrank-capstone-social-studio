from fastapi import FastAPI

from app.api import auth

app = FastAPI(title="Social Media Studio", version="0.1.0")
app.include_router(auth.router)


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok"}
