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

from trading_bot.api.bot_instance import bot_instance, clear_bot, set_bot
from trading_bot.api.routes import backtest, data, monte_carlo, status, strategies
from trading_bot.bot import TradingBot
from trading_bot.config import load_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    startup_time = time.time()
    logger.info("=" * 80)
    logger.info("APPLICATION STARTUP")
    logger.info("=" * 80)

    try:
        logger.info("Step 1: Loading configuration...")
        config = load_config()
        logger.info("Step 1: ✅ Configuration loaded successfully")
        logger.info(f"  - exchange: {config.exchange_id}")
        logger.info(f"  - data_provider: {config.data_provider}")
        logger.info(f"  - sandbox: {config.exchange_sandbox}")
        logger.info(f"  - log_level: {config.log_level}")

        logger.info("Step 2: Initializing TradingBot instance...")
        bot = TradingBot(config=config)
        set_bot(bot)
        init_time = time.time() - startup_time
        logger.info(f"Step 2: ✅ Trading Bot initialized successfully in {init_time:.2f}s")
        logger.info(f"  - Bot exchange: {bot.config.exchange_id}")
        logger.info(f"  - Bot provider: {bot.config.data_provider}")
    except Exception as e:
        logger.exception("=" * 80)
        logger.exception("CRITICAL: Failed to initialize Trading Bot")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 80)
        logger.warning("Server starting without bot instance - some endpoints may not work")
        logger.warning("Endpoints will return 503 (Service Unavailable) until bot is initialized")
    finally:
        total_startup_time = time.time() - startup_time
        logger.info("=" * 80)
        logger.info("SERVER STARTUP COMPLETE")
        logger.info(f"Startup time: {total_startup_time:.2f}s")
        logger.info("=" * 80)
        logger.info("Trading Bot API ready to accept requests")
        logger.info("  - Server URL: http://0.0.0.0:8000")
        logger.info("  - Local URL: http://localhost:8000")
        logger.info("  - API Docs: http://localhost:8000/docs")
        logger.info("  - Health Check: http://localhost:8000/api/health")
        logger.info("=" * 80)

    try:
        yield
    finally:
        shutdown_start = time.time()
        logger.info("=" * 80)
        logger.info("Shutting down Trading Bot API Server")
        logger.info("=" * 80)
        try:
            # Get bot instance and close it properly
            bot = get_bot() if bot_instance else None
            if bot:
                logger.info("Closing bot instance and cleaning up resources...")
                bot.close()
                logger.info("Bot instance closed successfully")
            else:
                logger.debug("No bot instance to close")

            # Clear the global bot instance
            clear_bot()
            logger.info("Bot instance cleared from global state")

        except Exception as e:
            logger.exception(f"Error during bot shutdown: {e}")

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
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Log immediately at the start
    try:
        logger.info(f"[{request_id}] ========== INCOMING REQUEST ==========")
        logger.info(f"[{request_id}] Method: {request.method}")
        logger.info(f"[{request_id}] Path: {request.url.path}")
        logger.info(f"[{request_id}] Full URL: {request.url}")
    except Exception as e:
        logger.error(f"[{request_id}] Failed to log request start: {e}")

    # Extract request details
    try:
        client_ip = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else "unknown"
    except Exception as e:
        logger.warning(f"[{request_id}] Failed to get client info: {e}")
        client_ip = "unknown"
        client_port = "unknown"

    try:
        user_agent = request.headers.get("user-agent", "unknown")
        origin = request.headers.get("origin", "none")
        referer = request.headers.get("referer", "none")
    except Exception as e:
        logger.warning(f"[{request_id}] Failed to get headers: {e}")
        user_agent = "unknown"
        origin = "none"
        referer = "none"

    try:
        query_params = dict(request.query_params) if request.query_params else {}
    except Exception as e:
        logger.warning(f"[{request_id}] Failed to get query params: {e}")
        query_params = {}

    # Log request details
    try:
        logger.info(f"[{request_id}] Client: {client_ip}:{client_port}")
        logger.info(f"[{request_id}] Origin: {origin}")
        logger.info(f"[{request_id}] Referer: {referer}")
        logger.info(f"[{request_id}] User-Agent: {user_agent[:100]}")
        if query_params:
            logger.info(f"[{request_id}] Query Params: {query_params}")
    except Exception as e:
        logger.error(f"[{request_id}] Failed to log request details: {e}")

    # Process request
    try:
        logger.debug(f"[{request_id}] Processing request...")
        response = await call_next(request)
        process_time = time.time() - start_time

        # Determine status emoji
        status_emoji = (
            "✅" if 200 <= response.status_code < 300
            else "⚠️" if 300 <= response.status_code < 400
            else "❌"
        )

        # Get response details
        try:
            content_length = response.headers.get("content-length", "unknown")
            content_type = response.headers.get("content-type", "unknown")
        except Exception:
            content_length = "unknown"
            content_type = "unknown"

        # Log response
        logger.info(f"[{request_id}] ========== RESPONSE ==========")
        logger.info(f"[{request_id}] {status_emoji} Status: {response.status_code}")
        logger.info(f"[{request_id}] Process Time: {process_time:.3f}s")
        logger.info(f"[{request_id}] Content-Type: {content_type}")
        logger.info(f"[{request_id}] Content-Length: {content_length} bytes")
        logger.info(f"[{request_id}] ==============================")

        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.exception(f"[{request_id}] ========== ERROR ==========")
        logger.exception(f"[{request_id}] ❌ ERROR in {request.method} {request.url.path}")
        logger.exception(f"[{request_id}] Error Type: {type(e).__name__}")
        logger.exception(f"[{request_id}] Error Message: {str(e)}")
        logger.exception(f"[{request_id}] Process Time: {process_time:.3f}s")
        logger.exception(f"[{request_id}] ==========================")
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


# CORS middleware with detailed logging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log CORS configuration
logger.info("=" * 80)
logger.info("CORS Configuration:")
logger.info(f"  Allowed Origins: http://localhost:3000, http://localhost:5173, http://localhost:3001")
logger.info(f"  Allow Credentials: True")
logger.info(f"  Allow Methods: *")
logger.info(f"  Allow Headers: *")
logger.info("=" * 80)

# Include routers with detailed logging
logger.info("=" * 80)
logger.info("REGISTERING API ROUTES")
logger.info("=" * 80)

try:
    logger.info("Registering status router at /api/status...")
    app.include_router(status.router, prefix="/api", tags=["status"])
    logger.info("✅ Status router registered successfully")
except Exception as e:
    logger.exception(f"❌ Failed to register status router: {e}")

try:
    logger.info("Registering strategies router at /api/strategies...")
    app.include_router(strategies.router, prefix="/api", tags=["strategies"])
    logger.info("✅ Strategies router registered successfully")
except Exception as e:
    logger.exception(f"❌ Failed to register strategies router: {e}")

try:
    logger.info("Registering data router at /api/data...")
    app.include_router(data.router, prefix="/api", tags=["data"])
    logger.info("✅ Data router registered successfully")
except Exception as e:
    logger.exception(f"❌ Failed to register data router: {e}")

try:
    logger.info("Registering backtest router at /api/backtest...")
    app.include_router(backtest.router, prefix="/api", tags=["backtest"])
    logger.info("✅ Backtest router registered successfully")
except Exception as e:
    logger.exception(f"❌ Failed to register backtest router: {e}")

try:
    logger.info("Registering monte_carlo router at /api/monte-carlo...")
    app.include_router(monte_carlo.router, prefix="/api", tags=["monte-carlo"])
    logger.info("✅ Monte Carlo router registered successfully")
except Exception as e:
    logger.exception(f"❌ Failed to register monte_carlo router: {e}")

logger.info("=" * 80)
logger.info("ALL API ROUTES REGISTERED SUCCESSFULLY")
logger.info("=" * 80)


@app.get("/")
async def root():
    """Root endpoint."""
    logger.info("Root endpoint (/) accessed")
    return {"message": "Trading Bot API", "version": "0.1.0"}

@app.get("/api")
async def api_root():
    """API root endpoint."""
    logger.info("API root endpoint (/api) accessed")
    return {
        "message": "Trading Bot API",
        "version": "0.1.0",
        "endpoints": {
            "status": "/api/status",
            "strategies": "/api/strategies",
            "data": "/api/data",
            "backtest": "/api/backtest",
            "monte_carlo": "/api/monte-carlo",
        }
    }


def main():
    """Main entry point for API server."""
    import uvicorn

    logger.info("=" * 80)
    logger.info("STARTING UVICORN SERVER")
    logger.info("=" * 80)
    logger.info("Server configuration:")
    logger.info("  - Host: 0.0.0.0 (listening on all interfaces)")
    logger.info("  - Port: 8000")
    logger.info("  - Access Log: Enabled")
    logger.info("=" * 80)

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_config=None,  # Use our own logging configuration
            access_log=True,
        )
    except Exception as e:
        logger.exception("=" * 80)
        logger.exception("CRITICAL: Failed to start uvicorn server")
        logger.exception(f"Exception type: {type(e).__name__}")
        logger.exception(f"Exception message: {str(e)}")
        logger.exception("=" * 80)
        raise


if __name__ == "__main__":
    main()
