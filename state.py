# state.py
from pydantic import BaseModel, Field
from typing import List, Dict

class FinancialReportState(BaseModel):
    input_pdf: str = ""
    company_name: str = ""
    year: str = ""
    
    # Store the calculated physical pages (1-indexed) containing ALL statements combined
    statement_pages: List[int] = Field(default_factory=list)
    
    # NEW FIELD: Holds the mapped layout for individual sheets
    statement_pages_breakdown: Dict[str, List[int]] = Field(default_factory=dict)
    
    # Path to the generated cropped validation PDF file
    extracted_pdf: str = ""
    
    # Text extracted from the statement pages
    statements_json: str = ""
    
    # Calculated metrics
    financial_highlights_json: str = ""
    
    # Path to the compiled Excel workbook
    excel_file: str = ""
