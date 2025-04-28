1. Có cách nào để import nguyên 1 file excel lên Larkbase không??? 

2. Không thì xài cách cơ bản: 

```bash
curl --location 'http://103.253.20.13:25033/api/larkbase/create-many-records' \
--header 'Content-Type: application/json' \
--header 'Authorization: Basic KyVZLSVtLSVkVCVIOiVN' \
--data '{
    "config": {
        "app_id": "cli_a7852e8dc6fc5010",
        "app_secret": "6SIj0RfQ0ZwROvUhkjAwLebhLfJkIwnT",
        "app_base_token": "BtGmbls2CaqfHnsuwxelJNlpgvb",
        "base_table_id": "tblvifRIX8c9xGpp"
    },
    "records": [
        {
            "fields": {
                "Id": "lesson123",
                "Workflow name": "This is a test feedback"
            }
        }
    ]
}'
```


### log_rating_toLarkbase

- Sau khi return ra results. 
- So sánh results này so với file query_results/ratings_only
- Nếu nó có thêm dòng nào, thì lưu dòng đó vào Larkbase bằng API 
Dựa vào Query DBeaver -> python lưu data vào CSV không ổn - Excel oke (results thu được check với file Excel cũ, nếu có dòng mới sẽ lưu dòng mới đó vào Excel và Larkbase thông qua API). 
- Đơn giản hóa code để chỉ kiểm tra thay đổi trong cột rating

```
curl --location 'http://103.253.20.13:25033/api/larkbase/create-many-records' \
--header 'Content-Type: application/json' \
--header 'Authorization: Basic KyVZLSVtLSVkVCVIOiVN' \
--data '{
    "config": {
        "app_id": "cli_a7852e8dc6fc5010",
        "app_secret": "6SIj0RfQ0ZwROvUhkjAwLebhLfJkIwnT",
        "app_base_token": "BtGmbls2CaqfHnsuwxelJNlpgvb",
        "base_table_id": "tblvifRIX8c9xGpp"
    },
    "records": [
        {
            "fields": {
                "id": "id_value",
                "workflow_run_id": "workflow_run_id_value", 
                "app_id": "app_id_value",
                "title": "title_value",
                "node_type": "node_type_value",
                "inputs": "inputs_value",
                "outputs": "outputs_value",
                "provider_id": "provider_id_value",
                "user_inputs_text": "user_inputs_text_value",
                "rating": "rating_value",
                "rate_updated_at": "rate_updated_at_value",
                "rate_account_id": "rate_account_id_value"
            }
        }
    ]
}'
```


### log RatingTooksWorkflowMindpal

Tương tự hãy sửa file @queryRatingToolsWorkflowMindpal_logLarkbase.py 
1. Chỉ check data thay đổi trong cột: execution_metadata
2. Sử dụng 1 API hơi khác 1 tí để log vào Larkbase
```bash
curl --location 'http://103.253.20.13:25033/api/larkbase/create-many-records' \
--header 'Content-Type: application/json' \
--header 'Authorization: Basic KyVZLSVtLSVkVCVIOiVN' \
--data '{
    "config": {
        "app_id": "cli_a7852e8dc6fc5010",
        "app_secret": "6SIj0RfQ0ZwROvUhkjAwLebhLfJkIwnT",
        "app_base_token": "BtGmbls2CaqfHnsuwxelJNlpgvb",
        "base_table_id": "tblcmmgOlAYW4dXS"
    },
    "records": [
        {
            "fields": {
                "id": "id_value",
                "tenant_id": "tenant_id_value",
                "app_id": "app_id_value", 
                "workflow_id": "workflow_id_value",
                "triggered_from": "triggered_from_value",
                "workflow_run_id": "workflow_run_id_value",
                "workflow_node_execution_id": "workflow_node_execution_id_value",
                "index": "index_value",
                "predecessor_node_id": "predecessor_node_id_value",
                "node_id": "node_id_value",
                "node_type": "node_type_value",
                "title": "title_value",
                "inputs": "inputs_value",
                "process_data": "process_data_value",
                "outputs": "outputs_value", 
                "status": "status_value",
                "error": "error_value",
                "elapsed_time": "elapsed_time_value",
                "execution_metadata": "execution_metadata_value",
                "created_at": "created_at_value",
                "created_by_role": "created_by_role_value",
                "created_by": "created_by_value",
                "finished_at": "finished_at_value",
                "node_execution_id": "node_execution_id_value"
            }
        }
    ]
}'
```
