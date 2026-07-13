"""Web看板启动脚本"""
import subprocess
import sys
import os

# 安装web依赖
print("安装Web依赖...")
web_dir = os.path.join(os.path.dirname(__file__), 'web')
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", os.path.join(web_dir, "requirements.txt")],
    capture_output=True, text=True, timeout=60
)
if result.returncode != 0:
    print(f"安装失败: {result.stderr[-300:]}")
else:
    print("✅ Web依赖安装完成")

# 启动FastAPI
print("\n启动Web看板...")
print("="*50)
print("🌐 访问地址: http://localhost:8000")
print("📊 API文档: http://localhost:8000/docs")
print("="*50)
print("\n按 Ctrl+C 停止\n")

os.chdir(web_dir)
subprocess.run([
    sys.executable, "-m", "uvicorn", "api:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
])
