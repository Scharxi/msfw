"""Tests for the MSFW database system."""

import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.exc import StatementError

from msfw.core.config import DatabaseConfig
from msfw.core.database import Base, Database, DatabaseManager

# Async tests will be marked individually


# Test model
class DatabaseTestModel(Base):
    """Test model for database tests."""
    
    __tablename__ = "test_models"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))

# Ensure the model is properly registered with Base metadata
DatabaseTestModel.__table__


@pytest.mark.unit
class TestDatabaseConfig:
    """Test database configuration."""
    
    def test_default_config(self):
        """Test default database configuration."""
        config = DatabaseConfig()
        
        assert config.url == "sqlite+aiosqlite:///./app.db"
        assert config.echo is False
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600


@pytest.mark.integration
class TestDatabase:
    """Test database operations."""
    
    @pytest_asyncio.fixture
    async def database(self):
        """Create a test database."""
        import tempfile
        import os
        
        # Create a temporary file for the database
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)  # Close the file descriptor since we'll let SQLAlchemy handle the file
        
        try:
            config = DatabaseConfig(url=f"sqlite+aiosqlite:///{db_path}")
            db = Database(config)
            await db.initialize()
            
            # Register the test model
            db.register_model("DatabaseTestModel", DatabaseTestModel)
            
            # Create tables
            await db.create_tables()
            yield db
            await db.close()
        finally:
            # Clean up the temporary database file
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, database: Database):
        """Test database initialization."""
        assert database._engine is not None
        assert database._sync_engine is not None
        assert database._session_factory is not None
        assert database._sync_session_factory is not None
    
    @pytest.mark.asyncio
    async def test_database_properties(self, database: Database):
        """Test database properties."""
        assert database.engine is not None
        assert database.sync_engine is not None
        assert database.session_factory is not None
        assert database.sync_session_factory is not None
    
    @pytest.mark.asyncio
    async def test_model_registration(self, database: Database):
        """Test model registration."""
        database.register_model("DatabaseTestModel", DatabaseTestModel)
        
        assert database.get_model("DatabaseTestModel") == DatabaseTestModel
        assert "DatabaseTestModel" in database.get_models()
        assert database.get_model("NonExistent") is None
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self, database: Database):
        """Test session context manager."""
        # Test session creation and usage
        async with database.session() as session:
            # Create a test record
            test_obj = DatabaseTestModel(name="Test", description="Test description")
            session.add(test_obj)
            await session.flush()
            assert test_obj.id is not None
        
        # Verify the record was committed
        async with database.session() as session:
            result = await session.execute(select(DatabaseTestModel))
            records = result.scalars().all()
            assert len(records) == 1
            assert records[0].name == "Test"
    
    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, database: Database):
        """Test session rollback on error."""
        
        try:
            async with database.session() as session:
                # Create a valid record
                test_obj = DatabaseTestModel(name="Test", description="Test description")
                session.add(test_obj)
                await session.flush()
                
                # Cause an error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify no records were committed due to rollback
        async with database.session() as session:
            result = await session.execute(select(DatabaseTestModel))
            records = result.scalars().all()
            assert len(records) == 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, database: Database):
        """Test database health check."""
        # Healthy database
        assert await database.health_check() is True
        
        # Close database and test unhealthy state
        await database.close()
        assert await database.health_check() is False
    
    @pytest.mark.asyncio
    async def test_create_and_drop_tables(self, database: Database):
        """Test table creation and dropping."""
        
        # Create tables
        await database.create_tables()
        
        # Verify table exists by inserting data
        async with database.session() as session:
            test_obj = DatabaseTestModel(name="Test", description="Test")
            session.add(test_obj)
        
        # Drop tables
        await database.drop_tables()
        
        # Verify table is gone (should raise an error)
        with pytest.raises(Exception):  # Could be various SQLAlchemy exceptions
            async with database.session() as session:
                result = await session.execute(select(DatabaseTestModel))
                result.scalars().all()


@pytest.mark.integration
class TestDatabaseManager:
    """Test database manager."""
    
    @pytest.fixture
    def manager(self):
        """Create a database manager."""
        return DatabaseManager()
    
    def test_add_database(self, manager: DatabaseManager):
        """Test adding databases."""
        config1 = DatabaseConfig(url="sqlite+aiosqlite:///db1.db")
        config2 = DatabaseConfig(url="sqlite+aiosqlite:///db2.db")
        
        # Add first database as default
        db1 = manager.add_database("db1", config1, is_default=True)
        assert isinstance(db1, Database)
        
        # Add second database
        db2 = manager.add_database("db2", config2)
        assert isinstance(db2, Database)
        
        # Test retrieval
        assert manager.get_database() == db1  # Default
        assert manager.get_database("db1") == db1
        assert manager.get_database("db2") == db2
        
        # Test listing
        databases = manager.list_databases()
        assert len(databases) == 2
        assert "db1" in databases
        assert "db2" in databases
    
    def test_get_nonexistent_database(self, manager: DatabaseManager):
        """Test getting non-existent database."""
        with pytest.raises(ValueError, match="Database 'nonexistent' not found"):
            manager.get_database("nonexistent")
    
    @pytest.mark.asyncio
    async def test_initialize_all(self, manager: DatabaseManager):
        """Test initializing all databases."""
        config1 = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        config2 = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        
        db1 = manager.add_database("db1", config1)
        db2 = manager.add_database("db2", config2)
        
        # Initialize all
        await manager.initialize_all()
        
        # Verify both are initialized
        assert db1._engine is not None
        assert db2._engine is not None
        
        # Cleanup
        await manager.close_all()
    
    @pytest.mark.asyncio
    async def test_close_all(self, manager: DatabaseManager):
        """Test closing all databases."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        db = manager.add_database("test", config)
        
        await manager.initialize_all()
        assert db._engine is not None
        
        await manager.close_all()
        # Note: SQLAlchemy engines don't have a direct "closed" state to check


@pytest.mark.unit
class TestDatabaseUrlFormats:
    """Test different database URL formats."""
    
    def test_sqlite_url(self):
        """Test SQLite URL configuration."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///./test.db")
        assert "sqlite" in config.url
        assert "aiosqlite" in config.url
    
    def test_postgresql_url(self):
        """Test PostgreSQL URL configuration."""
        config = DatabaseConfig(url="postgresql+asyncpg://user:pass@localhost/test")
        assert "postgresql" in config.url
        assert "asyncpg" in config.url
    
    def test_mysql_url(self):
        """Test MySQL URL configuration."""
        config = DatabaseConfig(url="mysql+aiomysql://user:pass@localhost/test")
        assert "mysql" in config.url
        assert "aiomysql" in config.url


@pytest.mark.integration
class TestDatabaseWithRealOperations:
    """Test database with real operations."""
    
    @pytest_asyncio.fixture
    async def populated_database(self):
        """Create a database with test data."""
        import tempfile
        import os
        
        # Create a temporary file for the database
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)  # Close the file descriptor since we'll let SQLAlchemy handle the file
        
        try:
            config = DatabaseConfig(url=f"sqlite+aiosqlite:///{db_path}")
            db = Database(config)
            await db.initialize()
            
            # Register the test model
            db.register_model("DatabaseTestModel", DatabaseTestModel)
            
            await db.create_tables()
            
            # Add test data
            async with db.session() as session:
                test_data = [
                    DatabaseTestModel(name="Item 1", description="Description 1"),
                    DatabaseTestModel(name="Item 2", description="Description 2"),
                    DatabaseTestModel(name="Item 3", description="Description 3"),
                ]
                for item in test_data:
                    session.add(item)
            
            yield db
            await db.close()
        finally:
            # Clean up the temporary database file
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_query_operations(self, populated_database: Database):
        """Test various query operations."""
        async with populated_database.session() as session:
            # Count all records
            result = await session.execute(select(DatabaseTestModel))
            all_records = result.scalars().all()
            assert len(all_records) == 3
            
            # Query by name
            result = await session.execute(
                select(DatabaseTestModel).where(DatabaseTestModel.name == "Item 1")
            )
            item1 = result.scalar_one()
            assert item1.name == "Item 1"
            assert item1.description == "Description 1"
    
    @pytest.mark.asyncio
    async def test_update_operations(self, populated_database: Database):
        """Test update operations."""
        async with populated_database.session() as session:
            # Get an item to update
            result = await session.execute(
                select(DatabaseTestModel).where(DatabaseTestModel.name == "Item 1")
            )
            item = result.scalar_one()
            
            # Update it
            item.description = "Updated description"
            await session.flush()
            await session.refresh(item)
            
            assert item.description == "Updated description"
    
    @pytest.mark.asyncio
    async def test_delete_operations(self, populated_database: Database):
        """Test delete operations."""
        async with populated_database.session() as session:
            # Delete an item
            result = await session.execute(
                select(DatabaseTestModel).where(DatabaseTestModel.name == "Item 2")
            )
            item = result.scalar_one()
            await session.delete(item)
        
        # Verify deletion
        async with populated_database.session() as session:
            result = await session.execute(select(DatabaseTestModel))
            remaining_items = result.scalars().all()
            assert len(remaining_items) == 2
            
            names = [item.name for item in remaining_items]
            assert "Item 2" not in names
            assert "Item 1" in names
            assert "Item 3" in names 