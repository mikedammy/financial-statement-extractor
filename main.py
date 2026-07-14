import argparse
from pathlib import Path
from dotenv import load_dotenv
import time

from flow import FinancialReportFlow
from functions.log_adder import add_log

load_dotenv()

# Prevent CrewAI cache warning clutter
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg


def get_pdf_files(files_or_dirs: list[str], is_directory_mode: bool) -> list[Path]:
    """Gathers a list of unique Path objects pointing to valid PDFs based on input arguments.

    Args:
        files_or_dirs (list[str]): A list of file or directory paths provided by the user.
        is_directory_mode (bool): If True, treats elements in files_or_dirs as directory paths to scan.

    Returns:
        list[Path]: A cleanly sorted list of unique, verified PDF file paths.
    """
    pdf_paths = []
    
    if is_directory_mode:
        for path_str in files_or_dirs:
            dir_path = Path(path_str.strip())
            if dir_path.is_dir():
                add_log(f"Looking for PDF files in this folder: {dir_path}", level='debug', source='MAIN')
                # Glob all files ending in .pdf or .PDF inside the directory
                found_pdfs = list(dir_path.glob("*.pdf")) + list(dir_path.glob("*.PDF"))
                pdf_paths.extend(found_pdfs)
            else:
                add_log(f"'{path_str}' is not a valid folder, so it's being skipped.", level='warning', source='MAIN')
    else:
        for path_str in files_or_dirs:
            file_path = Path(path_str.strip())
            if file_path.is_file() and file_path.suffix.lower() == '.pdf':
                pdf_paths.append(file_path)
            else:
                add_log(f"'{path_str}' is not a PDF file, so it's being skipped.", level='warning', source='MAIN')
                
    return sorted(list(set(pdf_paths)))  # Remove duplicates and sort cleanly


def main():
    """Execution entry point for the batch processing pipeline.
    
    Parses CLI arguments, converts raw string inputs into targets via `get_pdf_files`, 
    and iterates over files sequentially using `FinancialReportFlow`.
    """
    parser = argparse.ArgumentParser(description='A financial statement extractor batch flow.')
    
    # Accept one or more inputs positional strings
    parser.add_argument('inputs', type=str, nargs='*', 
                        help='One or more file paths, or directory paths if using the -d/--directory flag.')
    
    # The flag toggle to shift behavior from file processing to directory scanning
    parser.add_argument('-d', '--directory', action='store_true', 
                        help='Treat the input arguments as directory names to scan for PDFs.')

    args = parser.parse_args()
    
    # Fallback check if user forgot to provide any positional inputs
    if not args.inputs:
        add_log("No files or folders were given, so the program is stopping.", level='error', source='MAIN')
        parser.error("No input files or directories provided.")

    # 1. Resolve and gather all target PDF paths
    target_pdfs = get_pdf_files(args.inputs, is_directory_mode=args.directory)
    
    # FIX: Converted path objects to strings before using '\n'.join() and corrected typo sourcr='MAIN' -> source='MAIN'
    target_strings = [str(p) for p in target_pdfs]
    add_log(f"Starting batch processing on these files:\n{'\n'.join(target_strings).strip()}", level='info', source='MAIN')

    if not target_pdfs:
        add_log("No valid PDF files were found, so processing is stopping.", level='critical', source='MAIN')
        return

    add_log(f"Found {len(target_pdfs)} PDF file(s) to process.", level='info', source='MAIN')

    # 2. Iterate and process each PDF through your flow sequentially
    for index, pdf_path in enumerate(target_pdfs, start=1):
        add_log(f"[{index}/{len(target_pdfs)}] Starting to process: {pdf_path.name}", level='info', source='MAIN')
        start_time = time.time()
        
        try:
            flow = FinancialReportFlow()
            result = flow.kickoff(
                inputs={
                    "input_pdf": str(pdf_path)
                }
            )
            elapsed = time.time() - start_time
            add_log(f"Finished processing {pdf_path.name} in {elapsed:.2f} seconds.", level='info', source='MAIN')
            add_log(f"Preview of the result: {str(result)[:200]}...", level='debug', source='MAIN')
            time.sleep(3)
            
        except Exception as e:
            # Replaced sys.exit conditions down the pipeline bubble up safely here
            add_log(f"Failed to process {pdf_path.name}. Error: {e}", level='error', source='MAIN')
            # Continues execution loop for remaining documents instead of a hard crash
            continue

    add_log("Batch processing is complete.", level='info', source='MAIN')


if __name__ == "__main__":
    main()
