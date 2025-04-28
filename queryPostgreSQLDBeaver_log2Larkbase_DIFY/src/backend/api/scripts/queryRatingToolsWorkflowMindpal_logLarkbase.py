from pathlib import Path
import pandas as pd
import os
from utils_saveToLarkbase import save_workflow_tools_to_larkbase
from utils_query import execute_query_with_connection, query_workflow_tools_data

# Define the base paths
SCRIPTS_FOLDER = Path(__file__).parent
QUERY_RESULTS_FOLDER = SCRIPTS_FOLDER / 'query_results'
WORKFLOW_TOOLS_FILE = QUERY_RESULTS_FOLDER / 'workflow_tools.xlsx'

def get_existing_records():
    """Get records from workflow_tools.xlsx file"""
    try:
        if not WORKFLOW_TOOLS_FILE.exists():
            print(f"File not found: {WORKFLOW_TOOLS_FILE}")
            return pd.DataFrame()
            
        existing_df = pd.read_excel(WORKFLOW_TOOLS_FILE)
        print(f"Found {len(existing_df)} existing records in workflow_tools.xlsx")
        return existing_df
    except Exception as e:
        print(f"Error reading workflow_tools.xlsx: {e}")
        return pd.DataFrame()

def compare_and_find_changes(existing_df, new_df):
    """
    Compare existing and new data to find rating changes in execution_metadata. 
    Nếu có sự thay đổi về rating trong execution_metadata
    (thay vì compare toàn bộ data trong cột excution_metadata)
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
    
    # Find updated ratings in execution_metadata
    changed_records = []
    for _, new_record in new_df[new_df['id'].isin(existing_df['id'])].iterrows():
        old_record = existing_df[existing_df['id'] == new_record['id']].iloc[0]
        
        try:
            # Parse execution_metadata JSON
            import json
            old_metadata = json.loads(str(old_record['execution_metadata']))
            new_metadata = json.loads(str(new_record['execution_metadata']))
            
            # Extract ratings
            old_rating = old_metadata.get('rate', {}).get('rating')
            new_rating = new_metadata.get('rate', {}).get('rating')
            
            # Compare ratings
            if str(old_rating) != str(new_rating):
                print(f"\nRating changed in execution_metadata for record ID {new_record['id']}:")
                print(f"  Old rating: {old_rating}")
                print(f"  New rating: {new_rating}")
                changed_records.append(new_record)
                
        except json.JSONDecodeError as e:
            print(f"Error parsing execution_metadata for record {new_record['id']}: {e}")
            continue
        except Exception as e:
            print(f"Error processing record {new_record['id']}: {e}")
            continue
    
    if changed_records:
        changed_df = pd.DataFrame(changed_records)
        return pd.concat([new_records, changed_df], ignore_index=True)
    
    return new_records if not new_records.empty else pd.DataFrame(columns=new_df.columns)

def query_tools_in_workflow():
    """Query and update workflow tools data"""
    try:
        # Get existing records
        existing_df = get_existing_records()

        # Get new data from database
        new_df = execute_query_with_connection(query_workflow_tools_data)
        if new_df.empty:
            return

        # Find changes
        changed_records_df = compare_and_find_changes(existing_df, new_df)

        if not changed_records_df.empty:
            # Save changes to Larkbase
            save_workflow_tools_to_larkbase(changed_records_df.values.tolist())
            
            # Create query_results directory if it doesn't exist
            QUERY_RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)
            
            # Update Excel file
            all_records = pd.concat([existing_df, changed_records_df], ignore_index=True)
            all_records.to_excel(WORKFLOW_TOOLS_FILE, index=False)
            print(f"Updated Excel file with {len(changed_records_df)} new/modified records")
        else:
            print("No changes to save")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    query_tools_in_workflow() 