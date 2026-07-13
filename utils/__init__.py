"""日志工具"""
import sys
from loguru import logger

def setup_logger(level="INFO", log_file=None):
    """配置日志"""
    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<7}</level> | {name}:{function}:{line} - <level>{message}</level>",
        colorize=True,
    )
    
    # 文件输出
    if log_file:
        logger.add(
            log_file,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
        )
    
    return logger

# 默认logger实例
log = setup_logger()
