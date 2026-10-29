import logging
from datetime import datetime
from .paths import LOG_DIR


def get_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def setup_logging(run_id: str) -> logging.Logger:
    log_file = LOG_DIR / f"run_{run_id}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    log = logging.getLogger("cortex")
    log.info(f"=== RUN START {run_id} ===")
    log.info(f"Log: {log_file}")
    return log