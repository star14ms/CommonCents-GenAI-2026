import os
import json
import ssl
import urllib.request
import urllib.error
from dotenv import load_dotenv
from ..base import LLMProvider, ChatMessage


class ChatGPTProvider:
    """OpenAI ChatGPT LLM provider."""

    @property
    def name(self) -> str:
        return "ChatGPT"

    @property
    def id(self) -> str:
        return "chatgpt"

    def chat(self, messages: list[ChatMessage]) -> str:
        load_dotenv()

        api_key = (
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
            or os.environ.get("HF_TOKEN")
        )
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        ssl_verify = os.environ.get("OPENAI_SSL_VERIFY", "true").lower() not in {
            "0",
            "false",
            "no",
        }

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        if str(api_key).startswith("http://") or str(api_key).startswith("https://"):
            raise ValueError(
                "OPENAI_API_KEY is set to a URL. Put the endpoint URL in OPENAI_BASE_URL and put the real API token in OPENAI_API_KEY."
            )

        if "huggingface" in str(base_url).lower() and model == "gpt-4o-mini":
            raise ValueError(
                "OPENAI_MODEL is set to gpt-4o-mini, but this Hugging Face endpoint likely serves a different model. Set OPENAI_MODEL to your deployed endpoint model id."
            )

        formatted = [{"role": msg.role, "content": msg.content} for msg in messages]

        payload = json.dumps(
            {
                "model": model,
                "messages": formatted,
            }
        ).encode("utf-8")

        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        request = urllib.request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        if ssl_verify:
            try:
                import certifi

                ssl_context = ssl.create_default_context(cafile=certifi.where())
            except Exception:
                ssl_context = ssl.create_default_context()
        else:
            ssl_context = ssl._create_unverified_context()

        try:
            with urllib.request.urlopen(request, timeout=60, context=ssl_context) as response:
                response_json = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            if e.code == 404 and "model" in (body or "").lower():
                raise ValueError(
                    f"LLM endpoint request failed (404): model '{model}' not found. Set OPENAI_MODEL to the deployed model id for this endpoint."
                )
            raise ValueError(f"LLM endpoint request failed ({e.code}): {body or e.reason}")
        except Exception as e:
            raise ValueError(f"LLM endpoint request failed: {str(e)}")

        choices = response_json.get("choices") or []
        if choices:
            message = (choices[0] or {}).get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict)
                ]
                return "".join(text_parts).strip()
        return ""

