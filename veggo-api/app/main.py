import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import close_mongo_connection, connect_to_mongo, db_wrapper
from app.routes import (
    addresses,
    admin,
    agent,
    auth,
    banners,
    cart,
    categories,
    coupons,
    delivery,
    favorites,
    home,
    notifications,
    orders,
    products,
    reviews,
    search,
    users,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("veggo.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    logger.info("Initializing Veggo API 🇱🇰...")
    await connect_to_mongo()
    yield
    logger.info("Shutting down Veggo API...")
    await close_mongo_connection()


app = FastAPI(
    title="VEGGO Sri Lanka Grocery API",
    description="Production-ready Online Vegetable & Grocery Ordering Platform API for Sri Lanka 🇱🇰",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Configuration
origins = settings.ALLOWED_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers for standard consistent error payloads
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "success" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(detail),
            "error_code": f"HTTP_{exc.status_code}"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Validation error")
    loc = ".".join(str(l) for l in first_error.get("loc", []))
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": f"{loc}: {msg}" if loc else msg,
            "error_code": "VALIDATION_ERROR",
            "details": errors
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled internal server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An internal server error occurred. Please try again later.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )


# Root and Health Checks
@app.get("/", tags=["Health"], summary="API Root Status")
async def root():
    return {
        "name": "Veggo API",
        "version": "1.0.0",
        "status": "online",
        "country": "Sri Lanka 🇱🇰",
        "docs": "/docs",
        "port": int(os.getenv("PORT", settings.PORT))
    }


@app.get("/health", tags=["Health"], summary="Health Check")
async def health_check():
    db_status = "healthy"
    try:
        if db_wrapper.client:
            await db_wrapper.client.admin.command('ping')
        else:
            db_status = "not_connected"
    except Exception:
        db_status = "unreachable"

    return {
        "api": "healthy",
        "database": db_status
    }


# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(home.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(search.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(addresses.router)
app.include_router(delivery.router)
app.include_router(favorites.router)
app.include_router(reviews.router)
app.include_router(coupons.router)
app.include_router(notifications.router)
app.include_router(banners.router)
app.include_router(agent.router)
app.include_router(admin.router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run("app.main:app", host=settings.HOST, port=port, reload=True)
