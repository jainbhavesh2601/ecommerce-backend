from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing information."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.url}")
        
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return error response with CORS headers
            error_response = JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error": str(e)
                }
            )
            
            # Add CORS headers manually (for failed requests)
            origin = request.headers.get("Origin", "*")
            error_response.headers["Access-Control-Allow-Origin"] = origin
            error_response.headers["Access-Control-Allow-Credentials"] = "true"
            error_response.headers["Access-Control-Allow-Methods"] = "*"
            error_response.headers["Access-Control-Allow-Headers"] = "*"
            
            return error_response


def setup_middleware(app: FastAPI):
    """Setup all middleware for the FastAPI application."""
    
    # ✅ CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "https://ecommerce-frontend-tan-five.vercel.app",  # ✅ Your Vercel frontend
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ✅ TrustedHost middleware — allow Render + localhost
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "ecommerce-backend-7jlj.onrender.com",  # ✅ Your Render backend
            ".onrender.com",  # ✅ Any Render subdomain
        ]
    )

    # ✅ Custom middleware (order matters)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
