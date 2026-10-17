import time
import requests
import base64
from typing import Tuple, Dict, Any

def call_llm_api(
    prompt: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
    provider: str = "gemini",
    json_mode: bool = False,
    image_bytes: bytes = None,
    mime_type: str = "image/jpeg"
) -> Tuple[bool, str, float]:
    """
    Funció centralitzada per fer crides a qualsevol proveïdor d'IA (Gemini, DeepSeek, OpenRouter).
    Suporta prompts de text, mode JSON estructurat i imatges (multimodal).
    """
    start_time = time.time()
    
    if provider == "gemini":
        return _call_gemini(prompt, api_key, model_name, start_time, json_mode=json_mode, image_bytes=image_bytes, mime_type=mime_type)
    elif provider in ["deepseek", "openrouter", "openai"]:
        return _call_openai_compatible(prompt, api_key, model_name, provider, start_time, json_mode=json_mode, image_bytes=image_bytes, mime_type=mime_type)
    else:
        return False, f"Proveïdor d'IA desconegut: {provider}", 0.0

def _call_gemini(
    prompt: str,
    api_key: str,
    model_name: str,
    start_time: float,
    json_mode: bool = False,
    image_bytes: bytes = None,
    mime_type: str = "image/jpeg"
) -> Tuple[bool, str, float]:
    models_to_try = [model_name]
    for alt in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-flash-latest", "gemini-pro-latest"]:
        if alt not in models_to_try:
            models_to_try.append(alt)
        
    last_error = ""
    for current_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
        parts = [{"text": prompt}]
        if image_bytes:
            encoded_image = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": encoded_image
                }
            })
            
        gen_config: Dict[str, Any] = {
            "temperature": 0.1,
            "maxOutputTokens": 4096
        }
        if json_mode:
            gen_config["responseMimeType"] = "application/json"
            
        payload = {
            "contents": [
                {
                    "parts": parts
                }
            ],
            "generationConfig": gen_config
        }
        
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                resp = requests.post(url, json=payload, timeout=90)
                elapsed = round(time.time() - start_time, 2)
                
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        clean_content = content.strip()
                        if clean_content and not clean_content.endswith("}") and not clean_content.endswith("]") and not clean_content.endswith("```"):
                            if attempt < max_attempts - 1:
                                time.sleep(2.0)
                                continue # Reintentar si està truncat
                            last_error = f"La IA ha tallat la resposta prematurament (truncat). Resposta crua:\n{content}"
                            break # Try the next model
                        return True, content, elapsed
                    last_error = "Resposta buida de Gemini"
                    break # Try the next model
                elif resp.status_code in [503, 429]:
                    if attempt < max_attempts - 1:
                        sleep_time = 16.0 if resp.status_code == 429 else 15.0
                        time.sleep(sleep_time)
                        continue
                    last_error = f"HTTP {resp.status_code} ({current_model}): {resp.text}"
                    break # Try the next model
                else:
                    last_error = f"Error HTTP {resp.status_code} ({current_model}): {resp.text}"
                    break
            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(1.0)
                    continue
                last_error = f"Excepció en cridar Gemini ({current_model}): {str(e)}"
                break
                
    elapsed = round(time.time() - start_time, 2)
    return False, last_error, elapsed

def _call_openai_compatible(
    prompt: str,
    api_key: str,
    model_name: str,
    provider: str,
    start_time: float,
    json_mode: bool = False,
    image_bytes: bytes = None,
    mime_type: str = "image/jpeg"
) -> Tuple[bool, str, float]:
    if provider == "deepseek":
        base_url = "https://api.deepseek.com/chat/completions"
    elif provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1/chat/completions"
    else:
        base_url = "https://api.openai.com/v1/chat/completions"
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://dashboard.local"
        headers["X-Title"] = "Dashboard Familiar"
        
    if image_bytes:
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{encoded_image}"
                    }
                }
            ]
        }]
    else:
        messages = [{"role": "user", "content": prompt}]

    # Per OpenRouter, 3000 tokens evita errors 402 si el balanç de crèdits és reduït
    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 3000
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    
    max_attempts = 2
    last_error = ""
    for attempt in range(max_attempts):
        try:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=90)
            elapsed = round(time.time() - start_time, 2)
            
            # Si el model no suporta response_format json_object (error 400), reintentem sense response_format
            if resp.status_code == 400 and json_mode and "response_format" in payload:
                del payload["response_format"]
                resp = requests.post(base_url, headers=headers, json=payload, timeout=90)
            
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    clean_content = content.strip()
                    if clean_content and not clean_content.endswith("}") and not clean_content.endswith("]") and not clean_content.endswith("```"):
                        if attempt < max_attempts - 1:
                            time.sleep(2.0)
                            continue
                        return False, f"La IA ha tallat la resposta prematurament (truncat). Resposta crua:\n{content}", elapsed
                    return True, content, elapsed
                last_error = "Resposta buida de l'API compatible"
                break
            elif resp.status_code in [503, 429]:
                if attempt < max_attempts - 1:
                    sleep_time = 16.0 if resp.status_code == 429 else 15.0
                    time.sleep(sleep_time)
                    continue
                last_error = f"HTTP {resp.status_code} ({model_name}): {resp.text}"
                break
            else:
                last_error = f"Error HTTP {resp.status_code} ({model_name}): {resp.text}"
                break
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(1.0)
                continue
            last_error = f"Excepció en cridar API ({model_name}): {str(e)}"
            break
            
    elapsed = round(time.time() - start_time, 2)
    return False, last_error, elapsed
