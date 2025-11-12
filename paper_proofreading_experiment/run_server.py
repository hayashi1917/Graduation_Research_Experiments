#!/usr/bin/env python3
"""
論文校正実験システム - Webサーバー起動スクリプト
"""

import sys
from pathlib import Path

# バックエンドディレクトリをパスに追加
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import uvicorn

if __name__ == "__main__":
    print("="*70)
    print("論文校正実験システム - Webサーバー")
    print("="*70)
    print()
    print("サーバーを起動しています...")
    print("アクセスURL: http://localhost:8000")
    print()
    print("終了するには Ctrl+C を押してください")
    print("="*70)
    print()

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
