import pypdf
import re
from functions.log_adder import add_log

def fallback_pdf_scan(pdf_path: str) -> dict:
    """Sequentially scans the target bounds of a document using comprehensive token patterns.

    Isolates explicit sheet ranges to keep target execution context narrow and 
    highly accurate when primary structural agent mappings are absent.

    Args:
        pdf_path (str): File destination point mapping to the document under review.

    Returns:
        dict: A map of core reporting terms associated with their matching page indices.

    Raises:
        RuntimeError: If structural validation rules evaluate completely empty arrays across the canvas.
    """
    add_log("Starting the backup scan using text keyword matching.", level='info', source='PDF_SCANNER')
    
    calibrated_pages = {
        "balance_sheet": [], 
        "income_statement": [], 
        "cash_flow": [], 
        "changes_in_equity": []
    }
    
    def heading_near_top(text_lower: str, headings: list[str], window: int = 100) -> bool:
        """Determines if a target text signature occurs directly inside the top boundary window.

        Args:
            text_lower (str): Lowercase document string context parameters.
            headings (list[str]): Matching title phrases to scan against.
            window (int): Total initial characters to isolate for verification. Defaults to 100.

        Returns:
            bool: True if matching criteria appear inside the layout boundary window.
        """
        head = text_lower[:window]
        return any(h in head for h in headings)

    balance_sheet_headings = ["statement of financial position", "balance sheet"]
    balance_sheet_signals = [
        r'total assets',
        r'total liabilities',
        r'total equity',
        r'non-current assets',
        r'current liabilities',
        r'property,?\s*plant\s*(?:and|&)\s*equipment',
    ]

    income_statement_headings = [
        "statement of profit or loss",
        "statement of comprehensive income",
        "income statement",
        "statement of other comprehensive income"
    ]
    income_statement_signals = [
        r'revenue',
        r'cost of sales',
        r'gross profit',
        r'profit before tax',
        r'profit for the year',
        r'earnings per share',
    ]

    cash_flow_headings = [
        "statement of cash flows",
        "cash flow statement",
        "statement of cash flow",
    ]
    cash_flow_signals = [
        r'cash flows? from operating activities',
        r'cash flows? from investing activities',
        r'cash flows? from financing activities',
        r'net increase.*cash',
        r'net decrease.*cash',
        r'cash and cash equivalents at (?:the )?end',
    ]

    equity_headings = [
        "statement of changes in equity",
        "statement of change in equity",
    ]
    equity_signals = [
        r'share capital',
        r'share premium',
        r'retained earnings',
        r'balance at \d',
        r'balance as at',
        r'total comprehensive profit|loss|income for the year|period',
        r'for the year|period ended \d{1,2}.*\d{4}'
    ]

    def matches(text_lower, headings, signals, min_signals=2):
        """Validates alignment metrics against keyword criteria structures."""
        if not heading_near_top(text_lower, headings):
            return False
        hit_count = sum(1 for s in signals if re.search(s, text_lower))
        num_pattern = r'\d{1,3}(?:,\d{3})+|\(\d{1,3}(?:,\d{3})+\)'
        num_check = re.search(num_pattern, text_lower)
        return bool(num_check and (hit_count >= min_signals))

    try:
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        scan_limit = min(40, total_pages)
        
        add_log(f"Checking the first {scan_limit} pages for statement keywords.", level='debug', source='PDF_SCANNER')
        
        for idx in range(scan_limit):
            # Safe internal utility lookahead extraction layer integration
            from functions.pdf_text import extract_text_hybrid
            result = extract_text_hybrid(pdf_path=pdf_path, target_pages=[idx])
            text_lower = result.get(idx, "").lower()

            if not text_lower.strip():
                continue

            all_statement_keys = [
                "statement of", "balance sheet", "financial position",
                "profit or loss", "income statement", "cash flow",
                "cash flows", "changes in equity", "change in equity"
            ]
            if sum(k in text_lower for k in all_statement_keys) >= 4:
                add_log(f"Page {idx + 1}: Skipping this page, it looks like a table of contents.", level='debug', source='PDF_SCANNER')
                continue

            if "notes to the " in text_lower:
                continue

            narrative_markers = [
                "directors' report", "directors report", "independent auditor",
                "corporate governance", "chairman's statement", "management discussion",
            ]
            if any(m in text_lower for m in narrative_markers):
                continue

            if matches(text_lower, balance_sheet_headings, balance_sheet_signals):
                calibrated_pages["balance_sheet"].append(idx)
                add_log(f"Found what looks like a balance sheet on page: {idx + 1}", level='debug', source='PDF_SCANNER')

            if matches(text_lower, income_statement_headings, income_statement_signals):
                calibrated_pages["income_statement"].append(idx)
                add_log(f"Found what looks like an income statement on page: {idx + 1}", level='debug', source='PDF_SCANNER')

            if matches(text_lower, cash_flow_headings, cash_flow_signals):
                calibrated_pages["cash_flow"].append(idx)
                add_log(f"Found what looks like a cash flow statement on page: {idx + 1}", level='debug', source='PDF_SCANNER')

            if matches(text_lower, equity_headings, equity_signals):
                calibrated_pages["changes_in_equity"].append(idx)
                add_log(f"Found what looks like a statement of changes in equity on page: {idx + 1}", level='debug', source='PDF_SCANNER')
            
    except Exception as e:
        add_log(f"Something went wrong while scanning the PDF for keywords: {e}", level='error', source='PDF_SCANNER')

    # FIX: Replaced sys.exit() with an exception to keep main pipeline loops active on isolated bad documents
    if all(not p_list for p_list in calibrated_pages.values()):
        add_log("The backup scanner could not find any statement pages.", level='error', source='PDF_SCANNER')
        raise RuntimeError("Matrix text lookup routine returned zero valid financial ranges across evaluation parameters.")
    
    add_log(f"Finished scanning. Pages found for each statement: {calibrated_pages}", level='info', source='PDF_SCANNER')
    return calibrated_pages
