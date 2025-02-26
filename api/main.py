from fastapi import FastAPI
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

app = FastAPI()
app.include_router(router) 