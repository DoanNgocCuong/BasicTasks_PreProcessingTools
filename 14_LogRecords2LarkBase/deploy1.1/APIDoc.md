```bash
curl --location 'http://127.0.0.1:5000/api/create-many-records' \
--header 'Content-Type: application/json' \
--data '{
    "config": {
        "app_id": "cli_a7852e8dc6fc5010",
        "app_secret": "6SIj0RfQ0ZwROvUhkjAwLebhLfJkIwnT",
        "app_base_token": "O3EybGW4TaQ1SusAtukl9RXzgJd",
        "base_table_id": "tblwZ1BvvVgP4Ot7"
    },
    "records": [
        {
            "fields": {
                "user_name": "Example Text 1",
                "stt_question": 1
            }
        },
        {
            "fields": {
                "user_name": "Example Text 2",
                "stt_question": 2
            }
        }
    ]
}'
```

hoặc 
```bash
curl --location 'http://127.0.0.1:5000/api/create-many-records' \
--header 'Content-Type: application/json' \
--data '{
    "config": {
        "app_doannngoccuong_id": "cli_a7852e8dc6fc5010",
        "app_doannngoccuong_secret": "6SIj0RfQ0ZwROvUhkjAwLebhLfJkIwnT",
        "app_base_token": "O3EybGW4TaQ1SusAtukl9RXzgJd",
        "base_table_id": "tblwZ1BvvVgP4Ot7"
    },
    "records": [
        {
            "fields": {
                "user_name": "Example Text 1",
                "stt_question": 1
            }
        },
        {
            "fields": {
                "user_name": "Example Text 2",
                "stt_question": 2
            }
        }
    ]
}'
```

hoặc 
```bash
{
    "config": {
        "appid": "cli_a7852e8dc6fc5010",
        "appsecret": "6SIj0RfQ0ZwROvUhkjAwLebhLfJkIwnT",
        "app_base_token": "O3EybGW4TaQ1SusAtukl9RXzgJd",
        "base_table_id": "tblwZ1BvvVgP4Ot7"
    },
    "records": [
        {
            "fields": {
                "user_name": "Example Text 1",
                "stt_question": 1
            }
        },
        {
            "fields": {
                "user_name": "Example Text 2",
                "stt_question": 2
            }
        }
    ]
}
```


```bash
@im lặng
chị Mai Anh, em mới ĐÓNG THÀNH 1 API duy nhất như này, 
----------------
Sau log lên lark cho tiện ạ. 
-------------
- app_id, app secret là id, secret của App (chẳng hạn: app blue-scrape, ...) <điều kiện: Cần add Application App vào trang Base đích >
```

```bash
Dạ vâng ạ, 
- Em test trên cả tài khoản cá nhân và tài khoản công ty được chị ạ. 

1. Cơ chế hoạt động: 
- Từ app_id, app_secret (app blue scrape, app DoanNgocCuong chẳng hạn, ...) -> lấy tenantAccessToken <vì tenantAccessToken 2 tiếng là nó sẽ tự động làm mới, nên là phải lấy tenantAccessToken nằng app_id, app_secret mỗi lần gọi API>
- sau đó từ tenantAccessToken, app_base_token, base_table_id, records_fields_json => Ghi vào table-base
(lấy app_base_token, base_table_id từ đường link của base , chẳng hạn: 

https://stepupenglish.sg.larksuite.com/base/FQTWbwSlvaLRLlsgpjwlbWOeg7f?table=tblzgYHSrqN5zN42&view=vewRx8N9zF
thì app_base_token = FQTWbwSlvaLRLlsgpjwlbWOeg7f , base_table_id = tblzgYHSrqN5zN42)

2. Về quyền: 
- App app blue scrape, app DoanNgocCuong cần có quyền ghi vào lark (quản trị viên duyệt / với tài khoản cá nhân thì mình tự duyệt cho mình :3 ) 
- và Base cần kết nối với App (vào trang base, chẳng hạn: https://stepupenglish.sg.larksuite.com/base/FQTWbwSlvaLRLlsgpjwlbWOeg7f?table=tblzgYHSrqN5zN42&view=vewRx8N9zF
Tìm đến dấu ... góc trên cùng bên phải, ấn xem thêm, thêm ứng dụng (App: app blue scrape, app DoanNgocCuong, ...) 
```