from pathlib import Path
import pypdf
import json
from google import genai
from google.genai import types
import os
import re
import sys
import time 
import random

from crewai.flow.flow import Flow, start, listen
from state import FinancialReportState

from crews.page_detection.crew import PageDetectionCrew
from crews.statement_extraction.crew import StatementExtractionCrew
from crews.financial_highlights.crew import FinancialHighlightsCrew
from crews.statement_extraction.crew import StatementExtractionOutput

from functions.pdf_text import extract_text_hybrid
from functions.pdf_extract import extract_pages
from functions.excel_builder import build_excel
from functions.pdf_scanner import fallback_pdf_scan
from functions.page_validator import validate_statement_pages
from functions.log_adder import add_log


class FinancialReportFlow(Flow[FinancialReportState]):
    """An agentic execution pipeline that orchestrates automated page selection,
    text targeting, data parsing, and excel compilation of corporate financial sheets.
    """

    @start()
    def detect_statement_pages(self):
        """Scans document structure using agent analysis or regular expressions to find physical target indices.

        Returns:
            FinancialReportState: The current active context state containing target ranges.

        Raises:
            ValueError: If no valid operational pages can be isolated for downstream components.
        """
        add_log("Starting to find the statement pages in the PDF.", level='info', source='FLOW')
        
        # 1. Gather cover text as before
        cover_text = ""
        reader = pypdf.PdfReader(self.state.input_pdf)
        total_pdf_pages = len(reader.pages)
        
        try:
            pages_to_read = min(5, total_pdf_pages)
            for i in range(pages_to_read):
                text_content = reader.pages[i].extract_text() or ""
                cover_text += f"--- PHYSICAL PAGE INDEX {i} ---\n{text_content}\n"
        except Exception as e:
            add_log(f"Could not read the first few pages of the PDF: {e}", level='warning', source='FLOW')

        # 2. Safely attempt Agentic Page Range Extraction
        llm_failed = False
        try:
            add_log("Asking the AI to find the statement pages.", level='debug', source='FLOW')
            result = PageDetectionCrew().crew().kickoff(inputs={"pdf_cover_text": cover_text})
            output = result.pydantic
            self.state.company_name = output.company_name
            self.state.year = output.year
        
            def _is_zeroed(pr):
                return pr is None or pr.start_page == 0
        
            if not output.statement_pages:
                llm_failed = True
            else:
                sp = output.statement_pages
                if any(_is_zeroed(pr) for pr in (
                    sp.balance_sheet, sp.income_statement, sp.cash_flow, sp.changes_in_equity
                )):
                    llm_failed = True
        except Exception as e:
            add_log(f"AI page detection did not return a valid result: {e}. Switching to the backup method.", level='warning', source='FLOW')
            llm_failed = True

        # 3. Resolve the target lists using either the LLM or your Heuristic Functional Module
        calibrated_pages = {}
        all_required_physical_pages = set()

        if llm_failed:
            add_log("Using the backup method to find statement pages.", level='info', source='FLOW')
            calibrated_pages = fallback_pdf_scan(self.state.input_pdf)
            calibrated_pages = validate_statement_pages(self.state.input_pdf, calibrated_pages)
            for page_list in calibrated_pages.values():
                all_required_physical_pages.update(page_list)
        else:
            add_log("AI page detection worked. Adjusting page numbers to match the PDF.", level='debug', source='FLOW')
            offset = output.first_numbered_page_physical_index - 1
            statement_map = output.statement_pages.model_dump()
            
            for name, range_data in statement_map.items():
                if range_data and range_data["start_page"] > 0:
                    printed_list = list(range(range_data["start_page"], range_data["end_page"] + 1))
                    physical_list = [p + offset for p in printed_list if 0 <= (p + offset) < total_pdf_pages]
                    calibrated_pages[name] = physical_list
                    all_required_physical_pages.update(physical_list)
                else:
                    calibrated_pages[name] = []

        self.state.statement_pages_breakdown = calibrated_pages
        self.state.statement_pages = sorted([p for p in all_required_physical_pages])
        
        add_log(f"Final list of pages found for each statement: {self.state.statement_pages_breakdown}", level='debug', source='FLOW')
        add_log(f"Pages that will be cut out of the PDF: {self.state.statement_pages}", level='debug', source='FLOW')

        # FIX: Replaced sys.exit() with an exception so main.py loop can capture and log it without crashing the script
        if not self.state.statement_pages:
            add_log("Stopping: no valid statement pages were found.", level='error', source='FLOW')
            raise ValueError("No matching statement pages could be determined via LLM or fallback heuristics.")

        return self.state

    @listen(detect_statement_pages)
    def extract_statement_pdf(self):
        """Crops the target full-length document down to isolated targets for optimization.

        Returns:
            FinancialReportState: The current active state context tracking file locations.
        """
        output_filename = f"{self.state.company_name}_{self.state.year}_statements.pdf"
        add_log(f"Cutting the relevant pages out of the PDF into a new file: {output_filename}", level='info', source='FLOW')
        
        extracted_pdf = extract_pages(
            input_pdf=self.state.input_pdf,
            pages=self.state.statement_pages,
            output_pdf=output_filename,
        )

        self.state.extracted_pdf = extracted_pdf
        return self.state

    @listen(extract_statement_pdf)
    def extract_statements(self):
        """Extracts characters from sub-documents and coordinates agent tasks for data mapping.

        Returns:
            FinancialReportState: Updated state tracking clean JSON data targets.
        """
        add_log("Reading the text from the cropped PDF.", level='info', source='FLOW')
        pages_dict = extract_text_hybrid(pdf_path=self.state.extracted_pdf)

        original_page_mapping = list(self.state.statement_pages)
        breakdown_0idx = self.state.statement_pages_breakdown
        breakdown = {
            key: [p for p in page_list]
            for key, page_list in breakdown_0idx.items()
        }

        def get_text_for_statement(statement_key: str) -> str:
            segments = []
            target_original_pages = breakdown.get(statement_key, [])

            for cropped_idx, text in pages_dict.items():
                if cropped_idx < len(original_page_mapping):
                    original_page = original_page_mapping[cropped_idx]
                    if original_page in target_original_pages:
                        segments.append(f"--- PHYSICAL PAGE {original_page} ---\n{text}")

            return "\n\n".join(segments) if segments else "No text found for this statement."

        bs_text = get_text_for_statement("balance_sheet")
        is_text = get_text_for_statement("income_statement")
        cf_text = get_text_for_statement("cash_flow")
        eq_text = get_text_for_statement("changes_in_equity")
        
        # ─── SAVE TEXT PAYLOADS FOR VERIFICATION & DEBUGGING ──────────────────
        txt_dir_name = f'{self.state.company_name}_{self.state.year}'
        os.makedirs(f"outputs/txt/{txt_dir_name}", exist_ok=True)
        segments_to_save = {
            "balance_sheet": bs_text,
            "income_statement": is_text,
            "cash_flow": cf_text,
            "changes_in_equity": eq_text
        }
        
        for name, content in segments_to_save.items():
            file_path = f"outputs/txt/{txt_dir_name}/{name}_segment.txt"
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                add_log(f"Saved extracted text to a debug file: {file_path}", level='debug', source='FLOW')
            except Exception as e:
                add_log(f"Could not save debug file {file_path}: {e}", level='warning', source='FLOW')
        # ─────────────────────────────────────────────
        
        add_log("Asking the AI to extract data from all four statements.", level='info', source='FLOW')
        crew_inputs = {
            "balance_sheet_text": bs_text,
            "income_statement_text": is_text,
            "cash_flow_text": cf_text,
            "equity_text": eq_text
        }
        
        crew_output = StatementExtractionCrew().crew().kickoff(inputs=crew_inputs)

        final_dict = {
            "balance_sheet": None,
            "income_statement": None,
            "cash_flow": None,
            "changes_in_equity": None
        }
        
        task_name_map = {
            "extract_balance_sheet_task": "balance_sheet",
            "extract_income_statement_task": "income_statement",
            "extract_cash_flow_task": "cash_flow",
            "extract_equity_task": "changes_in_equity",
        }

        try:
            for task_out in crew_output.tasks_output:
                if task_out.pydantic:
                    target_key = task_name_map.get(task_out.name)
                    if target_key:
                        final_dict[target_key] = task_out.pydantic.model_dump()
                    else:
                        add_log(f"Got an unexpected task name back from the AI: {task_out.name}", level='warning', source='FLOW')
        except Exception as e:
            add_log(f"Had trouble reading the AI's output, but continued: {e}", level='warning', source='FLOW')
        
        self.state.statements_json = json.dumps(final_dict, indent=4)
        return self.state

    @listen(extract_statements)
    def generate_financial_highlights(self):
        """Passes structured JSON strings to standard modeling structures for evaluation.

        Returns:
            FinancialReportState: Current execution state tracker containing evaluation calculations.
        """
        add_log("Pausing briefly to avoid hitting API rate limits.", level='debug', source='FLOW')
        time.sleep(random.uniform(15.0, 20.0))
        
        add_log("Sending the extracted data to the AI to calculate financial highlights.", level='info', source='FLOW')
        result = (
            FinancialHighlightsCrew()
            .crew()
            .kickoff(
                inputs={
                    "statements_json": self.state.statements_json
                }
            )
        )

        self.state.financial_highlights_json = result.pydantic.model_dump_json(indent=4)
        return self.state

    @listen(generate_financial_highlights)
    def build_excel_workbook(self):
        """Compiles generated JSON structural contexts into an Excel balance tracking file.

        Returns:
            FinancialReportState: Final terminal state container detailing execution paths.
        """
        output_excel_name = f"{self.state.company_name}_{self.state.year}_statements.xlsx"
        add_log(f"Building the Excel file: {output_excel_name}", level='info', source='FLOW')
        
        excel_file = build_excel(
            statements_json=self.state.statements_json,
            highlights_json=self.state.financial_highlights_json,
            output_file=output_excel_name,
        )

        self.state.excel_file = excel_file
        add_log("Excel file was built successfully.", level='info', source='FLOW')
        return self.state

