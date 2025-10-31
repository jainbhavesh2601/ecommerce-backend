from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc, or_, func
from src.product.models import Product
from src.product.schema import ProductCreate, ProductUpdate
from src.auth.user.models import User, UserRole
from src.common.location_utils import LocationUtils
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from src.common.response import ResponseHandler
from src.common.exceptions import NotFoundError, ValidationError
from decimal import Decimal
import uuid

class ProductService:
    @staticmethod
    async def get_all_products(
        db: AsyncSession, 
        page: int, 
        limit: int, 
        search: str = "",
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        max_distance_km: Optional[float] = None,
        sort_by_distance: bool = False
    ) -> Dict[str, Any]:
        try:
            offset = (page - 1) * limit
            
            # Join with User table to get seller location
            query = select(Product, User).join(User, Product.seller_id == User.id)
            
            if search:
                query = query.where(or_(
                    Product.title.ilike(f"%{search}%"),
                    Product.description.ilike(f"%{search}%"),
                    Product.brand.ilike(f"%{search}%")
                ))
            
            # Execute query to get all matching products with seller info
            result = await db.execute(query)
            product_seller_pairs = result.all()
            
            # Calculate distances and filter
            products_with_distance = []
            for product, seller in product_seller_pairs:
                # Calculate distance if user location is provided
                distance = None
                if user_lat is not None and user_lon is not None:
                    distance = LocationUtils.calculate_distance(
                        user_lat, user_lon, 
                        seller.latitude, seller.longitude
                    )
                
                # Filter by max distance if specified
                if max_distance_km is not None:
                    if not LocationUtils.is_within_radius(distance, max_distance_km):
                        continue
                
                products_with_distance.append({
                    "product": product,
                    "distance": distance,
                    "seller_city": seller.city,
                    "seller_state": seller.state
                })
            
            # Sort by distance if requested and user location is provided
            if sort_by_distance and user_lat is not None and user_lon is not None:
                # Sort by distance, putting None distances at the end
                products_with_distance.sort(
                    key=lambda x: (x["distance"] is None, x["distance"] if x["distance"] is not None else float('inf'))
                )
            else:
                # Sort by created_at (newest first)
                products_with_distance.sort(
                    key=lambda x: x["product"].created_at,
                    reverse=True
                )
            
            # Apply pagination
            total_count = len(products_with_distance)
            paginated_products = products_with_distance[offset:offset + limit]
            
            # Format response
            formatted_products = []
            for item in paginated_products:
                # Convert images JSON string back to list
                import json
                try:
                    images = json.loads(item["product"].images) if isinstance(item["product"].images, str) else item["product"].images
                except (json.JSONDecodeError, TypeError):
                    images = []
                
                product_dict = {
                    "id": item["product"].id,
                    "title": item["product"].title,
                    "description": item["product"].description,
                    "price": item["product"].price,
                    "discount_percentage": item["product"].discount_percentage,
                    "rating": item["product"].rating,
                    "stock": item["product"].stock,
                    "brand": item["product"].brand,
                    "thumbnail": item["product"].thumbnail,
                    "images": images,
                    "category_id": item["product"].category_id,
                    "seller_id": item["product"].seller_id,
                    "created_at": item["product"].created_at,
                    "updated_at": item["product"].updated_at,
                    "distance_km": item["distance"],
                    "distance_formatted": LocationUtils.format_distance(item["distance"]),
                    "seller_location": {
                        "city": item["seller_city"],
                        "state": item["seller_state"]
                    }
                }
                formatted_products.append(product_dict)
            
            return {
                "message": f"Successfully retrieved products for page {page}",
                "data": formatted_products,
                "metadata": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit if limit > 0 else 0,
                    "sorted_by_distance": sort_by_distance and user_lat is not None,
                    "max_distance_km": max_distance_km
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving products: {str(e)}"
            )

    @staticmethod
    async def get_product(db: AsyncSession, product_id: str) -> Product:
        try:
            query = select(Product).where(Product.id == product_id)
            result = await db.execute(query)
            product = result.scalar_one_or_none()
            if not product:
                raise NotFoundError("Product", product_id)
            return ResponseHandler.get_single_success(product.title, product_id, product)
        except NotFoundError:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving product: {str(e)}"
            )

    @staticmethod
    async def create_product(db: AsyncSession, product: ProductCreate, current_user: User) -> Product:
        try:
            # Check if user has permission to create products
            if current_user.role not in [UserRole.SELLER, UserRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only sellers and admins can create products"
                )
            
            product_dict = product.model_dump()
            # Add seller_id to track who created the product
            product_dict["seller_id"] = current_user.id
            # Convert images list to JSON string for SQLite compatibility
            if isinstance(product_dict.get("images"), list):
                import json
                product_dict["images"] = json.dumps(product_dict["images"])
            db_product = Product(**product_dict)
            db.add(db_product)
            await db.commit()
            await db.refresh(db_product)
            return ResponseHandler.create_success(db_product.title, db_product.id, db_product)
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating product: {str(e)}"
            )

    @staticmethod
    async def update_product(db: AsyncSession, product_id: str, updated_product: ProductUpdate, current_user: User) -> Product:
        try:
            query = select(Product).where(Product.id == product_id)
            result = await db.execute(query)
            db_product = result.scalar_one_or_none()
            if not db_product:
                raise NotFoundError("Product", product_id)
            
            # Authorization: Only the seller who created the product or admin can update it
            if current_user.role != UserRole.ADMIN and db_product.seller_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update products that you created. Only the product owner or admin can update this product."
                )

            for key, value in updated_product.model_dump(exclude_unset=True).items():
                setattr(db_product, key, value)
            db_product.updated_at = datetime.utcnow()

            db.add(db_product)
            await db.commit()
            await db.refresh(db_product)
            return ResponseHandler.update_success(db_product.title, db_product.id, db_product)
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating product: {str(e)}"
            )

    @staticmethod
    async def delete_product(db: AsyncSession, product_id: str, current_user: User) -> Product:
        try:
            query = select(Product).where(Product.id == product_id)
            result = await db.execute(query)
            db_product = result.scalar_one_or_none()
            if not db_product:
                raise NotFoundError("Product", product_id)
            
            # Authorization: Only the seller who created the product or admin can delete it
            if current_user.role != UserRole.ADMIN and db_product.seller_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete products that you created. Only the product owner or admin can delete this product."
                )
            
            # First, delete all related cart items
            from src.cart.models import CartItem
            cart_items_query = select(CartItem).where(CartItem.product_id == product_id)
            cart_items_result = await db.execute(cart_items_query)
            cart_items = cart_items_result.scalars().all()
            
            for cart_item in cart_items:
                await db.delete(cart_item)
            
            # Also delete all related order items
            from src.orders.models import OrderItem
            order_items_query = select(OrderItem).where(OrderItem.product_id == product_id)
            order_items_result = await db.execute(order_items_query)
            order_items = order_items_result.scalars().all()
            
            for order_item in order_items:
                await db.delete(order_item)
            
            # Then delete the product
            await db.delete(db_product)
            await db.commit()
            return ResponseHandler.delete_success(db_product.title, db_product.id, db_product)
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting product: {str(e)}"
            )

    @staticmethod
    async def get_products_by_seller(
        db: AsyncSession,
        seller_id: uuid.UUID,
        page: int = 1,
        limit: int = 100,
        search: str = ""
    ) -> Dict[str, Any]:
        """
        Get products by seller ID.
        """
        try:
            offset = (page - 1) * limit
            
            # Query products by seller_id
            query = select(Product).where(Product.seller_id == seller_id)
            
            if search:
                query = query.where(or_(
                    Product.title.ilike(f"%{search}%"),
                    Product.description.ilike(f"%{search}%"),
                    Product.brand.ilike(f"%{search}%")
                ))
            
            # Order by created_at (newest first)
            query = query.order_by(desc(Product.created_at))
            
            # Execute query
            result = await db.execute(query)
            products = result.scalars().all()
            
            # Get total count for pagination
            count_query = select(func.count()).select_from(Product).where(Product.seller_id == seller_id)
            if search:
                count_query = count_query.where(or_(
                    Product.title.ilike(f"%{search}%"),
                    Product.description.ilike(f"%{search}%"),
                    Product.brand.ilike(f"%{search}%")
                ))
            total = await db.scalar(count_query)
            
            # Apply pagination
            paginated_products = products[offset:offset + limit]
            
            # Format response
            formatted_products = []
            for product in paginated_products:
                # Convert images JSON string back to list
                import json
                try:
                    images = json.loads(product.images) if isinstance(product.images, str) else product.images
                except (json.JSONDecodeError, TypeError):
                    images = []
                
                product_dict = {
                    "id": product.id,
                    "title": product.title,
                    "description": product.description,
                    "price": float(product.price),
                    "discount_percentage": product.discount_percentage,
                    "rating": product.rating,
                    "stock": product.stock,
                    "brand": product.brand,
                    "thumbnail": product.thumbnail,
                    "images": images,
                    "category_id": product.category_id,
                    "seller_id": product.seller_id,
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None
                }
                formatted_products.append(product_dict)
            
            return {
                "message": f"Successfully retrieved seller's products for page {page}",
                "data": formatted_products,
                "metadata": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit if limit > 0 else 0
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving seller's products: {str(e)}"
            )