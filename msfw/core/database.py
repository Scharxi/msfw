"""Database management for MSFW applications."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional, Type, Union

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from msfw.core.config import DatabaseConfig


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Database:
    """Database management class."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Optional[AsyncEngine] = None
        self._sync_engine = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._sync_session_factory = None
        self._models: Dict[str, Type[Base]] = {}
        
    @property
    def engine(self) -> AsyncEngine:
        """Get the async database engine."""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine
    
    @property
    def sync_engine(self):
        """Get the sync database engine."""
        if self._sync_engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._sync_engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """Get the async session factory."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory
    
    @property
    def sync_session_factory(self) -> sessionmaker:
        """Get the sync session factory."""
        if self._sync_session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._sync_session_factory
    
    async def initialize(self) -> None:
        """Initialize the database connection."""
        # Create async engine
        engine_kwargs = {
            "echo": self.config.echo,
            "pool_recycle": self.config.pool_recycle,
        }
        
        # Handle SQLite differently
        if "sqlite" in self.config.url:
            engine_kwargs["poolclass"] = NullPool
            # SQLite doesn't support pool_timeout, pool_size, max_overflow
        else:
            engine_kwargs["pool_size"] = self.config.pool_size
            engine_kwargs["max_overflow"] = self.config.max_overflow
            engine_kwargs["pool_timeout"] = self.config.pool_timeout
            engine_kwargs["poolclass"] = QueuePool
        
        self._engine = create_async_engine(self.config.url, **engine_kwargs)
        
        # Create sync engine for migrations
        sync_url = self.config.url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")
        self._sync_engine = create_engine(sync_url, **engine_kwargs)
        
        # Create session factories
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        self._sync_session_factory = sessionmaker(
            bind=self._sync_engine,
            class_=Session,
        )
        
        # Add SQLite foreign key support
        if "sqlite" in self.config.url:
            @event.listens_for(self._engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create a new async database session."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @asynccontextmanager
    def sync_session(self) -> Session:
        """Create a new sync database session."""
        with self.sync_session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    def register_model(self, name: str, model: Type[Base]) -> None:
        """Register a database model."""
        self._models[name] = model
    
    def get_model(self, name: str) -> Optional[Type[Base]]:
        """Get a registered model by name."""
        return self._models.get(name)
    
    def get_models(self) -> Dict[str, Type[Base]]:
        """Get all registered models."""
        return self._models.copy()
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        # First, ensure all registered models are properly added to Base metadata
        for model_name, model in self._models.items():
            if hasattr(model, '__table__') and model.__table__ is not None:
                table = model.__table__
                # Force the table to be added to Base metadata if not already there
                if table.name not in Base.metadata.tables:
                    # Access the table to ensure it's initialized
                    _ = table.columns
                    # Add it to Base metadata
                    Base.metadata._add_table(table, None)
        
        # Create tables using a separate connection for each operation
        # This ensures proper transaction handling
        async with self._engine.connect() as conn:
            # Start a transaction and commit it to ensure table creation persists
            async with conn.begin() as trans:
                def create_all_tables(sync_conn):
                    Base.metadata.create_all(bind=sync_conn, checkfirst=True)
                    
                    # Also create individual tables for registered models
                    for model_name, model in self._models.items():
                        if hasattr(model, '__table__') and model.__table__ is not None:
                            table = model.__table__
                            table.create(bind=sync_conn, checkfirst=True)
                
                await conn.run_sync(create_all_tables)
                # Explicitly commit the transaction
                await trans.commit()
    
    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def health_check(self) -> bool:
        """Check if database is healthy."""
        try:
            # Check if engine is available
            if not self._engine:
                return False
            
            # Check if engine is disposed (for non-SQLite databases)
            if hasattr(self._engine.pool, 'invalidated') and self._engine.pool.invalidated:
                return False
                
            async with self.session() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


class DatabaseManager:
    """Manages multiple database connections."""
    
    def __init__(self):
        self._databases: Dict[str, Database] = {}
        self._default_name = "default"
    
    def add_database(self, name: str, config: DatabaseConfig, is_default: bool = False) -> Database:
        """Add a new database connection."""
        database = Database(config)
        self._databases[name] = database
        
        if is_default:
            self._default_name = name
            
        return database
    
    def get_database(self, name: Optional[str] = None) -> Database:
        """Get a database connection by name."""
        db_name = name or self._default_name
        
        if db_name not in self._databases:
            raise ValueError(f"Database '{db_name}' not found")
        
        return self._databases[db_name]
    
    async def initialize_all(self) -> None:
        """Initialize all database connections."""
        for database in self._databases.values():
            await database.initialize()
    
    async def close_all(self) -> None:
        """Close all database connections."""
        for database in self._databases.values():
            await database.close()
    
    def list_databases(self) -> Dict[str, Database]:
        """List all database connections."""
        return self._databases.copy()


# Global database manager instance
db_manager = DatabaseManager() 