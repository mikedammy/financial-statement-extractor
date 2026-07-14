"""
Quick diagnostic: dump what extract_text_hybrid actually returns
for the first N pages, so we can see whether:
  (a) local pypdf text extraction is working at all, or
  (b) it's falling to Gemini OCR and what that's returning, or
  (c) everything is coming back empty/error strings.

Run from your project root (same place you run main.py):
    python3 debug_scan.py inputs/neimeth_2022.pdf
"""
import sys
from functions.pdf_text import extract_text_hybrid
from pypdf import PdfReader

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 debug_scan.py <path_to_pdf> [num_pages]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    num_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    reader = PdfReader(pdf_path)

    for idx in range(num_pages):
        result = extract_text_hybrid(pdf_path=pdf_path, target_pages=[idx])
        text = result.get(idx, "<<NO TEXT RETURNED FOR THIS INDEX>>")
        # no_text = text == "<<NO KEY RETURNED FOR THIS INDEX>>"
        # page = reader.pages[idx]
        # text = page.extract_text() or ''
        
        print("=" * 60)
        print(f"PAGE INDEX {idx}  (length={len(text)})")
        print("-" * 60)
        # Print first 300 chars so we can see what's actually there
        print(text[:300])
        print()

if __name__ == "__main__":
    main()
