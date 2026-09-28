from __future__ import annotations
import json
from typing import Any
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash-lite"
SYSTEM_PROMPT = """
You are the TaskFlow desktop assistant.
You may ONLY create, update, or delete tasks, categories, tags, and title presets.
Never browse the web, access files, execute code, change settings, or perform any other action.
Use the supplied TaskFlow snapshot to resolve names to IDs. If multiple plausible records match,
ask for clarification instead of guessing. Interpret Italian and English naturally.
Relative dates are relative to TODAY in the snapshot. Ask if a required title is missing.
For deletion, call the delete function; the application will require explicit confirmation.
Never claim a destructive operation happened before the application confirms it.
Keep responses concise and in the user's language.
"""
FUNCTION_DECLARATIONS = [
 {"type":"function","name":"create_task","description":"Create one TaskFlow task.","parameters":{"type":"object","properties":{"title":{"type":"string"},"description":{"type":"string"},"due_date":{"type":"string"},"start_time":{"type":"string"},"end_time":{"type":"string"},"priority":{"type":"string","enum":["low","medium","high"]},"category":{"type":"string"},"tags":{"type":"string"},"recurrence":{"type":"string","enum":["none","daily","weekly","monthly"]}},"required":["title","due_date","category","tags","priority","recurrence"]}},
 {"type":"function","name":"update_task","description":"Update an existing task by ID.","parameters":{"type":"object","properties":{"task_id":{"type":"integer"},"title":{"type":"string"},"description":{"type":"string"},"due_date":{"type":"string"},"start_time":{"type":"string"},"end_time":{"type":"string"},"priority":{"type":"string","enum":["low","medium","high"]},"category":{"type":"string"},"tags":{"type":"string"},"recurrence":{"type":"string","enum":["none","daily","weekly","monthly"]},"completed":{"type":"boolean"}},"required":["task_id"]}},
 {"type":"function","name":"delete_task","description":"Delete a task by ID; confirmation is required.","parameters":{"type":"object","properties":{"task_id":{"type":"integer"}},"required":["task_id"]}},
 {"type":"function","name":"create_category","description":"Create a category.","parameters":{"type":"object","properties":{"name":{"type":"string"},"color":{"type":"string"},"icon":{"type":"string"}},"required":["name"]}},
 {"type":"function","name":"update_category","description":"Update a category by ID.","parameters":{"type":"object","properties":{"category_id":{"type":"integer"},"name":{"type":"string"},"color":{"type":"string"},"icon":{"type":"string"}},"required":["category_id"]}},
 {"type":"function","name":"delete_category","description":"Delete a category by ID; confirmation is required.","parameters":{"type":"object","properties":{"category_id":{"type":"integer"}},"required":["category_id"]}},
 {"type":"function","name":"create_tag","description":"Create a tag.","parameters":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}},
 {"type":"function","name":"update_tag","description":"Update a tag by ID.","parameters":{"type":"object","properties":{"tag_id":{"type":"integer"},"name":{"type":"string"}},"required":["tag_id","name"]}},
 {"type":"function","name":"delete_tag","description":"Delete a tag by ID; confirmation is required.","parameters":{"type":"object","properties":{"tag_id":{"type":"integer"}},"required":["tag_id"]}},
 {"type":"function","name":"create_title_preset","description":"Create a predefined title for a category.","parameters":{"type":"object","properties":{"category_id":{"type":"integer"},"title":{"type":"string"}},"required":["category_id","title"]}},
 {"type":"function","name":"update_title_preset","description":"Update a predefined title.","parameters":{"type":"object","properties":{"preset_id":{"type":"integer"},"category_id":{"type":"integer"},"title":{"type":"string"}},"required":["preset_id","category_id","title"]}},
 {"type":"function","name":"delete_title_preset","description":"Delete a predefined title; confirmation is required.","parameters":{"type":"object","properties":{"preset_id":{"type":"integer"}},"required":["preset_id"]}},
]

class TaskFlowAgent:
    """Narrow AI planning layer; it only returns declared TaskFlow operations."""
    def __init__(self, api_key: str, model: str = MODEL):
        if not api_key:
            raise ValueError("Gemini API key is not configured.")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def plan(self, user_text: str, context: dict[str, Any], audio_bytes: bytes | None = None,
             mime_type: str = "audio/m4a") -> dict[str, Any]:
        prompt = SYSTEM_PROMPT + "\nTODAY AND TASKFLOW SNAPSHOT:\n" + json.dumps(context, ensure_ascii=False, default=str)
        prompt += "\nUSER REQUEST:\n" + (user_text or "(voice command; analyze the attached audio)")
        parts: list[Any] = [types.Part.from_text(text=prompt)]
        if audio_bytes:
            parts.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime_type))
        config = types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=FUNCTION_DECLARATIONS)],
            temperature=0.1,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = self.client.models.generate_content(model=self.model, contents=parts, config=config)
        return {"text": response.text or "", "actions": [{"name": c.name, "args": dict(c.args or {})} for c in (response.function_calls or [])]}
