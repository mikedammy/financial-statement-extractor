from pathlib import Path
from pypdf import PdfReader, PdfWriter
from functions.log_adder import add_log

def extract_pages(
    input_pdf: str,
    pages: list[int],
    output_pdf: str,
) -> str:
    """Isolates specific target pages out of a larger file, rendering them into a smaller, optimized sub-PDF.

    Args:
        input_pdf (str): Local directory pathway location to parent PDF array structure.
        pages (list[int]): Collection tracking 0-indexed physical page targets for extraction.
        output_pdf (str): File name standard designated for output payload caching.

    Returns:
        str: Absolute system location point reference indicating the newly cropped PDF payload.
    """
    output_pdf = output_pdf.lower().strip().split()
    output_pdf = '_'.join(output_pdf)
    
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    
    add_log(f"Extracting these pages from the PDF: {pages}", level='info', source='PDF_EXTRACT')
    for page_num in pages:
        if 0 <= page_num < len(reader.pages):
            writer.add_page(reader.pages[page_num])
        else:
            add_log(f"Page {page_num} doesn't exist in this PDF (it only has pages 0-{len(reader.pages)-1}). Skipping it.", level='warning', source='PDF_EXTRACT')

    output_path = Path("outputs/pdf")
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / output_pdf

    with open(output_file, "wb") as pdf:
        writer.write(pdf)
        
    add_log(f"New PDF created successfully at: {output_file}", level='info', source='PDF_EXTRACT')
    return str(output_file)
