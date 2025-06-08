"""
Example Basic Module for MSFW
=============================

This demonstrates how to create a basic module with:
- Simple CRUD operations
- Database models
- Route registration
- Dependencies
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

from msfw import Module
from msfw.core.database import Base


# Pydantic models for API
class ItemCreate(BaseModel):
    """Item creation model."""
    name: str
    description: Optional[str] = None


class ItemUpdate(BaseModel):
    """Item update model."""
    name: Optional[str] = None
    description: Optional[str] = None


class ItemResponse(BaseModel):
    """Item response model."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True


# SQLAlchemy model
class Item(Base):
    """Item database model."""
    
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BasicModule(Module):
    """Example basic module demonstrating CRUD operations."""
    
    @property
    def name(self) -> str:
        return "basic"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Basic module with CRUD operations"
    
    async def setup(self) -> None:
        """Setup the module."""
        if self.context and self.context.database:
            # Register the model
            self.context.database.register_model("Item", Item)
            
            # Create tables
            await self.context.database.create_tables()
    
    def register_routes(self, router: APIRouter) -> None:
        """Register module routes."""
        
        @router.get("/items", response_model=List[ItemResponse])
        async def list_items():
            """Get all items."""
            if not self.context or not self.context.database:
                raise HTTPException(status_code=500, detail="Database not available")
            
            async with self.context.database.session() as session:
                from sqlalchemy import select
                result = await session.execute(select(Item))
                items = result.scalars().all()
                return items
        
        @router.post("/items", response_model=ItemResponse)
        async def create_item(item_data: ItemCreate):
            """Create a new item."""
            if not self.context or not self.context.database:
                raise HTTPException(status_code=500, detail="Database not available")
            
            async with self.context.database.session() as session:
                item = Item(
                    name=item_data.name,
                    description=item_data.description,
                )
                session.add(item)
                await session.flush()
                await session.refresh(item)
                return item
        
        @router.get("/items/{item_id}", response_model=ItemResponse)
        async def get_item(item_id: int):
            """Get an item by ID."""
            if not self.context or not self.context.database:
                raise HTTPException(status_code=500, detail="Database not available")
            
            async with self.context.database.session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Item).where(Item.id == item_id)
                )
                item = result.scalar_one_or_none()
                
                if not item:
                    raise HTTPException(status_code=404, detail="Item not found")
                
                return item
        
        @router.put("/items/{item_id}", response_model=ItemResponse)
        async def update_item(item_id: int, item_data: ItemUpdate):
            """Update an item."""
            if not self.context or not self.context.database:
                raise HTTPException(status_code=500, detail="Database not available")
            
            async with self.context.database.session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Item).where(Item.id == item_id)
                )
                item = result.scalar_one_or_none()
                
                if not item:
                    raise HTTPException(status_code=404, detail="Item not found")
                
                if item_data.name is not None:
                    item.name = item_data.name
                if item_data.description is not None:
                    item.description = item_data.description
                
                await session.flush()
                await session.refresh(item)
                return item
        
        @router.delete("/items/{item_id}")
        async def delete_item(item_id: int):
            """Delete an item."""
            if not self.context or not self.context.database:
                raise HTTPException(status_code=500, detail="Database not available")
            
            async with self.context.database.session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Item).where(Item.id == item_id)
                )
                item = result.scalar_one_or_none()
                
                if not item:
                    raise HTTPException(status_code=404, detail="Item not found")
                
                await session.delete(item)
                return {"message": "Item deleted successfully"}
        
        @router.get("/")
        async def module_info():
            """Get module information."""
            return {
                "module": self.name,
                "version": self.version,
                "description": self.description,
                "endpoints": [
                    "GET /items - List all items",
                    "POST /items - Create new item",
                    "GET /items/{id} - Get item by ID",
                    "PUT /items/{id} - Update item",
                    "DELETE /items/{id} - Delete item",
                ]
            } 