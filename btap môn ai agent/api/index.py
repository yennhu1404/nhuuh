import sys
from pathlib import Path

# Đảm bảo thư mục gốc dự án nằm trong sys.path khi chạy trên Vercel Serverless
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import B2BAgentHttpHandler


class handler(B2BAgentHttpHandler):
    """Vercel Python Serverless entrypoint kế thừa toàn bộ API từ B2BAgentHttpHandler."""
    pass
