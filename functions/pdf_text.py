import os
import io
from pypdf import PdfReader, PdfWriter
from google import genai
from functions.log_adder import add_log

def extract_text_hybrid(pdf_path: str, target_pages: list[int] = None) -> dict[int, str]:
    """Reads a PDF file page-by-page, selecting target indices or the entire document.
    
    Uses extremely fast local text extraction by default, and seamlessly escalates to 
    Gemini 2.5 Flash Vision OCR specifically for scanned text blocks, images, or legacy 
    rasterized data tables.

    Args:
        pdf_path (str): The physical system path layout location of the source PDF.
        target_pages (list[int], optional): A collection of 0-indexed page bounds to extract. 
            Defaults to None (processes all pages).

    Returns:
        dict[int, str]: A dictionary map linking individual physical page indexes (int) 
            to their corresponding clean text representations (str).
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    reader = PdfReader(pdf_path)
    pages_text = {}

    # Determine which precise pages to process safely
    if target_pages:
        indices_to_extract = [p for p in target_pages if 0 <= p < len(reader.pages)]
    else:
        indices_to_extract = list(range(len(reader.pages)))

    add_log(f"Extracting text from these pages: {indices_to_extract}", level='info', source='PDF_TEXT')
    
    for physical_idx in indices_to_extract:
        page = reader.pages[physical_idx]
        local_text = page.extract_text() or ""
        
        # Check if the page is layout-sparse (likely scanned image or legacy layout sheet)
        if len(local_text.strip()) < 50:
            add_log(f"Page {physical_idx + 1} has very little text, so it's probably a scanned image. Using AI vision to read it instead.", level='debug', source='PDF_TEXT')
            try:
                writer = PdfWriter()
                writer.add_page(page)
                pdf_buffer = io.BytesIO()
                writer.write(pdf_buffer)
                pdf_bytes = pdf_buffer.getvalue()
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        {'mime_type': 'application/pdf', 'data': pdf_bytes},
                        "Extract all financial tables and text from this page verbatim. Maintain rows, columns, and numeric precision."
                    ]
                )
                pages_text[physical_idx] = response.text + "\n"
                add_log(f"Successfully read Page {physical_idx + 1} using AI vision.", level='debug', source='PDF_TEXT')
            except Exception as e:
                add_log(f"Could not read page {physical_idx + 1} with AI vision: {e}", level='error', source='PDF_TEXT')
                pages_text[physical_idx] = "[Extraction Error: Scanned content unreadable]\n"
        else:
            pages_text[physical_idx] = local_text + "\n"

    return pages_text
