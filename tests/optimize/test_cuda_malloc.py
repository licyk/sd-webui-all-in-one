"""CUDA malloc 优化测试"""

from sd_webui_all_in_one.optimize import cuda_malloc


def test_cuda_malloc_detection_and_env_merge(monkeypatch):
    monkeypatch.setattr(cuda_malloc, "get_gpu_names", lambda: {"NVIDIA GeForce RTX 4090"})
    assert cuda_malloc.is_nvidia_device() is True
    assert cuda_malloc.cuda_malloc_supported() is True
    assert cuda_malloc.get_pytorch_cuda_alloc_conf(is_cuda=True) == "cuda_malloc"

    monkeypatch.setattr(cuda_malloc, "get_gpu_names", lambda: {"GeForce GTX 1650"})
    assert cuda_malloc.cuda_malloc_supported() is False
    assert cuda_malloc.get_pytorch_cuda_alloc_conf(is_cuda=True) == "pytorch_malloc"

    monkeypatch.setattr(cuda_malloc, "get_gpu_names", lambda: {"AMD Radeon"})
    assert cuda_malloc.is_nvidia_device() is False
    assert cuda_malloc.get_pytorch_cuda_alloc_conf(is_cuda=True) is None

    origin = {"PYTORCH_CUDA_ALLOC_CONF": "old", "PYTORCH_ALLOC_CONF": ""}
    env = cuda_malloc.apply_pytorch_alloc_conf("backend:cudaMallocAsync", origin_env=origin)
    assert env["PYTORCH_CUDA_ALLOC_CONF"] == "backend:cudaMallocAsync,old"
    assert env["PYTORCH_ALLOC_CONF"] == "backend:cudaMallocAsync"
    assert origin["PYTORCH_CUDA_ALLOC_CONF"] == "old"
