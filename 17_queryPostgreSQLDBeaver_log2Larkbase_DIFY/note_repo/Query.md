Query Rating
```SQL
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
```

query_rating_toolsWorkflowMindpal.py

```SQL
WITH tool_nodes AS (
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
        AND execution_metadata::jsonb ? 'rate'
)
SELECT *
FROM public.workflow_node_execution_mindpal
WHERE workflow_run_id IN (SELECT workflow_run_id FROM tool_nodes);

```