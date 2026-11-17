import json
import re
import time

import requests

from . import config


class LLMError(RuntimeError):
    pass


def chat(system, user, model=None, temperature=0.8, max_tokens=8192, retries=3):
    """OpenAI 兼容 chat/completions 调用，带指数退避重试。"""
    url = f"{config.BASE_URL}/chat/completions"
    payload = {
        "model": model or config.MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {config.API_KEY}", "Content-Type": "application/json"}
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=600)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                raise LLMError("模型返回空内容")
            return content.strip()
        except (requests.RequestException, LLMError, KeyError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 3)
    raise LLMError(f"LLM 调用失败（已重试 {retries} 次）: {last_err}")


def chat_json(system, user, model=None, temperature=0.7, max_tokens=8192):
    """要求模型输出 JSON 并解析；容忍 markdown 代码块包裹。"""
    raw = chat(system + "\n\n只输出合法 JSON，不要输出任何其他文字。", user,
               model=model, temperature=temperature, max_tokens=max_tokens)
    text = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 截取最外层大括号再试一次
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise LLMError(f"无法解析模型 JSON 输出: {text[:300]}")