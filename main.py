import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from src.bill.routes import router as router_bill
from src.category.routes import router as router_category
from src.db.main import init_db
from src.index.routes import router as router_index
from src.middleware import register_middleware
from src.shop.routes import router as router_shop
from src.user.routes import router as router_user
from src.telegram.routes import router as router_telegram

# Załaduj zmienne środowiskowe
load_dotenv()

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/app.log'),
        logging.StreamHandler()
    ]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    await init_db()
    yield
    print("Shutting down...")

version = "v1"

app = FastAPI(
    version=version, 
    title="Bills API", 
    description="API for managing bills")

register_middleware(app)

app.include_router(router_bill, prefix=f"/api/{version}")
app.include_router(router_category, prefix=f"/api/{version}")
app.include_router(router_index, prefix=f"/api/{version}")
app.include_router(router_shop, prefix=f"/api/{version}")
app.include_router(router_user, prefix=f"/api/{version}")
app.include_router(router_telegram, prefix="/telegram")