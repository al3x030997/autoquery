from fastapi import FastAPI

app = FastAPI(title="AutoQuery API")


@app.get("/health")
async def health():
    return {"status": "ok"}
