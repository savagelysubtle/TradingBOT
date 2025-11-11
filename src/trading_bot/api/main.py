"""FastAPI main application for trading bot API."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi import status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from trading_bot.api.bot_instance import clear_bot, set_bot
from trading_bot.api.routes import backtest, data, status, strategies
from trading_bot.bot import TradingBot
from trading_bot.config import load_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    startup_time = time.time()
    logger.info("=" * 80)
    logger.info("Starting Trading Bot API Server")
    logger.info("=" * 80)
    try:
        logger.info("Loading configuration...")
        config = load_config()
        logger.info(
            f"Configuration loaded successfully: "
            f"exchange={config.exchange_id}, "
            f"data_provider={config.data_provider}, "
            f"sandbox={config.exchange_sandbox}, "
            f"log_level={config.log_level}"
        )
        logger.info("Initializing TradingBot instance...")
        bot = TradingBot(config=config)
        set_bot(bot)
        init_time = time.time() - startup_time
        logger.info(f"Trading Bot initialized successfully in {init_time:.2f}s")
        logger.info(
            f"Bot configuration: exchange={bot.config.exchange_id}, provider={bot.config.data_provider}"
        )
    except Exception as e:
        logger.exception(f"CRITICAL: Failed to initialize Trading Bot: {e}")
        logger.warning("Server starting without bot instance - some endpoints may not work")
        logger.warning("Endpoints will return 503 (Service Unavailable) until bot is initialized")
    finally:
        total_startup_time = time.time() - startup_time
        logger.info(f"Server startup completed in {total_startup_time:.2f}s")
        logger.info("Trading Bot API ready to accept requests on http://0.0.0.0:8000")
        logger.info("API documentation available at http://localhost:8000/docs")
        logger.info("=" * 80)

    try:
        yield
    finally:
        shutdown_start = time.time()
        logger.info("=" * 80)
        logger.info("Shutting down Trading Bot API Server")
        logger.info("=" * 80)
        try:
            clear_bot()
            logger.info("Bot instance cleared successfully")
        except Exception as e:
            logger.exception(f"Error clearing bot instance during shutdown: {e}")
        shutdown_time = time.time() - shutdown_start
        logger.info(f"Shutdown completed in {shutdown_time:.2f}s")
        logger.info("=" * 80)


app = FastAPI(
    title="Trading Bot API",
    description="REST API for algorithmic trading bot",
    version="0.1.0",
    lifespan=lifespan,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses with detailed information."""
    # Log immediately at the start - even before generating request ID
    try:
        logger.info(f"→ INCOMING REQUEST: {request.method} {request.url.path}")
    except Exception:
        pass  # If logging fails, continue anyway

    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    try:
        client_ip = request.client.host if request.client else "unknown"
    except Exception:
        client_ip = "unknown"

    try:
        user_agent = request.headers.get("user-agent", "unknown")[:50]
    except Exception:
        user_agent = "unknown"

    try:
        query_params = dict(request.query_params) if request.query_params else {}
    except Exception:
        query_params = {}

    try:
        logger.info(
            f"[{request_id}] → {request.method} {request.url.path} | "
            f"Client: {client_ip} | "
            f"Query: {query_params} | "
            f"User-Agent: {user_agent}"
        )
    except Exception as log_err:
        # If logging fails, at least try to log the error
        try:
            print(f"ERROR: Failed to log request: {log_err}")
        except Exception:
            pass

    try:
        logger.debug(f"[{request_id}] Processing request...")
        response = await call_next(request)
        process_time = time.time() - start_time
        status_emoji = (
            "✅"
            if 200 <= response.status_code < 300
            else "⚠️"
            if 300 <= response.status_code < 400
            else "❌"
        )
        try:
            content_length = response.headers.get("content-length", "unknown")
        except Exception:
            content_length = "unknown"

        try:
            logger.info(
                f"[{request_id}] {status_emoji} {request.method} {request.url.path} | "
                f"Status: {response.status_code} | "
                f"Time: {process_time:.3f}s | "
                f"Size: {content_length} bytes"
            )
        except Exception:
            pass  # If logging fails, continue anyway

        return response
    except Exception as e:
        process_time = time.time() - start_time
        try:
            logger.exception(
                f"[{request_id}] ❌ {request.method} {request.url.path} | "
                f"Error: {type(e).__name__}: {e!s} | "
                f"Time: {process_time:.3f}s"
            )
        except Exception:
            # If logging fails, at least print to console
            try:
                print(f"ERROR [{request_id}]: {type(e).__name__}: {e!s}")
            except Exception:
                pass
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    error_id = str(uuid.uuid4())[:8]
    logger.exception(
        f"[ERROR-{error_id}] Unhandled exception in {request.method} {request.url.path} | "
        f"Type: {type(exc).__name__} | "
        f"Error: {exc!s} | "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    return JSONResponse(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
        },
    )


# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(
        f"Validation error in {request.method} {request.url.path} | "
        f"Errors: {len(exc.errors())} validation issue(s) | "
        f"Details: {exc.errors()}"
    )
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method,
        },
    )


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
logger.info("Registering API routes...")
app.include_router(status.router, prefix="/api", tags=["status"])
logger.debug("Status router registered")
app.include_router(strategies.router, prefix="/api", tags=["strategies"])
logger.debug("Strategies router registered")
app.include_router(data.router, prefix="/api", tags=["data"])
logger.debug("Data router registered")
app.include_router(backtest.router, prefix="/api", tags=["backtest"])
logger.debug("Backtest router registered")
logger.info("All API routes registered successfully")


@app.get("/")
async def root():
    """Root endpoint."""
    logger.debug("Root endpoint accessed")
    return {"message": "Trading Bot API", "version": "0.1.0"}


def main():
    """Main entry point for API server."""
    import uvicorn

    logger.info("Starting uvicorn server...")
    logger.info("Server configuration: host=0.0.0.0, port=8000")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,  # Use our own logging configuration
        access_log=True,
    )


if __name__ == "__main__":
    main()
