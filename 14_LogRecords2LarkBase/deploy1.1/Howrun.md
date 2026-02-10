```bash
Successfully built 6d55b095cdb7
Successfully tagged larkbase-api:latest
SECURITY WARNING: You are building a Docker image from Windows against a non-Windows Docker host. All files and directories added to build context will have '-rwxr-xr-x' permissions. It is recommended to double check and reset permissions for sensitive files and directories.
```

Build image

```bash
docker build -t larkbase-api .
```

Run container
```bash
docker run -p 3000:3000 larkbase-api
```