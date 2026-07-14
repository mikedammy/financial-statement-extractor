import pypdf
import re
from functions.pdf_text import extract_text_hybrid
from functions.log_adder import add_log


def validate_statement_pages(pdf_path: str, calibrated_pages: dict) -> dict:
    """Re-examines each physical page already assigned to a statement type
    (from either the LLM/TOC path or the heuristic fallback) and drops
    any page that doesn't actually look like that statement's content.

    This exists because BOTH the LLM's TOC-range inference and the
    regex heuristic scanner can over-include pages (e.g. notes pages,
    directors' reports, or unrelated pages caught by a wide inferred
    range). Feeding those extra pages to the extraction crew wastes
    tokens and API calls without adding real data.

    Args:
        pdf_path: Path to the PDF the physical page indices refer to
                   (0-indexed page numbers, matching pypdf convention).
        calibrated_pages: dict like
            {"balance_sheet": [4,5,6], "income_statement": [7,8], ...}

    Returns:
        A new dict with the same keys, but each list filtered down to
        pages that pass a relevance check for that statement type.
    """
    add_log("Double-checking that each page actually matches its assigned statement type.", level='info', source='PAGE_VALIDATOR')

    number_pattern = r'\d{1,3}(?:,\d{3})+|\(\d{1,3}(?:,\d{3})+\)'

    # heading phrase(s), supporting signal regexes, min signals required
    checks = {
        "balance_sheet": (
            ["statement of financial position", "balance sheet"],
            [
                r'total assets',
                r'total liabilities',
                r'total equity',
                r'non-current assets',
                r'current liabilities',
                r'property,?\s*plant\s*(?:and|&)\s*equipment', number_pattern
        ],
            2,
        ),
        "income_statement": (
            [
                "statement of profit or loss",
                "statement of comprehensive income",
                "income statement",
                "statement of other comprehensive income"
        ],
            [
                r'revenue', r'sales', r'cost of sales',
                r'cost of goods sold', r'cogs',
                r'gross profit', r'net profit',
                r'operating expense|expenses|profit',
                r'profit|income|loss for the year*',
                r'earnings per share', r'eps',
                r'ebit', r'ebitda', 
                r'total comprehensive'
                r'loss', r'\btax\w*',
                number_pattern
        ],
            3,
        ),
        "cash_flow": (
            [
                "cash flows", "cash flow statement",
                "statement of cash flow"
        ],
            [
                r'cash flows? .* from operating activities',
                r'cash flows? .* from investing activities',
                r'cash flows? .* from financing activities',
                r'net increase.*cash',
                r'net decrease.*cash',
                r'cash and cash equivalents.*at (?:the )?end', number_pattern
        ],
            2,
        ),
        "changes_in_equity": (
            ["changes in equity", "change in equity"],
            [
                r'share capital',
                r'share premium',
                r'retained earnings',
                r'balance at \d',
                r'balance as at',
                r'total comprehensive profit|loss|income for the year|period',
                r'for the year|period ended \d{1,2}.*\d{4}', number_pattern
        ],
            2,
        ),
    }

    exclusion_markers = [
        "notes to the",
        "independent auditor",
        "directors' report",
        "directors report",
        "corporate governance",
    ]

    validated = {key: [] for key in calibrated_pages}

    try:
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)

        text_cache = {}

        def get_text(idx):
            if idx not in text_cache:
                if 0 <= idx < total_pages:
                    tmp_out = extract_text_hybrid(
                        pdf_path=pdf_path,
                        target_pages=[idx]
                    )
                    text_cache[idx] = tmp_out.get(idx, "").lower()
                else:
                    text_cache[idx] = ""
            return text_cache[idx]

        for statement_key, page_list in calibrated_pages.items():
            headings, signals, min_signals = checks.get(statement_key, ([], [], 99))

            for phys_idx in page_list:
                text_lower = get_text(phys_idx)

                if not text_lower.strip():
                    add_log(f"Removing page {phys_idx + 1} from '{statement_key}': no readable text found on this page.", level='debug', source='PAGE_VALIDATOR')
                    continue

                if any(marker in text_lower[:100] for marker in exclusion_markers):
                    add_log(f"Removing page {phys_idx + 1} from '{statement_key}': this page looks like notes or a report, not a statement.", level='debug', source='PAGE_VALIDATOR')
                    continue

                has_heading = any(h in text_lower[:200] for h in headings) if headings else True
                signal_hits = sum(1 for s in signals if re.search(s, text_lower))

                if has_heading or signal_hits >= min_signals:
                    validated[statement_key].append(phys_idx)
                else:
                    add_log(f"Removing page {phys_idx + 1} from '{statement_key}': heading found = {has_heading}, matching signals = {signal_hits}/{min_signals}.", level='debug', source='PAGE_VALIDATOR')

    except Exception as e:
        add_log(f"Something went wrong while validating pages: {e}. Using the original, unfiltered page list instead.", level='error', source='PAGE_VALIDATOR')
        return calibrated_pages

    add_log(f"Finished validating pages. Filtered page list: {validated}", level='info', source='PAGE_VALIDATOR')
    return validated
