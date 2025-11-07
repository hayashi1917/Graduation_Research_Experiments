"""
LLM APIクライアント
Gemini API と Claude API をサポート
"""

import os
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
import base64
import json


class LLMClient:
    """LLM APIクライアントの基底クラス"""

    def __init__(self, model: str, temperature: float = 0.0):
        self.model = model
        self.temperature = temperature

    def call(
        self,
        prompt: str,
        pdf_path: Optional[Path] = None,
        tex_path: Optional[Path] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        LLMを呼び出す

        Args:
            prompt: プロンプトテキスト
            pdf_path: PDFファイルのパス（オプション）
            tex_path: TeXファイルのパス（オプション）
            system_prompt: システムプロンプト（オプション）

        Returns:
            LLMの応答テキスト
        """
        raise NotImplementedError


class GeminiClient(LLMClient):
    """Gemini APIクライアント"""

    def __init__(self, model: str, api_key: str, temperature: float = 0.0):
        super().__init__(model, temperature)
        self.api_key = api_key

        # google-generativeai をインポート
        try:
            import google.generativeai as genai
            self.genai = genai
            genai.configure(api_key=api_key)
        except ImportError:
            raise ImportError(
                "google-generativeai パッケージがインストールされていません。\n"
                "pip install google-generativeai を実行してください。"
            )

    def call(
        self,
        prompt: str,
        pdf_path: Optional[Path] = None,
        tex_path: Optional[Path] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Gemini APIを呼び出す"""

        # モデルを初期化
        model = self.genai.GenerativeModel(
            model_name=self.model,
            generation_config={
                "temperature": self.temperature,
            },
        )

        # コンテンツを構築
        contents = []

        # システムプロンプトがある場合は先頭に追加
        if system_prompt:
            contents.append(system_prompt + "\n\n")

        # PDFファイルを追加
        if pdf_path and pdf_path.exists():
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            pdf_part = {
                "mime_type": "application/pdf",
                "data": pdf_data,
            }
            contents.append(pdf_part)

        # TeXファイルを追加
        if tex_path and tex_path.exists():
            with open(tex_path, "r", encoding="utf-8") as f:
                tex_content = f.read()
            contents.append(f"\n\n# TeXソースコード\n\n```latex\n{tex_content}\n```\n\n")

        # プロンプトを追加
        contents.append(prompt)

        # APIを呼び出す
        response = model.generate_content(contents)

        return response.text


class ClaudeClient(LLMClient):
    """Claude APIクライアント"""

    def __init__(self, model: str, api_key: str, temperature: float = 0.0):
        super().__init__(model, temperature)
        self.api_key = api_key

        # anthropic をインポート
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError(
                "anthropic パッケージがインストールされていません。\n"
                "pip install anthropic を実行してください。"
            )

    def call(
        self,
        prompt: str,
        pdf_path: Optional[Path] = None,
        tex_path: Optional[Path] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Claude APIを呼び出す"""

        # メッセージコンテンツを構築
        content = []

        # PDFファイルを追加（base64エンコード）
        if pdf_path and pdf_path.exists():
            with open(pdf_path, "rb") as f:
                pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_data,
                },
            })

        # TeXファイルを追加
        tex_content_text = ""
        if tex_path and tex_path.exists():
            with open(tex_path, "r", encoding="utf-8") as f:
                tex_content = f.read()
            tex_content_text = f"\n\n# TeXソースコード\n\n```latex\n{tex_content}\n```\n\n"

        # プロンプトを追加
        content.append({
            "type": "text",
            "text": tex_content_text + prompt,
        })

        # APIを呼び出す
        message = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            temperature=self.temperature,
            system=system_prompt if system_prompt else "",
            messages=[{"role": "user", "content": content}],
        )

        return message.content[0].text


def create_llm_client(
    provider: str,
    model: str,
    api_key_env: str,
    temperature: float = 0.0,
) -> LLMClient:
    """
    LLMクライアントを作成する

    Args:
        provider: LLMプロバイダー（"gemini" または "claude"）
        model: モデル名
        api_key_env: APIキーの環境変数名
        temperature: 温度パラメータ

    Returns:
        LLMクライアント
    """
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(
            f"環境変数 {api_key_env} が設定されていません。\n"
            f"APIキーを設定してください。"
        )

    if provider.lower() == "gemini":
        return GeminiClient(model, api_key, temperature)
    elif provider.lower() == "claude":
        return ClaudeClient(model, api_key, temperature)
    else:
        raise ValueError(f"サポートされていないプロバイダー: {provider}")


if __name__ == "__main__":
    # テスト用コード
    print("LLM Clientモジュールのテスト")

    # Geminiクライアントのテスト
    try:
        gemini_client = create_llm_client(
            provider="gemini",
            model="gemini-1.5-pro",
            api_key_env="GEMINI_API_KEY",
        )
        print("✓ Geminiクライアントの初期化成功")
    except Exception as e:
        print(f"✗ Geminiクライアントの初期化失敗: {e}")

    # Claudeクライアントのテスト
    try:
        claude_client = create_llm_client(
            provider="claude",
            model="claude-3-5-sonnet-20241022",
            api_key_env="ANTHROPIC_API_KEY",
        )
        print("✓ Claudeクライアントの初期化成功")
    except Exception as e:
        print(f"✗ Claudeクライアントの初期化失敗: {e}")
