
```bash
curl -X POST http://103.253.20.13:25029/role_assign \
    -H "Content-Type: multipart/form-data" \
    -F "audio=@path_to_audio_file.wav" \
    -F "secret_key=codedongian" \
    -F "language=en"
```