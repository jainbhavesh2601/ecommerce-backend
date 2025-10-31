from fastapi import APIRouter, Depends, Query, status, HTTPException
from src.db.main import get_db
from src.dashboard.service import DashboardService, InvoiceService
from src.dashboard.schema import (
    DashboardResponse, InvoiceCreate, InvoiceUpdate, InvoiceResponse,
    InvoiceListResponse, InvoiceDetailResponse
)
from src.dashboard.models import Invoice, InvoiceStatus
from src.auth.utils import get_current_active_user, require_seller_or_admin, require_admin
from src.auth.user.models import User, UserRole
from src.common.exceptions import NotFoundError
from typing import Optional, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import uuid

router = APIRouter()

# Dashboard Routes
@router.get("/seller", response_model=DashboardResponse)
async def get_seller_dashboard(
    days: int = Query(30, ge=1, le=365, description="Number of days for analytics"),
    current_user: User = Depends(require_seller_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard data for sellers.
    
    Returns analytics including:
    - Total products, orders, revenue
    - Recent orders
    - Top products
    - Revenue trends
    - Order status breakdown
    """
    try:
        # For sellers, use their own ID; for admins, they can specify seller_id
        seller_id = current_user.id
        return await DashboardService.get_seller_dashboard(db, seller_id, days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving seller dashboard: {str(e)}"
        )

@router.get("/admin", response_model=DashboardResponse)
async def get_admin_dashboard(
    days: int = Query(30, ge=1, le=365, description="Number of days for analytics"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard data for admins.
    
    Returns platform-wide analytics including:
    - Total users, sellers, products, orders, revenue
    - Recent orders
    - Top sellers
    - Revenue and user growth trends
    - Order status breakdown
    """
    try:
        return await DashboardService.get_admin_dashboard(db, days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving admin dashboard: {str(e)}"
        )

# Invoice Routes
@router.post("/invoices", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: User = Depends(require_seller_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create an invoice from an order.
    
    Only sellers can create invoices for their own products.
    Admins can create invoices for any order.
    """
    try:
        # For sellers, they can only create invoices for their own products
        seller_id = current_user.id
        return await InvoiceService.create_invoice_from_order(
            db, invoice_data.order_id, seller_id, invoice_data.due_days
        )
    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating invoice: {str(e)}"
        )

@router.get("/invoices", response_model=InvoiceListResponse)
async def get_invoices(
    seller_id: Optional[uuid.UUID] = Query(None, description="Filter by seller ID"),
    status: Optional[InvoiceStatus] = Query(None, description="Filter by invoice status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get invoices with optional filtering.
    
    - Normal users: Can only see invoices for orders they placed
    - Sellers: Can only see their own invoices
    - Admins: Can see all invoices
    """
    try:
        # Apply role-based filtering
        if current_user.role == UserRole.NORMAL_USER:
            # Normal users can only see invoices for their orders
            # This would require additional logic to filter by user's orders
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Normal users cannot access invoice listings"
            )
        elif current_user.role == UserRole.SELLER:
            # Sellers can only see their own invoices
            seller_id = current_user.id
        
        return await InvoiceService.get_invoices(db, seller_id, status, skip, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving invoices: {str(e)}"
        )

@router.get("/invoices/{invoice_id}", response_model=InvoiceDetailResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific invoice with items.
    
    - Sellers: Can only view their own invoices
    - Admins: Can view any invoice
    """
    try:
        # First get the invoice to check permissions
        invoice_query = select(Invoice).where(Invoice.id == invoice_id)
        invoice_result = await db.execute(invoice_query)
        invoice = invoice_result.scalar_one_or_none()
        
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        
        # Check permissions
        if current_user.role == UserRole.NORMAL_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Normal users cannot access invoices"
            )
        elif current_user.role == UserRole.SELLER and invoice.seller_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own invoices"
            )
        
        return await InvoiceService.get_invoice(db, invoice_id)
    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving invoice: {str(e)}"
        )

@router.put("/invoices/{invoice_id}/status", response_model=Dict[str, Any])
async def update_invoice_status(
    invoice_id: uuid.UUID,
    status: InvoiceStatus,
    current_user: User = Depends(require_seller_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update invoice status.
    
    - Sellers: Can only update their own invoices
    - Admins: Can update any invoice
    """
    try:
        return await InvoiceService.update_invoice_status(db, invoice_id, status, current_user)
    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating invoice status: {str(e)}"
        )

@router.get("/invoices/{invoice_id}/pdf")
async def generate_invoice_pdf(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate PDF for an invoice.
    
    Returns the invoice as a PDF file.
    """
    try:
        # First get the invoice to check permissions
        invoice_query = select(Invoice).where(Invoice.id == invoice_id)
        invoice_result = await db.execute(invoice_query)
        invoice = invoice_result.scalar_one_or_none()
        
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        
        # Check permissions
        if current_user.role == UserRole.NORMAL_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Normal users cannot access invoices"
            )
        elif current_user.role == UserRole.SELLER and invoice.seller_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own invoices"
            )
        
        # Import PDF generator
        from src.dashboard.pdf_generator import PDFGenerator
        
        # Get invoice with items
        invoice_data = await InvoiceService.get_invoice(db, invoice_id)
        
        # Generate PDF
        pdf_content = await PDFGenerator.generate_invoice_pdf(invoice_data["data"])
        
        # Return PDF as response
        from fastapi.responses import Response
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"
            }
        )
        
    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating invoice PDF: {str(e)}"
        )
