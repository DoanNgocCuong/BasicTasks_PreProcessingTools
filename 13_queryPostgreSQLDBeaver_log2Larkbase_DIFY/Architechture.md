- Kiến trúc tham khảo 1 project đã làm trước đây: 
https://github.com/DoanNgocCuong/MiniProd_ContentEngFlow_IELTSStepUpE_T102024/blob/main/deploy/backend/app.py

Cấu trúc thư mục: 
```
src/
|
├── .ssh/                # Thư mục chứa tệp SSH key
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── scripts/
│   │   │   ├── __init__.py
│   │   │   ├── connect_PostgresSQLDBeaver.py
│   │   │   ├── queryRating_logLarkbase.py
│   │   │   ├── queryRatingToolsWorkflowMindpal_logLarkbase.py
│   │   │   └── utils_*.py
│   │   └── scripts.py
│   ├── app.py
│   ├── requirements.txt
|   ├── id_rsa  # Di chuyển tệp vào đây
│   └── Dockerfile
```
