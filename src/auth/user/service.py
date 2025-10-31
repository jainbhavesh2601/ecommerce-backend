from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from src.auth.user.models import User, UserRole
from src.auth.user.schema import UserCreate, UserUpdate, UserLogin, PasswordChange
from src.auth.utils import get_password_hash, verify_password, create_access_token
from src.auth.verification_models import EmailVerificationToken
from src.common.email_service import EmailService
from src.common.geocoding_service import GeocodingService
from src.cart.models import Cart
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from src.common.response import ResponseHandler
from src.common.exceptions import NotFoundError, ConflictError, ValidationError
from src.config import Config
from decimal import Decimal
import uuid

class UserService:
    @staticmethod
    async def get_all_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str = "",
        role: Optional[UserRole] = None
    ) -> Dict[str, Any]:
        try:
            query = select(User)
            
            # Apply filters
            if search:
                query = query.where(
                    User.username.ilike(f"%{search}%") |
                    User.email.ilike(f"%{search}%") |
                    User.full_name.ilike(f"%{search}%")
                )
            
            if role:
                query = query.where(User.role == role)
            
            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            users = result.scalars().all()
            
            # Get total count
            count_query = select(func.count()).select_from(User)
            if search:
                count_query = count_query.where(
                    User.username.ilike(f"%{search}%") |
                    User.email.ilike(f"%{search}%") |
                    User.full_name.ilike(f"%{search}%")
                )
            if role:
                count_query = count_query.where(User.role == role)
            
            total = await db.scalar(count_query)
            
            return {
                "message": "Successfully retrieved users",
                "data": users,
                "metadata": {
                    "skip": skip,
                    "limit": limit,
                    "total": total
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving users: {str(e)}"
            )

    @staticmethod
    async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
        try:
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise NotFoundError("User", user_id)
                
            return ResponseHandler.get_single_success("User", user_id, user)
        except NotFoundError:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user: {str(e)}"
            )

    @staticmethod
    async def create_user(db: AsyncSession, user: UserCreate) -> User:
        try:
            # Check if email already exists
            email_query = select(User).where(User.email == user.email)
            email_result = await db.execute(email_query)
            if email_result.scalar_one_or_none():
                raise ConflictError(f"User with email '{user.email}' already exists")
            
            # Check if username already exists
            username_query = select(User).where(User.username == user.username)
            username_result = await db.execute(username_query)
            if username_result.scalar_one_or_none():
                raise ConflictError(f"User with username '{user.username}' already exists")
            
            # Geocode address if provided (for sellers)
            lat, lon = None, None
            if hasattr(user, 'address') and user.address:
                print(f"Geocoding address for user: {user.address}")
                lat, lon = GeocodingService.geocode_address(user.address)
                if lat and lon:
                    print(f"Successfully geocoded: lat={lat}, lon={lon}")
                else:
                    print(f"Failed to geocode address: {user.address}")
            
            # Create user
            user_dict = user.model_dump(exclude={"password"})
            # password = user.password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
            user_dict["hashed_password"] = get_password_hash(user.password)
            user_dict["is_verified"] = False  # User must verify email
            
            # Add geocoded coordinates if available
            if lat is not None:
                user_dict["latitude"] = lat
            if lon is not None:
                user_dict["longitude"] = lon
            
            db_user = User(**user_dict)
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            
            # Create a cart for the new user
            try:
                user_cart = Cart(user_id=db_user.id, total_price=Decimal('0.00'))
                db.add(user_cart)
                await db.commit()
                print(f"Created cart for user {db_user.id}")
            except Exception as e:
                print(f"Failed to create cart for user: {str(e)}")
                # Don't fail user creation if cart creation fails
            
            # Create verification token and send email
            try:
                verification_token = EmailVerificationToken.create_token(db_user.id)
                db.add(verification_token)
                await db.commit()
                
                # Send verification email
                EmailService.send_verification_email(
                    db_user.email,
                    db_user.username,
                    verification_token.token
                )
            except Exception as e:
                # Log error but don't fail user creation
                print(f"Failed to send verification email: {str(e)}")
            
            return ResponseHandler.create_success("User", db_user.id, db_user)
        except (ConflictError, ValidationError):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating user: {str(e)}"
            )

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        user_update: UserUpdate,
        current_user: User
    ) -> User:
        try:
            # Get user to update
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                raise NotFoundError("User", user_id)
            
            # Check permissions
            if current_user.role != UserRole.ADMIN and current_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own profile"
                )
            
            # Check for email conflicts
            if user_update.email and user_update.email != db_user.email:
                email_query = select(User).where(User.email == user_update.email)
                email_result = await db.execute(email_query)
                if email_result.scalar_one_or_none():
                    raise ConflictError(f"User with email '{user_update.email}' already exists")
            
            # Check for username conflicts
            if user_update.username and user_update.username != db_user.username:
                username_query = select(User).where(User.username == user_update.username)
                username_result = await db.execute(username_query)
                if username_result.scalar_one_or_none():
                    raise ConflictError(f"User with username '{user_update.username}' already exists")
            
            # Update fields
            update_dict = user_update.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                setattr(db_user, key, value)
            
            # Geocode address if it's being updated
            if 'address' in update_dict and update_dict['address']:
                print(f"Geocoding updated address for user {user_id}: {update_dict['address']}")
                lat, lon = GeocodingService.geocode_address(update_dict['address'])
                if lat and lon:
                    print(f"Successfully geocoded: lat={lat}, lon={lon}")
                    setattr(db_user, 'latitude', lat)
                    setattr(db_user, 'longitude', lon)
                else:
                    print(f"Failed to geocode address: {update_dict['address']}")
            
            db_user.updated_at = datetime.utcnow()
            
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            
            return ResponseHandler.update_success("User", user_id, db_user)
        except (NotFoundError, ConflictError, ValidationError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating user: {str(e)}"
            )

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: uuid.UUID, current_user: User) -> User:
        try:
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise NotFoundError("User", user_id)
            
            # Check permissions
            if current_user.role != UserRole.ADMIN and current_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete your own account"
                )
            
            # Prevent admin from deleting themselves
            if current_user.id == user_id and current_user.role == UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Admin cannot delete their own account"
                )
            
            await db.delete(user)
            await db.commit()
            
            return ResponseHandler.delete_success("User", user_id, user)
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting user: {str(e)}"
            )

    @staticmethod
    async def authenticate_user(db: AsyncSession, login_data: UserLogin) -> Dict[str, Any]:
        try:
            # Find user by username or email
            query = select(User).where(
                (User.username == login_data.username) | (User.email == login_data.username)
            )
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password"
                )
            
            if not verify_password(login_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is deactivated"
                )
            
            if not user.is_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Please verify your email address before logging in. Check your email for the verification link."
                )
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.add(user)
            await db.commit()
            
            # Create access token
            access_token_expires = timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": str(user.id)}, expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": Config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": user
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication error: {str(e)}"
            )

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: uuid.UUID,
        password_data: PasswordChange,
        current_user: User
    ) -> Dict[str, Any]:
        try:
            # Get user
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise NotFoundError("User", user_id)
            
            # Check permissions
            if current_user.role != UserRole.ADMIN and current_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only change your own password"
                )
            
            # Verify current password
            if not verify_password(password_data.current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Update password
            user.hashed_password = get_password_hash(password_data.new_password)
            user.updated_at = datetime.utcnow()
            
            db.add(user)
            await db.commit()
            
            return {
                "message": "Password changed successfully",
                "data": {"user_id": str(user_id)}
            }
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error changing password: {str(e)}"
            )

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> Dict[str, Any]:
        """
        Verify user's email with the provided token
        """
        try:
            # Find the token
            query = select(EmailVerificationToken).where(
                EmailVerificationToken.token == token
            )
            result = await db.execute(query)
            verification_token = result.scalar_one_or_none()
            
            if not verification_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid verification token"
                )
            
            if verification_token.is_used:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification token has already been used"
                )
            
            if verification_token.is_expired():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification token has expired. Please request a new one."
                )
            
            # Get the user
            user_query = select(User).where(User.id == verification_token.user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise NotFoundError("User", verification_token.user_id)
            
            if user.is_verified:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email is already verified"
                )
            
            # Mark user as verified
            user.is_verified = True
            user.updated_at = datetime.utcnow()
            
            # Mark token as used
            verification_token.is_used = True
            
            db.add(user)
            db.add(verification_token)
            await db.commit()
            await db.refresh(user)
            
            # Send welcome email
            try:
                EmailService.send_welcome_email(user.email, user.username)
            except Exception as e:
                print(f"Failed to send welcome email: {str(e)}")
            
            return {
                "message": "Email verified successfully",
                "data": {"user_id": str(user.id), "email": user.email}
            }
        except (NotFoundError, HTTPException):
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error verifying email: {str(e)}"
            )

    @staticmethod
    async def resend_verification_email(db: AsyncSession, email: str) -> Dict[str, Any]:
        """
        Resend verification email to user
        """
        try:
            # Find user by email
            query = select(User).where(User.email == email)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User with this email not found"
                )
            
            if user.is_verified:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email is already verified"
                )
            
            # Invalidate old tokens
            old_tokens_query = select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.is_used == False
            )
            old_tokens_result = await db.execute(old_tokens_query)
            old_tokens = old_tokens_result.scalars().all()
            
            for old_token in old_tokens:
                old_token.is_used = True
                db.add(old_token)
            
            # Create new verification token
            verification_token = EmailVerificationToken.create_token(user.id)
            db.add(verification_token)
            await db.commit()
            
            # Send verification email
            email_sent = EmailService.send_verification_email(
                user.email,
                user.username,
                verification_token.token
            )
            
            if not email_sent:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send verification email"
                )
            
            return {
                "message": "Verification email sent successfully",
                "data": {"email": user.email}
            }
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error resending verification email: {str(e)}"
            )
