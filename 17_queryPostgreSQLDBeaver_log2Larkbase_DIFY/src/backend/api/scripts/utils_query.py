import pandas as pd
from connect_PostgresSQLDBeaver import connect_to_database

def query_ratings_data(cursor):
    """Query rating data from database"""
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
    
    columns = ['id', 'workflow_run_id', 'app_id', 'title', 'node_type', 'inputs', 
              'outputs', 'provider_id', 'user_inputs_text', 'rating', 
              'rate_updated_at', 'rate_account_id']
    return pd.DataFrame(cursor.fetchall(), columns=columns)

def query_workflow_tools_data(cursor):
    """Query workflow tools data from database"""
    query = """
    WITH tool_nodes AS (
        SELECT *
        FROM public.workflow_node_execution_mindpal
        WHERE node_type = 'tool' 
        AND execution_metadata::jsonb ? 'rate'
    )
    SELECT *
    FROM public.workflow_node_execution_mindpal
    WHERE workflow_run_id IN (SELECT workflow_run_id FROM tool_nodes);
    """
    cursor.execute(query)
    
    columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=columns)

def execute_query_with_connection(query_func):
    """Execute query with database connection handling"""
    tunnel = connection = cursor = None
    try:
        # Connect to database
        tunnel, connection = connect_to_database()
        cursor = connection.cursor()
        
        # Execute query
        df = query_func(cursor)
        print(f"\nFound {len(df)} total records in database")
        return df

    except Exception as e:
        print(f"An error occurred during query: {e}")
        return pd.DataFrame()

    finally:
        # Clean up connections
        if cursor: cursor.close()
        if connection: connection.close()
        if tunnel: tunnel.stop()
        print("Connections closed.")
