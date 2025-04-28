from flask import Flask, jsonify, request
from config import APP_DOANNGOCCUONG_ID, APP_DOANNGOCCUONG_SECRET, APP_BASE_TOKEN, BASE_TABLE_ID
from larkbaseOperationsClassNoASYNC import LarkBaseOperations

app = Flask(__name__)

@app.route('/api/larkbase/create-many-records', methods=['POST'])
def process_data():
    try:
        data = request.get_json()
        config_data = data.get('config', {})
        
        # Map different possible key names to standard names
        config_mapping = {
            'APP_DOANNGOCCUONG_ID': ['app_id', 'app_doannngoccuong_id', 'appid', 'APP_DOANNGOCCUONG_ID'],
            'APP_DOANNGOCCUONG_SECRET': ['app_secret', 'app_doannngoccuong_secret', 'appsecret', 'APP_DOANNGOCCUONG_SECRET'],
            'APP_BASE_TOKEN': ['app_base_token', 'token', 'APP_BASE_TOKEN'],
            'BASE_TABLE_ID': ['base_table_id', 'table_id', 'BASE_TABLE_ID']
        }
        
        # Create standardized config dictionary
        standardized_config = {}
        for standard_key, possible_keys in config_mapping.items():
            value = None
            for key in possible_keys:
                if key in config_data:
                    value = config_data[key]
                    break
            if value is None:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required config field. Please provide one of: {possible_keys}"
                }), 400
            standardized_config[standard_key] = value
        
        # Initialize LarkBaseOperations with standardized config
        lark_ops = LarkBaseOperations()
        lark_ops.app_id = standardized_config['APP_DOANNGOCCUONG_ID']
        lark_ops.app_secret = standardized_config['APP_DOANNGOCCUONG_SECRET']
        lark_ops.app_base_token = standardized_config['APP_BASE_TOKEN']
        lark_ops.base_table_id = standardized_config['BASE_TABLE_ID']
        
        # Extract records data from the request
        records_data = data.get('records')
        if not records_data:
            return jsonify({
                "status": "error",
                "message": "Missing 'records' field in request data"
            }), 400
            
        records_payload = {"records": records_data}
        response = lark_ops.create_many_records_with_checkTenantAccessToken(records_payload)
        
        if response:
            return jsonify({
                "status": "success",
                "message": "Records processed successfully",
                "data": response.json()
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to process records"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run()