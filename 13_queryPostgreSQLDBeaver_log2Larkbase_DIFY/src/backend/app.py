from flask import Flask
from flask_cors import CORS
from api.scripts import bp as scripts_bp
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging
import os
import atexit

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment configs
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 5000))
FLASK_ENV = os.getenv('FLASK_ENV', 'production')
FLASK_DEBUG = FLASK_ENV == 'development'
SCHEDULER_ENABLED = os.getenv('SCHEDULER_ENABLED', 'true').lower() == 'true'

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(scripts_bp, url_prefix='/api/scripts')

# Set up scheduler
scheduler = BackgroundScheduler()

def trigger_daily_queries():
    """Trigger both queries via API endpoints"""
    try:
        # Sử dụng service name thay vì localhost
        base_url = f'http://{API_HOST}:{API_PORT}'
        
        # Call rating query
        requests.post(f'{base_url}/api/scripts/run/queryRating_logLarkbase')
        logger.info("Rating query triggered")
        
        # Call workflow query
        requests.post(f'{base_url}/api/scripts/run/queryRatingToolsWorkflowMindpal_logLarkbase')
        logger.info("Workflow query triggered")
        
    except Exception as e:
        logger.error(f"Error triggering queries: {str(e)}")

def init_scheduler():
    """Initialize scheduler if enabled"""
    if SCHEDULER_ENABLED:
        try:
            # Schedule queries to run at midnight
            scheduler.add_job(trigger_daily_queries, 'cron', hour=0, minute=0)
            scheduler.start()
            logger.info("Scheduler started successfully")
            
            # Shut down scheduler when app exits
            atexit.register(lambda: scheduler.shutdown())
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    scheduler_status = "running" if scheduler.running else "stopped"
    return {
        "status": "healthy",
        "environment": FLASK_ENV,
        "scheduler": scheduler_status
    }

if __name__ == '__main__':
    # Initialize scheduler
    init_scheduler()
    
    # Run app
    app.run(
        host=API_HOST,
        port=API_PORT,
        debug=FLASK_DEBUG,
        use_reloader=FLASK_DEBUG
    )