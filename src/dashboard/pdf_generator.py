from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import base64

class PDFGenerator:
    """PDF generator for invoices and other documents"""
    
    @staticmethod
    async def generate_invoice_pdf(invoice_data: Dict[str, Any]) -> bytes:
        """
        Generate PDF for an invoice
        
        Args:
            invoice_data: Dictionary containing invoice and items data
            
        Returns:
            bytes: PDF content as bytes
        """
        try:
            # Extract data
            invoice = invoice_data["invoice"]
            items = invoice_data["items"]
            
            # Create PDF buffer
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Create custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.darkblue
            )
            
            normal_style = styles['Normal']
            normal_style.fontSize = 10
            
            # Build story (content)
            story = []
            
            # Title
            story.append(Paragraph("INVOICE", title_style))
            story.append(Spacer(1, 20))
            
            # Invoice details table
            invoice_details_data = [
                ['Invoice Number:', invoice.invoice_number],
                ['Issue Date:', invoice.issue_date.strftime('%B %d, %Y')],
                ['Due Date:', invoice.due_date.strftime('%B %d, %Y')],
                ['Status:', invoice.status.value.upper()],
                ['Order Number:', f"ORD-{str(invoice.order_id)[:8].upper()}"]
            ]
            
            invoice_table = Table(invoice_details_data, colWidths=[2*inch, 3*inch])
            invoice_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(invoice_table)
            story.append(Spacer(1, 30))
            
            # Seller and Customer information
            info_data = [
                ['FROM:', 'TO:'],
                [f"{invoice.seller_name}", f"{invoice.customer_name}"],
                [f"{invoice.seller_email}", f"{invoice.customer_email}"],
                [f"{invoice.seller_address or 'N/A'}", f"{invoice.customer_address}"],
                [f"{invoice.seller_phone or 'N/A'}", ""]
            ]
            
            info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTSIZE', (0, 0), (1, 0), 12),
                ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 30))
            
            # Items table
            story.append(Paragraph("ITEMS", heading_style))
            
            # Table headers
            items_data = [
                ['Description', 'Qty', 'Unit Price', 'Total']
            ]
            
            # Add items
            for item in items:
                items_data.append([
                    f"{item.product_name}\n{item.product_description or ''}",
                    str(item.quantity),
                    f"${item.unit_price:.2f}",
                    f"${item.total_price:.2f}"
                ])
            
            items_table = Table(items_data, colWidths=[3.5*inch, 0.8*inch, 1*inch, 1*inch])
            items_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 20))
            
            # Totals
            totals_data = [
                ['Subtotal:', f"${invoice.subtotal:.2f}"],
                ['Tax:', f"${invoice.tax_amount:.2f}"],
                ['Total:', f"${invoice.total_amount:.2f}"]
            ]
            
            totals_table = Table(totals_data, colWidths=[4*inch, 2*inch])
            totals_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 14),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ]))
            
            story.append(totals_table)
            story.append(Spacer(1, 30))
            
            # Notes and Terms
            if invoice.notes:
                story.append(Paragraph("NOTES", heading_style))
                story.append(Paragraph(invoice.notes, normal_style))
                story.append(Spacer(1, 20))
            
            if invoice.terms:
                story.append(Paragraph("TERMS & CONDITIONS", heading_style))
                story.append(Paragraph(invoice.terms, normal_style))
                story.append(Spacer(1, 20))
            
            # Footer
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            
            story.append(Spacer(1, 20))
            story.append(Paragraph(
                f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Artisans Alley Platform",
                footer_style
            ))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF content
            buffer.seek(0)
            pdf_content = buffer.getvalue()
            buffer.close()
            
            return pdf_content
            
        except Exception as e:
            raise Exception(f"Error generating PDF: {str(e)}")

    @staticmethod
    async def generate_simple_invoice_pdf(invoice_data: Dict[str, Any]) -> bytes:
        """
        Generate a simpler PDF for invoices (fallback option)
        """
        try:
            invoice = invoice_data["invoice"]
            items = invoice_data["items"]
            
            # Create simple text-based PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            story.append(Paragraph("INVOICE", styles['Title']))
            story.append(Spacer(1, 20))
            
            # Invoice info
            story.append(Paragraph(f"Invoice #: {invoice.invoice_number}", styles['Normal']))
            story.append(Paragraph(f"Date: {invoice.issue_date.strftime('%Y-%m-%d')}", styles['Normal']))
            story.append(Paragraph(f"Due: {invoice.due_date.strftime('%Y-%m-%d')}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # From/To
            story.append(Paragraph("FROM:", styles['Heading2']))
            story.append(Paragraph(f"{invoice.seller_name}", styles['Normal']))
            story.append(Paragraph(f"{invoice.seller_email}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            story.append(Paragraph("TO:", styles['Heading2']))
            story.append(Paragraph(f"{invoice.customer_name}", styles['Normal']))
            story.append(Paragraph(f"{invoice.customer_email}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Items
            story.append(Paragraph("ITEMS:", styles['Heading2']))
            for item in items:
                story.append(Paragraph(
                    f"{item.product_name} - Qty: {item.quantity} - ${item.total_price:.2f}",
                    styles['Normal']
                ))
            story.append(Spacer(1, 20))
            
            # Total
            story.append(Paragraph(f"TOTAL: ${invoice.total_amount:.2f}", styles['Heading2']))
            
            doc.build(story)
            buffer.seek(0)
            pdf_content = buffer.getvalue()
            buffer.close()
            
            return pdf_content
            
        except Exception as e:
            raise Exception(f"Error generating simple PDF: {str(e)}")

    @staticmethod
    def format_currency(amount: Decimal) -> str:
        """Format decimal amount as currency string"""
        return f"${amount:.2f}"

    @staticmethod
    def format_date(date: datetime) -> str:
        """Format datetime as readable string"""
        return date.strftime('%B %d, %Y')
