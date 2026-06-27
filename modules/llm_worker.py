from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


class LLMWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, api_key: str, model: str, prompt: str, timeout_seconds: int = 20) -> None:
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.timeout_seconds = timeout_seconds

    @pyqtSlot()
    def run(self) -> None:
        try:
            raw_text = self._request_gemini()
            dialogue = self._parse_dialogue(raw_text)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return

        self.finished.emit(dialogue)

    def _request_gemini(self) -> str:
        payload = {
            "model": self.model,
            "input": self.prompt,
            "generation_config": {
                "temperature": 0.9,
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            GEMINI_INTERACTIONS_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Gemini API request failed: {exc.reason}") from exc

        try:
            data = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini API returned invalid JSON.") from exc

        text = self._extract_text(data)
        if not text:
            raise RuntimeError("Gemini API returned no text output.")
        return text

    @staticmethod
    def _extract_text(data: dict) -> str:
        output_text = data.get("output_text")
        if isinstance(output_text, str):
            return output_text

        for step in reversed(data.get("steps", [])):
            content = step.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                if parts:
                    return "".join(parts)
        return ""

    @staticmethod
    def _parse_dialogue(raw_text: str) -> str:
        text = raw_text.strip()
        if not text:
            raise RuntimeError("Gemini response is empty.")

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            text = match.group(0)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini response was not valid JSON.") from exc

        dialogue = data.get("dialogue")
        if not isinstance(dialogue, str):
            raise RuntimeError("Gemini response did not contain a string dialogue field.")

        dialogue = dialogue.strip()
        if not dialogue:
            raise RuntimeError("Gemini dialogue was empty.")
        dialogue = dialogue.rstrip("。.!！?？~～…，,、；;：:")
        if len(dialogue) > 25:
            dialogue = dialogue[:25]
        return dialogue
