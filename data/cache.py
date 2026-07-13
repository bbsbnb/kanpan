"""数据缓存模块"""
import os
import json
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

class DataCache:
    """本地文件缓存，避免重复请求API"""
    
    def __init__(self, cache_dir: str = "./data/cache", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_cache_path(self, key: str, ext: str = ".pkl") -> Path:
        """获取缓存文件路径"""
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        return self.cache_dir / f"{safe_name}{ext}"
    
    def get(self, key: str) -> Optional[Any]:
        """从缓存读取数据"""
        path = self._get_cache_path(key, ".pkl")
        if not path.exists():
            return None
        
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            
            # 检查过期
            cached_time = datetime.fromisoformat(data["timestamp"])
            if datetime.now() - cached_time > self.ttl:
                path.unlink(missing_ok=True)
                return None
            
            return data["data"]
        except Exception as e:
            print(f"[Cache] Read error: {e}")
            return None
    
    def set(self, key: str, data: Any) -> bool:
        """写入缓存"""
        try:
            path = self._get_cache_path(key, ".pkl")
            payload = {
                "timestamp": datetime.now().isoformat(),
                "data": data,
            }
            with open(path, "wb") as f:
                pickle.dump(payload, f)
            return True
        except Exception as e:
            print(f"[Cache] Write error: {e}")
            return False
    
    def clear(self, key: str = None) -> bool:
        """清除缓存"""
        try:
            if key:
                path = self._get_cache_path(key, ".pkl")
                path.unlink(missing_ok=True)
            else:
                # 清除全部
                for f in self.cache_dir.glob("*.pkl"):
                    f.unlink()
            return True
        except Exception as e:
            print(f"[Cache] Clear error: {e}")
            return False
