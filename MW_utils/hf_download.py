from huggingface_hub import snapshot_download
from typing import Dict, Iterable, List, Literal, Optional, Type, Union
import os

def download_model_with_snapshot(
    repo_id: str,
    local_dir: str,
    repo_type: str = None,
    revision: str = None,
    cache_dir: str = None,
    library_name: str = None,
    library_version: str = None,
    user_agent: str = None,
    proxies: dict = None,
    etag_timeout: float = 10,
    force_download: bool = False,
    token: str = None,
    headers: dict = None,
    local_files_only: bool = False,
    allow_patterns: Optional[Union[List[str], str]] = None,
    ignore_patterns: Optional[Union[List[str], str]] = None,
    max_workers: int = 8,
    tqdm_class: 'tqdm' = None,
    endpoint: str = 'https://hf-mirror.com',
):
    """
    :param repo_id: 模型的 repo_id，例如 "openai/gpt-oss-safeguard-20b"
    :param local_dir: 存放下载文件的本地文件夹
    :param repo_type: 模型类型，可选 "model"、"dataset"、"space"
    :param revision: 模型版本（branch，tag，或 commit hash）
    :param cache_dir: 缓存目录
    :param library_name: 库名（如 transformers）
    :param library_version: 库版本
    :param user_agent: 自定义请求头 User-Agent
    :param proxies: 代理设置
    :param etag_timeout: 获取 ETag 的超时时间（秒）
    :param force_download: 是否强制重新下载文件
    :param token: 用于身份验证的 Hugging Face 令牌
    :param headers: 自定义请求头
    :param local_files_only: 是否仅使用本地缓存的文件
    :param allow_patterns: 只下载符合指定模式的文件
    :param ignore_patterns: 忽略下载符合指定模式的文件
    :param max_workers: 同时下载的最大线程数
    :param tqdm_class: 自定义进度条类
    :param endpoint: 模型仓库的 API 端点
    :return: 下载文件的本地路径
    """
    
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    else:
        print(f"模型文件夹{local_dir}已存在。")
        return local_dir

    download_params = {
        "repo_id": repo_id,
        "local_dir": local_dir,
        "repo_type": repo_type,
        "revision": revision,
        "cache_dir": cache_dir,
        "library_name": library_name,
        "library_version": library_version,
        "user_agent": user_agent,
        "etag_timeout": etag_timeout,
        "force_download": force_download,
        "token": token,
        "headers": headers,
        "local_files_only": local_files_only,
        "allow_patterns": allow_patterns,
        "ignore_patterns": ignore_patterns,
        "max_workers": max_workers,
        "tqdm_class": tqdm_class,
        "proxies": proxies,
        "endpoint": endpoint,
    }

    download_params = {key: value for key, value in download_params.items() if value is not None}
    print(f"开始下载模型 https://huggingface.co/{repo_id} 到本地目录 {local_dir}...")
    snapshot_path = snapshot_download(**download_params)

    return snapshot_path
