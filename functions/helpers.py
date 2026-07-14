from pathlib import Path
from functions.log_adder import add_log

def sanitize_filename(text: str) -> str:
    """Cleans inbound raw text lines into uniform, filesystem-safe string structures.

    Removes spaces, platform path delimiters, and slashes to safeguard localized file creation routines.

    Args:
        text (str): Raw name or input title context.

    Returns:
        str: Uniformly structured text using snake_case syntax guidelines.
    """
    cleaned = (
        text.strip()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
    )
    add_log(f"Cleaned up the text so it's safe to use as a filename: '{cleaned}'", level='debug', source='HELPERS')
    return cleaned


def ensure_directory(path: str) -> None:
    """Verifies existence of an output directory route, building it out on the canvas if missing.

    Args:
        path (str): Intended file system target folder location path string.
    """
    target_path = Path(path)
    if not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)
        add_log(f"Folder didn't exist, so it was created: '{path}'", level='info', source='HELPERS')
    else:
        add_log(f"Confirmed the folder already exists: '{path}'", level='debug', source='HELPERS')

