`python -m venv .venv`

Cách 2. Build mất tầm hơn 10 min. 
```bash
cd src/backend
docker build -f Dockerfile.requirements -t query-api-requirements .              
docker run -p 5000:5000 query-api-requirements
```
(Có cách để volumn và để .env ở ngoài docker build ...)

============
Đây là các lệnh curl để test API:

1. Health check:
````bash
curl http://localhost:5000/health
````

2. Chạy script rating:
````bash
curl -X POST http://localhost:5000/api/scripts/run/queryRating_logLarkbase
````

3. Chạy script workflow:
````bash
curl -X POST http://localhost:5000/api/scripts/run/queryRatingToolsWorkflowMindpal_logLarkbase
````

4. Để xem output chi tiết hơn (Windows PowerShell):
````powershell
# Health check
curl -v http://localhost:5000/health | ConvertFrom-Json | Format-List

# Run rating script
curl -v -X POST http://localhost:5000/api/scripts/run/queryRating_logLarkbase | ConvertFrom-Json | Format-List

# Run workflow script
curl -v -X POST http://localhost:5000/api/scripts/run/queryRatingToolsWorkflowMindpal_logLarkbase | ConvertFrom-Json | Format-List
````

5. Nếu dùng Windows CMD:
````batch
:: Health check
curl -v http://localhost:5000/health

:: Run rating script
curl -v -X POST http://localhost:5000/api/scripts/run/queryRating_logLarkbase

:: Run workflow script
curl -v -X POST http://localhost:5000/api/scripts/run/queryRatingToolsWorkflowMindpal_logLarkbase
````

Flag `-v` sẽ hiển thị thông tin chi tiết về request/response, giúp debug nếu có lỗi. Response sẽ có dạng:
```json
{
    "success": true,
    "message": "Script executed successfully",
    "output": "Found 100 total records in database..."
}
```

hoặc nếu có lỗi:
```json
{
    "success": false,
    "error": "Error message here",
    "stdout": "Any output before error..."
}
```

====

### 1. Bug đường dẫn với id_rsa mãi --- sau phải copy nó vào trong backend ??? 

Để sao chép tệp `id_rsa` từ ổ C vào thư mục `src` trong dự án của bạn, bạn có thể làm theo các bước sau:

1. **Sao chép tệp**:
   - Mở File Explorer và điều hướng đến `C:/Users/User/.ssh/`.
   - Tìm tệp `id_rsa`, sau đó sao chép nó.
   - Dán tệp vào thư mục `src` trong dự án của bạn.

2. **Cập nhật Dockerfile**:
   - Sau khi đã sao chép tệp vào thư mục `src`, bạn cần cập nhật `Dockerfile` để sử dụng đường dẫn tương đối. Dưới đây là cách cập nhật:

```dockerfile:src/backend/Dockerfile
# Copy SSH key
COPY ./src/id_rsa /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa
```

**Giải thích:**
- Đoạn mã trên sẽ sao chép tệp `id_rsa` từ thư mục `src` vào thư mục `/root/.ssh/` trong container Docker và thiết lập quyền truy cập cho tệp đó.

Sau khi thực hiện các thay đổi này, hãy thử xây dựng lại Docker image và kiểm tra xem mọi thứ có hoạt động như mong đợi không.


---

### 2. Bug Run docker hơn 10 min (lỗi thư viện requirements.txt các thứ??? - run docker với poetry thì bug chưa fix)

```bash
PS D:\OneDrive - Hanoi University of Science and Technology\GIT\1. Demo\BasicTasks_PreProcessingTools\queryPostgreSQLDBeaver_log2Larkbase_DIFY\src\backend> docker build -f Dockerfile.requirements -t query-api-requirements .
[+] Building 869.8s (13/13) FINISHED                        docker:desktop-linux
 => [internal] load build definition from Dockerfile.requirements           0.0s
 => => transferring dockerfile: 566B                                        0.0s 
 => [internal] load metadata for docker.io/library/python:3.9-slim          1.3s 
 => [internal] load .dockerignore                                           0.0s
 => => transferring context: 2B                                             0.0s 
 => [1/8] FROM docker.io/library/python:3.9-slim@sha256:4ee0613170ac55ebc6  0.0s 
 => [internal] load build context                                           0.0s 
 => => transferring context: 2.74kB                                         0.0s 
 => CACHED [2/8] WORKDIR /app                                               0.0s 
 => CACHED [3/8] COPY ./id_rsa /root/.ssh/id_rsa                            0.0s 
 => CACHED [4/8] RUN chmod 600 /root/.ssh/id_rsa                            0.0s 
 => CACHED [5/8] COPY requirements.txt ./                                   0.0s 
 => [6/8] RUN pip install --no-cache-dir -r requirements.txt -i https://  866.3s 
 => [7/8] RUN mkdir -p api/scripts/query_results                            0.4s
 => [8/8] COPY . .                                                          0.1s
 => exporting to image                                                      1.5s
 => => exporting layers                                                     1.5s
 => => writing image sha256:8f2f305765cda32b62661a411bc7948a2f3189c8a24d17  0.0s 
 => => naming to docker.io/library/query-api-requirements                   0.0s 

View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/u31nkq43sm8cz96jotfys5s7w

 1 warning found (use docker --debug to expand):
 - SecretsUsedInArgOrEnv: Do not use ARG or ENV instructions for sensitive data (ENV "SSH_KEY_PATH") (line 10)
```