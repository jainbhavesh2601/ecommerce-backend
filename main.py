from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.product.routes import router as product_router
from contextlib import asynccontextmanager
from src.db.main import init_db
from src.db.auto_migrations import run_auto_migrations
from src.cart.routes import router as cart_router
from src.category.routes import router as category_router
from src.auth.routes import router as auth_router
from src.auth.user.routes import router as user_router
from src.orders.routes import router as order_router
from src.dashboard.routes import router as dashboard_router
from src.payment.routes import router as payment_router
from src.middleware import setup_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Server is starting...")
    await init_db()
    await run_auto_migrations()
    yield
    print("🧹 Server is shutting down...")


description = """
Welcome to the E-commerce API! 🚀

This API provides a comprehensive set of functionalities for managing your e-commerce platform.

Key features include:

- **Crud**
	- Create, Read, Update, and Delete endpoints.
- **Search**
	- Find specific information with parameters and pagination.
- **Auth**
	- Verify user/system identity.
	- Secure with Access and Refresh tokens.
- **Permission**
	- Assign roles with specific permissions.
	- Different access levels for User/Admin.
- **Validation**
	- Ensure accurate and secure input data.


For any inquiries, please contact:

* Github: https://github.com/Thakur-Rohit-chauhan
"""

version = "1.0.0"

app = FastAPI(
    title="E-commerce API",
    description=description,
    version=version,
    contact={
        "name": "Rohit Chauhan",
        "url": "https://github.com/Thakur-Rohit-chauhan",
    },
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "layout": "BaseLayout",
        "filter": True,
        "tryItOutEnabled": True,
        "onComplete": "Ok"
    },
    lifespan=lifespan
)

# ✅ Add CORS middleware (must come before routers)
origins = [
    "https://ecommerce-frontend-tan-five.vercel.app",  # your frontend URL
    "http://localhost:3000",  # for local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup middleware
setup_middleware(app)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(product_router, prefix="/products", tags=["Products"])
app.include_router(cart_router, prefix="/carts", tags=["Carts"])
app.include_router(category_router, prefix="/categories", tags=["Categories"])
app.include_router(order_router, prefix="/orders", tags=["Orders"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(payment_router, prefix="/payments", tags=["Payments"])
