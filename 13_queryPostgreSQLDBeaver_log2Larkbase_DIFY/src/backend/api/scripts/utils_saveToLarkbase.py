import requests

def save_ratings_to_larkbase(new_records):
    """Save rating records to Larkbase via API"""
    url = 'http://103.253.20.13:25033/api/larkbase/create-many-records'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic KyVZLSVtLSVkVCVIOiVN'
    }
    
    payload = {
        "config": {
            "app_id": "cli_a7852e8dc6fc5010",
            "app_secret": "6SIj0RfQ0ZwROvUhkjAwLebhLfJkIwnT", 
            "app_base_token": "BtGmbls2CaqfHnsuwxelJNlpgvb",
            "base_table_id": "tblvifRIX8c9xGpp"
        },
        "records": [
            {
                "fields": {
                    "id": str(record[0]),
                    "workflow_run_id": str(record[1]),
                    "app_id": str(record[2]), 
                    "title": str(record[3]),
                    "node_type": str(record[4]),
                    "inputs": str(record[5]),
                    "outputs": str(record[6]),
                    "provider_id": str(record[7]),
                    "user_inputs_text": str(record[8]),
                    "rating": str(record[9]),
                    "rate_updated_at": str(record[10]),
                    "rate_account_id": str(record[11])
                }
            } for record in new_records
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Successfully saved {len(new_records)} new records to Larkbase")
        else:
            print(f"Error saving to Larkbase: {response.text}")
    except Exception as e:
        print(f"Error making API request: {e}")

def save_workflow_tools_to_larkbase(new_records):
    """Save workflow tool records to Larkbase via API"""
    url = 'http://103.253.20.13:25033/api/larkbase/create-many-records'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic KyVZLSVtLSVkVCVIOiVN'
    }
    
    payload = {
        "config": {
            "app_id": "cli_a7852e8dc6fc5010",
            "app_secret": "6SIj0RfQ0ZwROvUhkjAwLebhLfJkIwnT", 
            "app_base_token": "BtGmbls2CaqfHnsuwxelJNlpgvb",
            "base_table_id": "tblcmmgOlAYW4dXS"
        },
        "records": [
            {
                "fields": {
                    "id": str(record[0]),
                    "tenant_id": str(record[1]),
                    "app_id": str(record[2]),
                    "workflow_id": str(record[3]),
                    "triggered_from": str(record[4]),
                    "workflow_run_id": str(record[5]),
                    "workflow_node_execution_id": str(record[6]),
                    "index": str(record[7]),
                    "predecessor_node_id": str(record[8]),
                    "node_id": str(record[9]),
                    "node_type": str(record[10]),
                    "title": str(record[11]),
                    "inputs": str(record[12]),
                    "process_data": str(record[13]),
                    "outputs": str(record[14]),
                    "status": str(record[15]),
                    "error": str(record[16]),
                    "elapsed_time": str(record[17]),
                    "execution_metadata": str(record[18]),
                    "created_at": str(record[19]),
                    "created_by_role": str(record[20]),
                    "created_by": str(record[21]),
                    "finished_at": str(record[22]),
                    "node_execution_id": str(record[23])
                }
            } for record in new_records
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Successfully saved {len(new_records)} new records to Larkbase")
        else:
            print(f"Error saving to Larkbase: {response.text}")
    except Exception as e:
        print(f"Error making API request: {e}")