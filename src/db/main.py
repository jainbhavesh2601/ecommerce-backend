import ssl
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel
from src.config import Config

# Create secure SSL context based on environment
if Config.ENVIRONMENT == "production":
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    connect_args = {"ssl": ssl_context}
else:
    # For development, use less strict SSL or no SSL
    connect_args = {}

# Engine with environment-appropriate SSL configuration
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=Config.ENVIRONMENT == "development",
    connect_args=connect_args,
    pool_pre_ping=True
)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_db() -> AsyncSession:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session