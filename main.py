#!/usr/bin/env python3

"""
Invoice PDF Generator

This script generates a professional-looking PDF invoice from a TOML data file.
It is designed to be run from the command line, providing the path to the
TOML file as an argument.

Author: Your Name (or Gemini)
Version: 1.1.0
"""

import argparse
import sys
import toml
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

# Third-party library for PDF creation.
# Install with: pip install reportlab
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph # MODIFIED: Added Paragraph
    from reportlab.lib.styles import getSampleStyleSheet # ADDED: For paragraph styling
    from reportlab.lib.units import inch
except ImportError:
    print("Error: The 'reportlab' library is required. Please install it using 'pip install reportlab'.")
    sys.exit(1)


# --- Constants for PDF Layout ---
PAGE_WIDTH, PAGE_HEIGHT = letter
TOP_MARGIN = PAGE_HEIGHT - inch
BOTTOM_MARGIN = inch
LEFT_MARGIN = inch
RIGHT_MARGIN = PAGE_WIDTH - inch
CONTENT_WIDTH = PAGE_WIDTH - (2 * inch)


def format_currency(value: Decimal, symbol: str) -> str:
    """Formats a decimal value into a currency string (e.g., $1,234.50)."""
    return f"{symbol}{value:,.2f}"


def generate_invoice_pdf(data: dict, output_path: Path):
    """
    Generates the invoice PDF from the parsed TOML data.

    Args:
        data (dict): A dictionary containing all the invoice data.
        output_path (Path): The file path to save the generated PDF.
    """
    try:
        # --- Extract data from the dictionary for easier access ---
        sender = data.get('sender', {})
        client = data.get('client', {})
        invoice_info = data.get('invoice', {})
        items = data.get('items', [])
        financials = data.get('financials', {})
        terms = data.get('terms', {})

        # --- Basic Validation ---
        if not all([sender, client, invoice_info, items]):
            raise ValueError("Error: TOML file is missing one of the required sections: "
                             "[sender], [client], [invoice], or [[items]].")

        # --- Initialize Canvas ---
        c = canvas.Canvas(str(output_path), pagesize=letter)
        c.setTitle(f"Invoice #{invoice_info.get('number', 'N/A')} from {sender.get('name', 'N/A')}")

        # --- Draw Header ---
        c.setFont("Helvetica-Bold", 16)
        c.drawString(LEFT_MARGIN, TOP_MARGIN, sender.get('name', 'Sender Name Missing').upper())

        c.setFont("Helvetica-Bold", 24)
        c.drawRightString(RIGHT_MARGIN, TOP_MARGIN, "INVOICE")

        c.setFont("Helvetica", 10)
        c.drawRightString(RIGHT_MARGIN, TOP_MARGIN - 0.25 * inch, f"# {invoice_info.get('number', 'N/A')}")

        # --- Draw Client and Date Information ---
        y_pos = TOP_MARGIN - 1.5 * inch

        # Client Info (Bill To)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT_MARGIN, y_pos, "Bill To:")
        c.setFont("Helvetica", 10)
        
        client_name = client.get('name', 'Client Name Missing')
        client_address = client.get('address', 'Client Address Missing').strip().split('\n')
        
        c.drawString(LEFT_MARGIN, y_pos - 0.2 * inch, client_name)
        
        text_object = c.beginText(LEFT_MARGIN, y_pos - 0.4 * inch)
        text_object.setFont("Helvetica", 10)
        text_object.setLeading(14) # Line spacing
        for line in client_address:
            text_object.textLine(line.strip())
        c.drawText(text_object)
        
        # Date, Due Date, Balance Due
        info_x_pos = RIGHT_MARGIN - 1.5 * inch
        c.setFont("Helvetica", 10)
        c.drawString(info_x_pos, y_pos, "Date:")
        c.drawString(info_x_pos, y_pos - 0.25 * inch, "Due Date:")
        
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.white)
        c.rect(info_x_pos - 0.1 * inch, y_pos - 0.55 * inch, 2.6 * inch, 0.3 * inch, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.drawString(info_x_pos, y_pos - 0.5 * inch, "Balance Due:")

        c.setFont("Helvetica", 10)
        c.drawRightString(RIGHT_MARGIN, y_pos, invoice_info.get('issue_date', 'N/A'))
        c.drawRightString(RIGHT_MARGIN, y_pos - 0.25 * inch, invoice_info.get('due_date', 'N/A'))
        

        # --- Calculate Totals ---
        currency_symbol = invoice_info.get('currency_symbol', '$')
        tax_rate = Decimal(str(financials.get('tax_rate', 0.0)))

        subtotal = Decimal(0)
        for item in items:
            quantity = Decimal(str(item.get('quantity', 0)))
            rate = Decimal(str(item.get('rate', 0)))
            subtotal += quantity * rate
        
        tax_amount = (subtotal * (tax_rate / Decimal(100))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = subtotal + tax_amount

        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(RIGHT_MARGIN, y_pos - 0.5 * inch, format_currency(total, currency_symbol))

        # --- Draw Items Table ---
        y_pos -= 1.5 * inch # Move down for the table

        # ADDED: Get a default stylesheet for paragraphs
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        normal_style.fontName = 'Helvetica'
        normal_style.fontSize = 10
        
        table_header = ['Item', 'Quantity', 'Rate', 'Amount']
        table_data = [table_header]
        
        for item in items:
            quantity = Decimal(str(item.get('quantity', 0)))
            rate = Decimal(str(item.get('rate', 0)))
            amount = (quantity * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            # MODIFIED: Wrap the description in a Paragraph object for automatic line wrapping
            description_paragraph = Paragraph(item.get('description', 'N/A'), normal_style)
            
            table_data.append([
                description_paragraph,
                str(quantity),
                format_currency(rate, currency_symbol),
                format_currency(amount, currency_symbol)
            ])

        table = Table(table_data, colWidths=[CONTENT_WIDTH * 0.55, CONTENT_WIDTH * 0.15, CONTENT_WIDTH * 0.15, CONTENT_WIDTH * 0.15])
        
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkslategray),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), # Align numeric columns to the right
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ])
        table.setStyle(style)

        table.wrapOn(c, CONTENT_WIDTH, y_pos)
        table.drawOn(c, LEFT_MARGIN, y_pos - table._height)
        
        y_pos -= table._height + 0.5 * inch

        # --- Draw Totals Section ---
        c.setFont("Helvetica", 10)
        c.drawRightString(RIGHT_MARGIN - 1 * inch, y_pos, "Subtotal:")
        c.drawRightString(RIGHT_MARGIN - 1 * inch, y_pos - 0.25 * inch, f"Tax ({tax_rate}%):")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(RIGHT_MARGIN - 1 * inch, y_pos - 0.5 * inch, "Total:")

        c.setFont("Helvetica", 10)
        c.drawRightString(RIGHT_MARGIN, y_pos, format_currency(subtotal, currency_symbol))
        c.drawRightString(RIGHT_MARGIN, y_pos - 0.25 * inch, format_currency(tax_amount, currency_symbol))
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(RIGHT_MARGIN, y_pos - 0.5 * inch, format_currency(total, currency_symbol))

        # --- Draw Terms ---
        y_pos = BOTTOM_MARGIN + 1 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT_MARGIN, y_pos, "Terms:")
        c.setFont("Helvetica", 10)
        c.drawString(LEFT_MARGIN, y_pos - 0.2 * inch, terms.get('notes', ''))

        # --- Save PDF ---
        c.save()
        print(f"✅ Successfully generated invoice at: {output_path}")

    except FileNotFoundError:
        print(f"Error: Could not find the input file at the specified path.", file=sys.stderr)
        sys.exit(1)
    except ValueError as ve:
        print(str(ve), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during PDF generation: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Main function to parse arguments and run the generator."""
    parser = argparse.ArgumentParser(
        description="Generate a PDF invoice from a TOML data file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "toml_file",
        type=Path,
        help="Path to the TOML file containing the invoice data."
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Path to save the output PDF file.\n"
             "If not provided, it will be saved in the current directory as:\n"
             "Invoice-[ClientName]-[Date].pdf"
    )
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    try:
        data = toml.load(args.toml_file)
    except FileNotFoundError:
        print(f"Error: The input file '{args.toml_file}' was not found.", file=sys.stderr)
        sys.exit(1)
    except toml.TomlDecodeError as e:
        print(f"Error: Could not parse the TOML file. Please check its syntax.\nDetails: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output
    if not output_path:
        client_name = data.get('client', {}).get('name', 'Client').replace(' ', '_').replace(',', '')
        issue_date = data.get('invoice', {}).get('issue_date', 'date').replace(' ', '_')
        output_path = Path(f"Invoice-{client_name}-{issue_date}.pdf")
        
    generate_invoice_pdf(data, output_path)


if __name__ == "__main__":
    main()
