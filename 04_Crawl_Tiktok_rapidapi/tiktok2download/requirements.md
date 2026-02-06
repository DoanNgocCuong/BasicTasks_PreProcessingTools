# Mục tiêu: cài đặt nemo_toolkit[all]

Lỗi này xảy ra khi cài đặt `nemo_toolkit[all]` vì nó yêu cầu PyTorch phải được cài đặt trước. Hãy làm theo các bước sau:

1. Đầu tiên, cài đặt PyTorch:
```bash
pip install torch torchvision torchaudio
```

2. Sau đó, cài đặt CUDA toolkit nếu bạn có GPU NVIDIA (không bắt buộc):
```bash
# Nếu có GPU NVIDIA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

3. Sau khi PyTorch đã được cài đặt, thử cài đặt NeMo:
```bash
pip install nemo_toolkit['all']
```
