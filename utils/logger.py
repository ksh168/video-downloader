import logging
from logging.handlers import RotatingFileHandler
import os


# Configure logging
def setup_logging(app):
    """Set up logging for the application."""
    # Ensure logs directory exists
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Configure file handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=10240, backupCount=10
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
