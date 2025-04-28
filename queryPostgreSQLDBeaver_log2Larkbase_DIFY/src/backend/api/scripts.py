from flask import Blueprint, jsonify
import subprocess
import os
from pathlib import Path
import logging
import sys

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bp = Blueprint('scripts', __name__)

SCRIPTS_FOLDER = Path(__file__).parent / 'scripts'

@bp.route('/run/<script_name>', methods=['POST'])
def run_script(script_name):
    script_path = SCRIPTS_FOLDER / f'{script_name}.py'
    
    # Log initial information
    logger.info(f"Attempting to run script: {script_name}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Script path: {script_path}")
    logger.info(f"Python executable: {sys.executable}")
    
    if not script_path.exists():
        logger.error(f'Script not found: {script_name}')
        return jsonify({'error': f'Script {script_name} not found'}), 404
        
    try:
        # Set up environment variables
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent.parent)  # Add backend folder to Python path
        logger.info(f"PYTHONPATH set to: {env['PYTHONPATH']}")
        
        # Log script execution attempt
        logger.info(f'Running script with Python: {sys.executable}')
        logger.info(f'Working directory: {SCRIPTS_FOLDER}')
        
        # Run the script with detailed output capture
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(SCRIPTS_FOLDER)
        )
        
        # Log the execution results
        logger.info(f'Script return code: {result.returncode}')
        logger.info(f'Script stdout: {result.stdout}')
        if result.stderr:
            logger.error(f'Script stderr: {result.stderr}')
        
        if result.returncode == 0:
            logger.info(f'Script {script_name} completed successfully')
            return jsonify({
                'success': True,
                'message': f'Script {script_name} executed successfully',
                'output': result.stdout
            })
        else:
            logger.error(f'Script {script_name} failed with return code {result.returncode}')
            return jsonify({
                'success': False,
                'error': result.stderr,
                'stdout': result.stdout
            }), 500
            
    except Exception as e:
        logger.error(f'Error running script {script_name}: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 
