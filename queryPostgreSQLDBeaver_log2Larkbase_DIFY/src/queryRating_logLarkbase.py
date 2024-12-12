import pandas as pd
import requests
import os
from connect_PostgresSQLDBeaver import connect_to_database
from utils_saveQueryExcel import save_query_to_excel

def get_existing_records():
    """Get records from ratings_only.xlsx file"""
    try:
        excel_path = './query_results/ratings_only.xlsx'
        if not os.path.exists(excel_path):
            print(f"File not found: {excel_path}")
            return pd.DataFrame()
            
        existing_df = pd.read_excel(excel_path)
        print(f"Found {len(existing_df)} existing records in ratings_only.xlsx")
        return existing_df
    except Exception as e:
        print(f"Error reading ratings_only.xlsx: {e}")
        return pd.DataFrame()

def save_to_larkbase(new_records):
    """Save new records to Larkbase via API"""
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

def compare_and_find_changes(existing_df, new_df):
    """
    Compare existing and new data to find rating changes
    - Sau khi return ra results. 
    - So sánh results này so với file query_results/ratings_only
    - Nếu nó có thêm dòng nào, thì lưu dòng đó vào Larkbase bằng API 
    Dựa vào Query DBeaver -> python lưu data vào CSV không ổn - Excel oke (results thu được check với file Excel cũ, nếu có dòng mới sẽ lưu dòng mới đó vào Excel và Larkbase thông qua API). 
    - Đơn giản hóa code để chỉ kiểm tra thay đổi trong cột rating
    """
    if existing_df.empty:
        print("No existing data - all records are new")
        return new_df

    # Convert IDs to string for comparison
    existing_df['id'] = existing_df['id'].astype(str)
    new_df['id'] = new_df['id'].astype(str)
    
    # Find new records
    new_records = new_df[~new_df['id'].isin(existing_df['id'])]
    if not new_records.empty:
        print(f"\nFound {len(new_records)} new records")
    
    # Find updated ratings
    changed_records = []
    for _, new_record in new_df[new_df['id'].isin(existing_df['id'])].iterrows():
        old_record = existing_df[existing_df['id'] == new_record['id']].iloc[0]
        
        # Only compare rating field
        if str(old_record['rating']) != str(new_record['rating']):
            print(f"\nRating changed for record ID {new_record['id']}:")
            print(f"  Old rating: {old_record['rating']}")
            print(f"  New rating: {new_record['rating']}")
            changed_records.append(new_record)
    
    if changed_records:
        changed_df = pd.DataFrame(changed_records)
        return pd.concat([new_records, changed_df], ignore_index=True)
    
    return new_records if not new_records.empty else pd.DataFrame(columns=new_df.columns)

def query_ratings():
    """Main function to query and update ratings"""
    tunnel = connection = cursor = None
    try:
        # Get existing records
        existing_df = get_existing_records()

        # Connect to database
        tunnel, connection = connect_to_database()
        cursor = connection.cursor()
        
        # Query database
        query = """
        SELECT 
            id, workflow_run_id, app_id, title, node_type, inputs, outputs,
            execution_metadata::json -> 'tool_info' ->> 'provider_id' AS provider_id,
            execution_metadata::json -> 'user_inputs' ->> '#1733764453822.text#' AS user_inputs_text,
            execution_metadata::json -> 'rate' ->> 'rating' AS rating,
            execution_metadata::json -> 'rate' ->> 'updated_at' AS rate_updated_at,
            execution_metadata::json -> 'rate' ->> 'account_id' AS rate_account_id
        FROM public.workflow_node_execution_mindpal
        WHERE node_type = 'tool' AND execution_metadata::jsonb ? 'rate';
        """
        cursor.execute(query)
        
        # Convert results to DataFrame
        columns = ['id', 'workflow_run_id', 'app_id', 'title', 'node_type', 'inputs', 
                  'outputs', 'provider_id', 'user_inputs_text', 'rating', 
                  'rate_updated_at', 'rate_account_id']
        new_df = pd.DataFrame(cursor.fetchall(), columns=columns)
        print(f"\nFound {len(new_df)} total records in database")

        # Find changes
        changed_records_df = compare_and_find_changes(existing_df, new_df)

        if not changed_records_df.empty:
            # Save changes to Larkbase
            save_to_larkbase(changed_records_df.values.tolist())
            
            # Update Excel file
            excel_path = './query_results/ratings_only.xlsx'
            all_records = pd.concat([existing_df, changed_records_df], ignore_index=True)
            all_records.to_excel(excel_path, index=False)
            print(f"Updated Excel file with {len(changed_records_df)} new/modified records")
        else:
            print("No changes to save")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up connections
        if cursor: cursor.close()
        if connection: connection.close()
        if tunnel: tunnel.stop()
        print("Connections closed.")

if __name__ == "__main__":
    query_ratings()