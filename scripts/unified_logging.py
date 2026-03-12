# This file is deprecated - use DataNinja.core.utils.setup_logging instead
try:
    from DataNinja.core.utils import setup_logging
except ImportError:
    # Fallback implementation
    import logging
    def setup_logging(level=logging.INFO, log_file=None, module_name=None):
        """Simple logging setup fallback."""
        logger = logging.getLogger(module_name or __name__)
        if logger.hasHandlers():
            return logger
        logger.setLevel(level)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        return logger

__all__ = ['setup_logging'] 