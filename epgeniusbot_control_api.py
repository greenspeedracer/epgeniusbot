from flask import Flask, jsonify, request
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

BOT_CONTROL_API_TOKEN = os.getenv("BOT_CONTROL_API_TOKEN")

if not BOT_CONTROL_API_TOKEN:
    raise ValueError("BOT_CONTROL_API_TOKEN not set in .env file")

def check_auth():
    token = request.headers.get('Authorization')
    if not token or token != f'Bearer {BOT_CONTROL_API_TOKEN}':
        return False
    return True

def run_script(script_name):
    try:
        result = subprocess.run(
            [f'/home/ubuntu/epgeniusbot/{script_name}'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout.strip() 
        success = result.returncode == 0
        
        response = {
            'success': success,
            'message': output if output else None
        }
        
        if result.stderr and result.stderr.strip():
            response['error'] = result.stderr.strip()
            
        return response
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Script timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/status', methods=['GET'])
def status():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    result = run_script('epgeniusbot_status.sh')
    return jsonify(result)

@app.route('/start', methods=['POST'])
def start():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    result = run_script('epgeniusbot_start.sh')
    return jsonify(result)

@app.route('/stop', methods=['POST'])
def stop():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    result = run_script('epgeniusbot_stop.sh')
    return jsonify(result)

@app.route('/restart', methods=['POST'])
def restart():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    result = run_script('epgeniusbot_restart.sh')
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
