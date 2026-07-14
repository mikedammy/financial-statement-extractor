import logging
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent
log_file_path = parent_dir / 'flow_logs.log'

# Use a dedicated, named logger instead of the root logger.
# This means library code that calls logging.info(...) elsewhere in the
# process does NOT get routed through our formatter (which would crash,
# since our format string requires a 'source' field those records won't have).
_logger = logging.getLogger("pipeline")
_logger.setLevel(logging.DEBUG)  # let the logger accept everything; handlers filter

if not _logger.handlers:
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] [%(source)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    _logger.addHandler(file_handler)
    _logger.addHandler(console_handler)

    # Don't propagate to the root logger, or CrewAI/other libraries'
    # root-level handlers could print/duplicate these lines too.
    _logger.propagate = False

_VALID_LEVELS = {"debug", "info", "warning", "error", "critical"}


def add_log(message, level="info", source="UNKNOWN"):
    """A simple wrapper function to add logs dynamically with a custom source."""
    level = level.lower()
    source = source.upper()
    log_extra = {"source": source}

    if level not in _VALID_LEVELS:
        _logger.info(f"[Unknown Level Specified: {level}] {message}", extra=log_extra)
        return

    log_fn = getattr(_logger, level)
    log_fn(message, extra=log_extra)


# --- How you use it now ---

# 1. Calling it from main.py
# add_log("Application pipeline started.", "info", source="MAIN")

# 2. Calling it from a crew file
# add_log("Research crew failed to fetch API data.", "error", source="RESEARCH_CREW")

# 3. Calling it without specifying a source (defaults to UNKNOWN)
# add_log("Generic background task completed.", "info")