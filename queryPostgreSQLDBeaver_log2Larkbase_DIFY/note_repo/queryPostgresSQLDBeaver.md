# Báo Cáo Kết Nối và Truy Vấn Cơ Sở Dữ Liệu PostgreSQL Qua SSH Tunnel

## 1. Giới Thiệu

Trong dự án này, mục tiêu là kết nối thành công tới cơ sở dữ liệu PostgreSQL thông qua SSH Tunnel, thực hiện các truy vấn để lấy thông tin về các bảng, đặc biệt là bảng `workflow_node_execution_mindpal`. Bên cạnh đó, chúng ta còn tập trung vào việc tối ưu hóa feedback từ các Node Tool bên trong workflow bằng cách truy xuất và xử lý dữ liệu liên quan.

## 2. Cài Đặt Môi Trường

Trước tiên, chúng ta cần cài đặt các thư viện cần thiết để thiết lập kết nối SSH và làm việc với PostgreSQL.

```bash
!pip install psycopg2-binary sshtunnel paramiko
```

## 3. Cấu Hình Kết Nối SSH và PostgreSQL

### 3.1. Cấu Hình SSH

```python
from sshtunnel import SSHTunnelForwarder
import psycopg2

# Configuration for SSH and PostgreSQL
SSH_CONFIG = {
    "ssh_host": "103.253.20.13",      # Địa chỉ SSH server
    "ssh_port": 22,                   # Cổng SSH
    "ssh_user": "ubuntu",             # SSH username
    "ssh_private_key": "C:/Users/User/.ssh/id_rsa"  # Đường dẫn khóa SSH cá nhân
}
```

### 3.2. Cấu Hình PostgreSQL

```python
DB_CONFIG = {
    "db_host": "localhost",           # PostgreSQL host (thường là localhost qua SSH tunnel)
    "db_port": 5434,                  # Cổng PostgreSQL
    "db_name": "postgres",            # Tên database
    "db_user": "postgres",            # Username PostgreSQL
    "db_password": "difyai123456"     # Mật khẩu PostgreSQL
}
```

## 4. Thiết Lập Kết Nối và Truy Vấn Dữ Liệu

### 4.1. Thiết Lập SSH Tunnel

```python
def establish_ssh_tunnel(ssh_config, db_config):
    """
    Thiết lập một SSH tunnel tới server từ xa.
    """
    try:
        tunnel = SSHTunnelForwarder(
            (ssh_config["ssh_host"], ssh_config["ssh_port"]),
            ssh_username=ssh_config["ssh_user"],
            ssh_private_key=ssh_config["ssh_private_key"],
            remote_bind_address=(db_config["db_host"], db_config["db_port"])
        )
        tunnel.start()
        print("SSH Tunnel đã được thiết lập thành công!")
        return tunnel
    except Exception as e:
        print(f"Lỗi khi thiết lập SSH Tunnel: {e}")
        raise
```

### 4.2. Kết Nối tới PostgreSQL

```python
def connect_to_postgresql(tunnel, db_config):
    """
    Kết nối tới cơ sở dữ liệu PostgreSQL thông qua SSH tunnel.
    """
    try:
        connection = psycopg2.connect(
            dbname=db_config["db_name"],
            user=db_config["db_user"],
            password=db_config["db_password"],
            host="127.0.0.1",  # Localhost vì đã qua SSH Tunnel
            port=tunnel.local_bind_port
        )
        print("Đã kết nối thành công tới cơ sở dữ liệu PostgreSQL!")
        return connection
    except Exception as e:
        print(f"Lỗi khi kết nối tới PostgreSQL: {e}")
        raise
```

### 4.3. Thực Thi Truy Vấn

```python
def execute_query(connection, query):
    """
    Thực thi một truy vấn trên cơ sở dữ liệu PostgreSQL và trả về kết quả.
    """
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        return results
    except Exception as e:
        print(f"Lỗi khi thực thi truy vấn: {e}")
        raise
```

### 4.4. Quy Trình Truy Vấn Qua SSH Tunnel

```python
def query_postgresql_with_ssh(query):
    """
    Thiết lập SSH tunnel, kết nối tới PostgreSQL và thực thi một truy vấn.
    """
    try:
        # Thiết lập SSH Tunnel
        tunnel = establish_ssh_tunnel(SSH_CONFIG, DB_CONFIG)

        # Kết nối tới PostgreSQL
        connection = connect_to_postgresql(tunnel, DB_CONFIG)

        # Thực thi truy vấn
        results = execute_query(connection, query)

        # Hiển thị kết quả truy vấn
        print(f"Kết quả truy vấn cho: {query}")
        for row in results:
            print(row)

        # Đóng kết nối PostgreSQL
        connection.close()
        print("Đã đóng kết nối PostgreSQL.")

        # Dừng SSH tunnel
        tunnel.stop()
        print("SSH Tunnel đã được dừng.")
    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
```

### 4.5. Ví Dụ Truy Vấn: Liệt Kê Tất Cả Các Bảng Trong Schema `public`

```python
if __name__ == "__main__":
    query_postgresql_with_ssh("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name;
    """)
```

## 5. Kiểm Tra và Truy Vấn Bảng `workflow_node_execution_mindpal`

### 5.1. Kiểm Tra Sự Tồn Tại của Bảng

```python
def check_table_existence_and_query():
    """
    Kiểm tra sự tồn tại của bảng và thực hiện truy vấn nếu bảng tồn tại.
    """
    try:
        # Thiết lập SSH Tunnel
        with SSHTunnelForwarder(
            (SSH_CONFIG["ssh_host"], SSH_CONFIG["ssh_port"]),
            ssh_username=SSH_CONFIG["ssh_user"],
            ssh_private_key=SSH_CONFIG["ssh_private_key"],
            remote_bind_address=(DB_CONFIG["db_host"], DB_CONFIG["db_port"])
        ) as tunnel:
            print("SSH Tunnel đã kết nối!")

            # Kết nối tới PostgreSQL thông qua SSH Tunnel
            connection = psycopg2.connect(
                dbname=DB_CONFIG["db_name"],
                user=DB_CONFIG["db_user"],
                password=DB_CONFIG["db_password"],
                host="127.0.0.1",
                port=tunnel.local_bind_port
            )
            print("Đã kết nối thành công tới PostgreSQL!")

            # Tạo cursor và thực thi truy vấn kiểm tra bảng
            cursor = connection.cursor()
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'workflow_node_execution_mindpal';
            """)
            table_exists = cursor.fetchone()

            if table_exists:
                print("Bảng 'workflow_node_execution_mindpal' tồn tại!")
                # Thực hiện truy vấn dữ liệu từ bảng
                cursor.execute("SELECT * FROM public.workflow_node_execution_mindpal LIMIT 10;")
                results = cursor.fetchall()
                print("Dữ liệu trong bảng:")
                for row in results:
                    print(row)
            else:
                print("Bảng 'workflow_node_execution_mindpal' không tồn tại.")

            # Đóng kết nối
            cursor.close()
            connection.close()
            print("Đã đóng kết nối PostgreSQL.")

    except Exception as e:
        print("Đã xảy ra lỗi:", e)

# Gọi hàm để kiểm tra và truy vấn
check_table_existence_and_query()
```

### 5.2. Kiểm Tra Các Cột Trong Bảng

```python
def check_table_columns_and_query():
    """
    Kiểm tra sự tồn tại của bảng và in danh sách các cột trong bảng.
    """
    try:
        # Thiết lập SSH Tunnel
        with SSHTunnelForwarder(
            (SSH_CONFIG["ssh_host"], SSH_CONFIG["ssh_port"]),
            ssh_username=SSH_CONFIG["ssh_user"],
            ssh_private_key=SSH_CONFIG["ssh_private_key"],
            remote_bind_address=(DB_CONFIG["db_host"], DB_CONFIG["db_port"])
        ) as tunnel:
            print("SSH Tunnel đã kết nối!")

            # Kết nối tới PostgreSQL
            connection = psycopg2.connect(
                dbname=DB_CONFIG["db_name"],
                user=DB_CONFIG["db_user"],
                password=DB_CONFIG["db_password"],
                host="127.0.0.1",
                port=tunnel.local_bind_port
            )
            print("Đã kết nối thành công tới PostgreSQL!")

            cursor = connection.cursor()

            # Kiểm tra sự tồn tại của bảng
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'workflow_node_execution_mindpal';
            """)
            table_exists = cursor.fetchone()

            if table_exists:
                print("Bảng 'workflow_node_execution_mindpal' tồn tại!")

                # Lấy danh sách các cột
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'workflow_node_execution_mindpal';
                """)
                columns = cursor.fetchall()
                print("Danh sách các cột trong bảng:")
                for column in columns:
                    print(f"Cột: {column[0]}, Loại dữ liệu: {column[1]}")

                # Truy vấn dữ liệu từ bảng
                cursor.execute("SELECT * FROM public.workflow_node_execution_mindpal LIMIT 10;")
                results = cursor.fetchall()
                print("Dữ liệu trong bảng:")
                for row in results:
                    print(row)
            else:
                print("Bảng 'workflow_node_execution_mindpal' không tồn tại.")

            # Đóng kết nối
            cursor.close()
            connection.close()
            print("Đã đóng kết nối PostgreSQL.")

    except Exception as e:
        print("Đã xảy ra lỗi:", e)

# Gọi hàm để kiểm tra và in cột
check_table_columns_and_query()
```

### 5.3. Truy Vấn Các Trường Cần Thiết Từ Bảng `workflow_node_execution_mindpal`

```python
def query_workflow_data():
    """
    Truy vấn các trường cần thiết từ bảng workflow_node_execution_mindpal.
    """
    try:
        # Thiết lập SSH Tunnel
        with SSHTunnelForwarder(
            (SSH_CONFIG["ssh_host"], SSH_CONFIG["ssh_port"]),
            ssh_username=SSH_CONFIG["ssh_user"],
            ssh_private_key=SSH_CONFIG["ssh_private_key"],
            remote_bind_address=(DB_CONFIG["db_host"], DB_CONFIG["db_port"])
        ) as tunnel:
            print("SSH Tunnel đã kết nối!")

            # Kết nối tới PostgreSQL
            connection = psycopg2.connect(
                dbname=DB_CONFIG["db_name"],
                user=DB_CONFIG["db_user"],
                password=DB_CONFIG["db_password"],
                host="127.0.0.1",
                port=tunnel.local_bind_port
            )
            print("Đã kết nối thành công tới PostgreSQL!")

            cursor = connection.cursor()

            # Truy vấn dữ liệu
            query = """
                SELECT 
                    workflow_run_id,
                    workflow_name,  -- Sửa lại tên cột thực tế nếu cần
                    config_link,    -- Sửa lại tên cột thực tế nếu cần
                    score,
                    bad_response,
                    input,
                    context,
                    prompt,
                    output,
                    conversation_link -- Sửa lại tên cột thực tế nếu cần
                FROM public.workflow_node_execution_mindpal
                LIMIT 10;
            """
            cursor.execute(query)
            results = cursor.fetchall()

            # Hiển thị kết quả
            print("Dữ liệu trong bảng theo yêu cầu:")
            for row in results:
                print(row)

            # Đóng kết nối PostgreSQL
            cursor.close()
            connection.close()
            print("Đã đóng kết nối PostgreSQL.")

    except Exception as e:
        print("Đã xảy ra lỗi:", e)

# Chạy hàm truy vấn
query_workflow_data()
```

### 5.4. Truy Vấn Dữ Liệu Cụ Thể Từ `execution_metadata`

Để lấy các thông tin cụ thể từ cột `execution_metadata`, chúng ta sử dụng cú pháp JSON của PostgreSQL để trích xuất các trường cần thiết.

#### SQL Truy Vấn

```sql
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

#### Giải Thích Truy Vấn

1. **Chọn Các Cột Cơ Bản:**
   - `id`: ID của bản ghi.
   - `workflow_run_id`: ID của lần chạy workflow.
   - `app_id`: ID của ứng dụng.
   - `title`: Tiêu đề của node.
   - `node_type`: Loại node (chỉ lấy `tool`).
   - `inputs` và `outputs`: Dữ liệu đầu vào và đầu ra của node.

2. **Trích Xuất Thông Tin Từ `execution_metadata`:**
   - `provider_id`: Lấy từ `execution_metadata -> tool_info -> provider_id`.
   - `user_inputs_text`: Lấy từ `execution_metadata -> user_inputs -> '#1733764453822.text#'`.
   - `rating`: Lấy từ `execution_metadata -> rate -> rating`.
   - `rate_updated_at`: Ngày cập nhật rating từ `execution_metadata -> rate -> updated_at`.
   - `rate_account_id`: ID người đánh giá từ `execution_metadata -> rate -> account_id`.

3. **Điều Kiện Lọc:**
   - `node_type = 'tool'`: Chỉ lấy các bản ghi có `node_type` là `tool`.
   - `execution_metadata::jsonb ? 'rate'`: Chỉ lấy các bản ghi mà `execution_metadata` chứa trường `rate`.

### 5.5. Truy Vấn Kết Hợp Với `workflow_run_id`

Để lấy toàn bộ các hàng có `workflow_run_id` tương ứng với các node `tool`, chúng ta sử dụng câu lệnh `WITH` (CTE - Common Table Expression).

#### SQL Truy Vấn

```sql
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

#### Giải Thích Truy Vấn

1. **CTE `tool_nodes`:**
   - Chọn các node có `node_type` là `tool` và chứa trường `rate` trong `execution_metadata`.
   - Trích xuất các thông tin cần thiết từ `execution_metadata`.

2. **Truy Vấn Chính:**
   - Lấy toàn bộ các hàng trong bảng `workflow_node_execution_mindpal` mà `workflow_run_id` nằm trong tập `workflow_run_id` của `tool_nodes`.

## 6. Mục Tiêu Tối Ưu Feedback Từ Các Node Tool

### 6.1. Mô Tả Vấn Đề

Mục tiêu là tối ưu hóa feedback từ các Node Tool bên trong workflow bằng cách:

1. Lấy các node có `node_type` = `tool`.
2. Trích xuất thông tin `provider_id`, `user_inputs_text`, và `rate` từ `execution_metadata`.
3. Lấy thêm các cột `inputs`, `outputs`, `title`, `node_type`.
4. Lấy các hàng có cùng `workflow_run_id` để có đầy đủ context.

### 6.2. Truy Vấn SQL Được Đề Xuất

```sql
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

### 6.3. Mở Rộng Truy Vấn Để Bao Gồm Các Node `llm`

Để lấy thêm các node có `node_type` = `llm` nằm giữa các node `tool` đã chọn, chúng ta cần mở rộng truy vấn như sau:

```sql
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
WHERE workflow_run_id IN (SELECT workflow_run_id FROM tool_nodes)
   OR (workflow_run_id IN (SELECT workflow_run_id FROM tool_nodes) AND node_type = 'llm')
ORDER BY created_at;
```

#### Giải Thích Truy Vấn

- **Điều Kiện Lọc Thêm:**
  - Bao gồm các hàng có `node_type` = `llm` và nằm trong cùng `workflow_run_id` với các node `tool`.
- **Sắp Xếp Kết Quả:**
  - Sắp xếp theo ngày tạo (`created_at`) để dễ dàng theo dõi quá trình thực thi.

## 7. Vấn Đề và Giải Pháp Đề Xuất

### 7.1. Vấn Đề Hiện Tại

- **Mối Quan Hệ Giữa Các Node:**
  - Các node `tool` và `llm` thuộc cùng một `workflow_run_id` nhưng có các `app_id` và `workflow_run_id` khác nhau, gây khó khăn trong việc truy vết liên kết giữa chúng.
  
- **Chạy Run MindPal:**
  - Các bản workflow draft liên tục được cập nhật, khiến việc truy vết kết nối giữa các node trở nên khó khăn.

### 7.2. Giải Pháp Đề Xuất

- **Cập Nhật `workflow_run_id`:**
  - Đảm bảo rằng tất cả các node liên quan trong cùng một workflow sử dụng chung một `workflow_run_id` để dễ dàng truy vết và liên kết.
  
- **Tối Ưu Hóa Truy Vấn:**
  - Sử dụng các truy vấn SQL phức tạp hơn để đảm bảo rằng tất cả các node liên quan đều được bao gồm trong kết quả truy vấn.

- **Thêm Thông Tin Mối Quan Hệ:**
  - Cân nhắc thêm các cột hoặc bảng phụ trợ để lưu trữ mối quan hệ giữa các node, giúp việc truy vết trở nên dễ dàng hơn.

## 8. Kết Luận

Qua quá trình kết nối và truy vấn cơ sở dữ liệu PostgreSQL thông qua SSH Tunnel, chúng ta đã thực hiện thành công việc kiểm tra, truy vấn và trích xuất dữ liệu từ bảng `workflow_node_execution_mindpal`. Đồng thời, chúng ta cũng đã đề xuất các giải pháp để tối ưu hóa việc truy vết và tối ưu hóa feedback từ các Node Tool trong workflow.

Việc đảm bảo rằng các node trong cùng một workflow sử dụng chung `workflow_run_id` sẽ giúp đơn giản hóa quá trình truy vết và phân tích dữ liệu, từ đó nâng cao hiệu quả làm việc và quản lý hệ thống.

# Kết Thúc

Nếu có bất kỳ câu hỏi hoặc yêu cầu hỗ trợ thêm, vui lòng liên hệ để được hỗ trợ kịp thời.

# Appendix

## 1. Hình Ảnh Minh Họa

*(Các hình ảnh đã được đề cập trong nội dung sẽ được đính kèm ở đây nếu có.)*

## 2. Mẫu Dữ Liệu

```plaintext
9e14ecfc-5eed-441f-879a-feda13d0f168	51d7f795-a145-483b-bcdf-7ef374d7e9dd	da0ecc2b-a5ca-42c4-81e8-d86974279f35	5b74bd6a-f801-49b4-8779-a32298cf3157	single-step	4d889e24-d901-49d3-a187-9f8f62766120	2fbaa53f-c349-4ea6-bee0-16c79176f644	1		1733764453822	tool	1.0 - PS/Input Problem	{"problem_statement": "New new "}		{"text": "{\"text\": \"D\u01b0\u1ed8i \u0111\u00e2y l\u00e0 m\u1ed9t s\u1ed1 nguy\u00ean nh\u00e2n g\u00e2y ra v\u1ea5n \u0111\u1ec1 newnew theo framework MECE:\n\n1. **Con ng\u01b0\u1eddi:**\n   - Thi\u1ebfu k\u1ef9 n\u0103ng ho\u1eb7c tr\u00ecnh \u0111\u1ed9 chuy\u00ean m\u00f4n c\u1ea7n thi\u1ebft.\n   - 2y nh\u00e9!"}]}	succeeded		4.453751286491752	{"tool_info": {"provider_type": "workflow", "provider_id": "3f7bf0a0-2cd3-4597-a57f-b11443194efb"}, "user_inputs": {"#1732873471087.problem_statement#": "New new "}, "rate": {"rating": 7, "updated_at": "2024-12-11 08:27:00", "account_id": "da8ab5b2-b5d0-460d-823b-856592af46ac"}}	2024-12-11 08:08:51.238	account	da8ab5b2-b5d0-460d-823b-856592af46ac	2024-12-11 08:08:51.238	
```

*(Dữ liệu mẫu trên thể hiện cách các trường trong bảng được lưu trữ và các giá trị cụ thể.)*

## 3. Tham Khảo

- [sshtunnel Documentation](https://sshtunnel.readthedocs.io/en/latest/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [PostgreSQL JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)

# End of Report