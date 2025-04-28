from connect_PostgresSQLDBeaver import connect_to_database
from utils_saveQueryExcel import save_query_to_excel

def query_ratings():
    """
    Query rating data for tool nodes from workflow_node_execution_mindpal table.
    """
    try:
        # Connect to database
        tunnel, connection = connect_to_database()

        # Create cursor and execute query
        cursor = connection.cursor()
        query = """
        SELECT 
            id,
            workflow_run_id,
            app_id,
            title,
            node_type,
            inputs,
            outputs,
            execution_metadata::json -> 'tool_info' ->> 'provider_id' AS provider_id,
            execution_metadata::json -> 'user_inputs' ->> '#1733764453822.text#' AS user_inputs_text,
            execution_metadata::json -> 'rate' ->> 'rating' AS rating,
            execution_metadata::json -> 'rate' ->> 'updated_at' AS rate_updated_at,
            execution_metadata::json -> 'rate' ->> 'account_id' AS rate_account_id
        FROM 
            public.workflow_node_execution_mindpal
        WHERE 
            node_type = 'tool' 
            AND execution_metadata::jsonb ? 'rate';
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Save results to Excel with query type
        excel_path = save_query_to_excel(
            results, 
            cursor,
            query_type='ratings_only'  # This will create files like: ratings_only_20240311_143022.xlsx
        )

        # Close connection
        cursor.close()
        connection.close()
        tunnel.stop()
        print("PostgreSQL and SSH Tunnel connection closed.")

    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    query_ratings()
