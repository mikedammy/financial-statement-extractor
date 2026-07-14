from pathlib import Path
import json
import pandas as pd
from functions.log_adder import add_log


def build_excel(
    statements_json: str,
    highlights_json: str,
    output_file: str,
) -> str:
    """Compiles structured text strings tracking statement fields and indicators into an active Excel workbook.

    Generates multi-sheet tables representing Balance Sheets, Income Statements, and 
    Cash Flow records while preserving structural tree indentation offsets. Saves 
    intermediary raw data structures out to a secondary CSV matrix.

    Args:
        statements_json (str): Raw string array containing parsed accounting row dictionaries.
        highlights_json (str): Structural JSON tracking evaluation performance calculations.
        output_file (str): System file layout output name target.

    Returns:
        str: Absolute string mapping pointing to the newly established Excel storage file destination.

    Raises:
        json.JSONDecodeError: If inbound structured text packages are corrupted or malformed.
    """
    output_file = output_file.lower().strip().split()
    # Normalize path naming standard bounds across operating platform variations
    output_file = '_'.join(output_file)
    
    # Create output file target directory locations
    output_dir = Path("outputs/excel")
    json_dir = Path("outputs/json")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    excel_path = output_dir / output_file
    
    add_log("Starting to build the Excel file.", level='info', source='EXCEL_BUILDER')
    
    # Parse incoming raw document data matrices safely
    try:
        statements = json.loads(statements_json)
        financial_highlights = json.loads(highlights_json)
    except Exception as e:
        add_log(f"Could not read the input JSON data: {e}", level='error', source='EXCEL_BUILDER')
        raise e
    
    # ─── SAVE RAW JSON FOR DEBUGGING ────────────────
    try:
        base_name = Path(output_file).stem
        base_name = '_'.join(base_name.split("_")[:-1])
        
        statements_debug_path = json_dir / f"{base_name}_statements.json"
        highlights_debug_path = json_dir / f"{base_name}_highlights.json"
        
        with open(statements_debug_path, "w", encoding="utf-8") as f:
            f.write(statements_json)
        with open(highlights_debug_path, "w", encoding="utf-8") as f:
            f.write(highlights_json)
            
        add_log(f"Saved a copy of the raw JSON data for debugging to: {json_dir}/", level='debug', source='EXCEL_BUILDER')
    except Exception as e:
        add_log(f"Could not save the debug JSON files: {e}", level='warning', source='EXCEL_BUILDER')
        
    # Save target parameters out into standalone CSV sheets
    try:
        add_log("Saving the calculated metrics to a CSV file.", level='debug', source='EXCEL_BUILDER')
        rows = []
        for category, metrics in financial_highlights.items():
            for metric_name, value in metrics.items():
                rows.append({
                    "metric": metric_name,
                    "value": value
                })
        
        csv_dir = Path("outputs/csv")
        csv_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        csv_file_path = csv_dir / f"{base_name}_highlights.csv"
        df.to_csv(csv_file_path, index=False)
        add_log(f"Saved the metrics CSV file to: {csv_file_path}", level='info', source='EXCEL_BUILDER')
    except Exception as e:
        add_log(f"Could not create the CSV file: {e}", level='warning', source='EXCEL_BUILDER')

    with pd.ExcelWriter(excel_path) as writer:
        sheets_written = 0

        # Extract statement objects directly from explicit keys
        statement_items = []
        if isinstance(statements, dict):
            target_keys = ["balance_sheet", "income_statement", "cash_flow", "changes_in_equity"]
            for key in target_keys:
                if key in statements and statements[key] is not None:
                    statement_items.append(statements[key])
                elif "statements" in statements and isinstance(statements["statements"], dict):
                    if key in statements["statements"] and statements["statements"][key] is not None:
                        statement_items.append(statements["statements"][key])
        else:
            statement_items = []

        # Construct individual accounting tab representations
        for statement in statement_items:
            if not isinstance(statement, dict) or "statement_name" not in statement:
                continue

            sheet_name = statement["statement_name"][:31]
            extracted_columns = statement.get("columns", [])
            rows = []
            max_values_len = 0

            for row in statement.get("rows", []):
                values = row.get("values", [])
                max_values_len = max(max_values_len, len(values))
                
                # Apply structural indentations for child hierarchy lines using whitespace padding
                rows.append(
                    [("    " * row.get("level", 0)) + row.get("label", "")]
                    + values
                )

            if rows:
                columns = ["Account"] + extracted_columns[:max_values_len]
                
                # Dynamic pad execution columns to match parsed row overflow widths safely
                if len(columns) < (max_values_len + 1):
                    extra_needed = (max_values_len + 1) - len(columns)
                    columns += [f"Value Column {i+1}" for i in range(extra_needed)]
                
                df = pd.DataFrame(rows, columns=columns)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                sheets_written += 1
                add_log(f"Added a worksheet tab for: {sheet_name}", level='debug', source='EXCEL_BUILDER')

        # Build Financial Highlights sheet tab matrix
        highlight_rows = []
        if isinstance(financial_highlights, dict):
            for category, metrics in financial_highlights.items():
                if isinstance(metrics, dict):
                    for metric, value in metrics.items():
                        highlight_rows.append(
                            {
                                "Category": str(category).replace("_", " ").title(),
                                "Metric": str(metric).replace("_", " ").title(),
                                "Value": value,
                            }
                        )

        if highlight_rows:
            highlights_df = pd.DataFrame(highlight_rows)
            highlights_df.to_excel(writer, sheet_name="Financial Highlights", index=False)
            sheets_written += 1
            add_log("Added the Financial Highlights summary tab.", level='debug', source='EXCEL_BUILDER')

        # ─── SAFETY CRASH GUARD ───────────────────────────────────────────────
        if sheets_written == 0:
            add_log("No statement data was found, so an empty workbook is being created.", level='warning', source='EXCEL_BUILDER')
            df_empty = pd.DataFrame([{"Status": "No statement sheets could be generated"}])
            df_empty.to_excel(writer, sheet_name="Summary", index=False)
        # ───────────────────────────────────────────────────────────────────────

    add_log(f"Excel file built successfully at: {excel_path}", level='info', source='EXCEL_BUILDER')
    return str(excel_path)

