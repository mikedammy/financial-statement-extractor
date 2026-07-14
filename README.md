# Financial Report Extraction Pipeline

This project takes a company's annual report (a PDF, often 100+ pages) and turns it into a clean Excel workbook with the four main financial statements and a set of calculated financial ratios.

You give it a PDF. You get back a spreadsheet with:
- Balance Sheet
- Income Statement
- Cash Flow Statement
- Statement of Changes in Equity
- A "Financial Highlights" sheet with ratios like ROE, current ratio, debt-to-equity, etc.

It's built to run on limited hardware, like a phone, through Google Colab, and to avoid burning through API rate limits, which is why it's careful about how much text it sends to the AI models at each step.

---

## How it works (the actual workflow)

Annual reports are long, and most of the pages aren't the financial statements — they're photos of the CEO, marketing copy, notes, disclaimers, and so on. Sending the whole PDF to an AI model would be slow, expensive, and error-prone. So instead, the pipeline finds the right pages first, and only looks closely at those.

Here's the step-by-step:

**1. Find the statement pages**
The pipeline reads the first few pages of the PDF, looking for the Table of Contents. An AI agent reads that TOC and figures out which printed page numbers the four statements start and end on. Annual reports print their own page numbers (which don't usually match the PDF's actual page order, because of cover pages, intro sections, etc.), so the pipeline also figures out the offset between "the page number printed on the page" and "the actual page in the PDF file."

If the AI can't find a usable Table of Contents (some reports don't have one, or it fails to parse), there's a backup plan: a page-by-page scanner that looks for known financial statement headings and keywords instead.

**2. Cut out just those pages**
Once it knows which pages matter, it crops the original PDF down to only those pages. This keeps everything downstream small and fast.

**3. Read the text off those pages**
Most pages have text you can just pull out directly. But some pages are scanned images instead of real text (common in older or lower-quality PDFs). For those, the pipeline sends just that page to Google's Gemini model to read it via OCR. This "hybrid" approach means it only pays the OCR cost when it actually needs to.

**4. Turn the raw text into structured data**
Each of the four statements gets sent to an AI model separately, one at a time, and turned into clean structured data — labeled rows, correct hierarchy (e.g. "Current Assets" containing "Cash," "Receivables," etc.), and the actual numbers. Processing them one at a time (rather than all at once) keeps each request small and avoids overwhelming the model with irrelevant context from the other statements.

**5. Calculate the financial ratios**
Once the four statements are structured, another AI step calculates standard financial ratios from them (margins, liquidity ratios, debt ratios, cash flow metrics, etc.) using the actual extracted numbers — it's not allowed to guess or estimate, only calculate from what's there.

**6. Build the Excel file**
Finally, everything gets assembled into a multi-sheet Excel workbook: one sheet per statement, plus a Financial Highlights sheet with all the ratios.

```
PDF in
  │
  ▼
Find statement pages (AI reads Table of Contents, or falls back to keyword scan)
  │
  ▼
Crop PDF down to just those pages
  │
  ▼
Extract text (direct read, or OCR for scanned pages)
  │
  ▼
Structure each statement into clean data (one at a time)
  │
  ▼
Calculate financial ratios
  │
  ▼
Excel file out
```

---

## Why it's built this way

**Only AI where it's actually needed.** Cropping a PDF, matching page numbers, and building an Excel file don't need an AI model — they're just code, and code is faster, cheaper, and more predictable. AI is only used for the two things that genuinely need judgment: reading a messy Table of Contents, and turning unstructured text into structured data.

**Small pieces, not one big request.** Instead of dumping the whole report at an AI model and hoping it sorts everything out, the pipeline breaks the work into small, focused pieces — one statement at a time. This is cheaper, less likely to produce mixed-up or hallucinated data, and much less likely to hit rate limits.

**OCR only when needed.** Reading text directly from a PDF is instant and free. OCR (having an AI "look" at a page like an image) is slower and costs more. The pipeline checks each page first and only falls back to OCR when the direct text extraction comes back mostly empty (i.e. the page is a scanned image).

**Automatic backup plans.** If the AI fails to read the Table of Contents properly, there's a fallback scanner that looks for statement headings directly. If an AI provider gets rate-limited, the system is set up to switch to a backup model automatically rather than just failing.

**Everything gets checked before moving forward.** At each handoff between steps, the data has to match a strict expected format (using Pydantic, a Python data-validation library). If something doesn't match the expected shape, it gets caught immediately instead of quietly corrupting later steps.

---

## Project layout

```
src/financial-report-flow/
├── config/
│   └── llm.py                  # AI model setup and fallback config
├── crews/
│   ├── page_detection/         # Finds which pages have the statements
│   ├── statement_extraction/   # Turns statement text into structured data
│   └── financial_highlights/   # Calculates the ratios
├── functions/
│   ├── pdf_extract.py          # Crops the PDF
│   ├── pdf_text.py             # Reads text (with OCR fallback)
│   ├── pdf_scanner.py          # Backup page-finder if AI page detection fails
│   ├── page_validator.py       # Double-checks pages actually match their statement
│   └── excel_builder.py        # Builds the final Excel file
├── flow.py                     # Runs all the steps in order
├── state.py                    # Tracks data as it moves through the steps
├── .env                        # The dotenv file to store your API keys
└── main.py                     # Entry point — run this to process a PDF

outputs/
├── pdf/     # The cropped PDF (just the statement pages)
├── txt/     # Raw extracted text per statement, for debugging
├── json/    # Structured data before it becomes Excel
└── excel/   # The final workbook
```

---

## What it's built with

- **CrewAI** — runs the AI agents and the overall step-by-step flow
- **Pydantic** — validates that data matches the expected shape at every step
- **Groq / Gemini** — the AI models used for reading and structuring data
- **PyPDF** — reads and crops PDF files
- **Pandas / OpenPyXL** — builds the Excel file
- Python 3.10+

---

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/financial-report-flow.git
cd financial-report-flow
pip install crewai pypdf pandas openpyxl pydantic python-dotenv litellm
```

### Setting up your AI models

There are a couple llm instances in `config/llm.py` that look like this:

```python
llm = LLM(
    model="provider/model",
    api_key=os.getenv("PROVIDER_API_KEY"),
    temperature=0.0
)
```

Here's what you'll do:

1. Go tot the`.env` file or create one and add as many provider API keys as you need, e.g.:

   ```text
   GROQ_API_KEY=...
   GEMINI_API_KEY=...
   ```

2. In `llm.py`, update/change the llm instances if you're using other providers and models.

3. In each of the 3 crew files (`page_detection`, `statement_extraction`, `financial_highlights`), import the LLM you want to use for that agent:

   ```python
   from config.llm import gemini_llm  # change to whatever you called your LLM
   ```

4. Then pass it into the `Agent` instance:

   ```python
   llm=gemini_llm,  # change to whatever you called your LLM
   ```


---

## Running it

Supports batch processing. main.py accepts individual PDF files, multiple PDF files, or directories (using the -d/--directory flag) and processes all discovered PDFs sequentially.

```bash
# For a single PDF file
python src/financial-report-flow/main.py annual_report.pdf
# For multiple PDF files
python src/financial-report-flow/main.py report1.pdf report2.pdf report3.pdf
# For a single directory
python src/financial-report-flow/main.py -d reports/
# For multiple directories
python src/financial-report-flow/main.py -d reports_2024/ reports_2025/
```

That's it — it runs through all the steps automatically and drops the finished Excel file in `outputs/excel/` with debug text and json files in `outputs/txt/` and `outputs/json/` respectively.

---

## What you get out of it

**Financial statements**, each as its own Excel sheet:
- Balance Sheet
- Income Statement
- Cash Flow Statement
- Statement of Changes in Equity

**A Financial Highlights sheet**, with ratios grouped into:

- **Profitability** — gross margin, EBITDA margin, operating margin, net margin, ROA, ROE, ROCE, effective tax rate
- **Liquidity** — current ratio, quick ratio, cash ratio, net working capital
- **Solvency** — debt-to-equity, debt ratio, equity multiplier, interest coverage
- **Efficiency** — asset turnover, days sales/inventory/payable outstanding, cash conversion cycle
- **Cash flow quality** — operating cash flow, free cash flow, quality of earnings, capital reinvestment ratio

---

## Known limitations / what's next

- No automated tests yet — verification so far has been manual, against real annual reports
- Only tested on a limited set of report formats/layouts; unusual layouts may need more work on the fallback page-scanner
- Excel formatting is functional but basic (no styling, borders, conditional formatting yet)
- No logging/monitoring beyond console prints
- Parallel processing is not yet implemented.
