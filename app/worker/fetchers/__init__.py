from app.worker.fetchers.base import BaseFetcher
from app.worker.fetchers.registry import FetcherRegistry
from app.worker.fetchers.baidu import BaiduFetcher
from app.worker.fetchers.yike import YiKeFetcher
from app.worker.fetchers.hefeng import HeFengFetcher

__all__ = [
    "BaseFetcher",
    "FetcherRegistry",
    "BaiduFetcher",
    "YiKeFetcher",
    "HeFengFetcher",
]
