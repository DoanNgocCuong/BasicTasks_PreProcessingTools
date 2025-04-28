import pandas as pd
from datetime import datetime
import os

def save_query_to_excel(results, cursor, query_type='default', folder_name='query_results'):
    """
    Save query results to an Excel file in specified folder.
    
    Args:
        results: Query results from cursor.fetchall()
        cursor: Database cursor object containing query metadata
        query_type: Type of query to prefix filename (default: 'default')
        folder_name: Name of folder to save Excel files (default: 'query_results')
    
    Returns:
        str: Path to saved Excel file
    """
    try:
        # Create folder if it doesn't exist
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            
        # Get column names from cursor description
        columns = [desc[0] for desc in cursor.description]
        
        # Create DataFrame
        df = pd.DataFrame(results, columns=columns)
        
        # Generate filename with query type
        excel_path = os.path.join(folder_name, f'{query_type}.xlsx')
        
        # Save to Excel
        df.to_excel(excel_path, index=False)
        print(f"Results saved to {excel_path}")
        
        return excel_path
        
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        return None

def save_multiple_queries_to_excel(query_results_dict, folder_name='query_results'):
    """
    Save multiple query results to separate sheets in one Excel file.
    
    Args:
        query_results_dict: Dictionary with format {
            'sheet_name': {
                'results': cursor.fetchall() results,
                'cursor': database cursor object
            }
        }
        folder_name: Name of folder to save Excel files (default: 'query_results')
    
    Returns:
        str: Path to saved Excel file
    """
    try:
        # Create folder if it doesn't exist
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            
        # Generate filename
        excel_path = os.path.join(folder_name, 'multiple_queries.xlsx')
        
        # Create Excel writer object
        with pd.ExcelWriter(excel_path) as writer:
            # Process each query result
            for sheet_name, data in query_results_dict.items():
                # Get column names from cursor description
                columns = [desc[0] for desc in data['cursor'].description]
                
                # Create DataFrame
                df = pd.DataFrame(data['results'], columns=columns)
                
                # Write to Excel sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"Results saved to {excel_path}")
        return excel_path
        
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        return None
