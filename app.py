from dotenv import load_dotenv
from utils.logger import setup_logging

load_dotenv()

import os

from flask import Flask, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

from utils.s3.cleanup_s3 import init_cleanup_scheduler


app = Flask(__name__, template_folder=os.path.join(os.getcwd(), "templates"))

# Fix for running behind a proxy (like Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Set up logging
setup_logging(app)

# Initialize the cleanup scheduler
if os.environ.get("ENABLE_S3_CLEANUP", "False").lower() == "true":
    init_cleanup_scheduler()

if os.environ.get("ENABLE_QUEUE_CONSUMER", "False").lower() == "true":
    from utils.queue.queue_consumer import consume_messages
    consume_messages()  # This will now run in a separate thread


# Add this route before the download API route
@app.route("/", methods=["GET"])
def index():
    """
    Render the main download page
    """
    return render_template("index.html")

@app.errorhandler(500)
def internal_error_handler(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    return jsonify(error="Internal server error"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3001, debug=False)
