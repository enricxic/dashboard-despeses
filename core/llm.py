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
    for alt in ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.5-pro", "gemini-flash-latest", "gemini-pro-latest"]:
        if alt not in models_to_try:
            models_to_try.append(alt)
        
    quota_exhausted = False
    for current_model in models_to_try:
        if quota_exhausted:
            break

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
                        parts = candidates[0].get("content", {}).get("parts", [{}])
                        content = parts[0].get("text", "") if parts else ""
                        if content is None:
                            content = ""
                        clean_content = content.strip() if isinstance(content, str) else ""
                        if json_mode and clean_content and not clean_content.endswith("}") and not clean_content.endswith("]") and not clean_content.endswith("```"):
                            if attempt < max_attempts - 1:
                                time.sleep(1.5)
                                continue # Reintentar si està truncat
                            last_error = f"La IA ha tallat la resposta prematurament (truncat). Resposta crua:\n{content}"
                            break # Provar següent model
                        return True, content, elapsed
                    last_error = "Resposta buida de Gemini"
                    break # Provar següent model
                elif resp.status_code == 429:
                    resp_txt = resp.text
                    is_quota = (
                        "RESOURCE_EXHAUSTED" in resp_txt
                        or "QuotaFailure" in resp_txt
                        or "GenerateContentRequests" in resp_txt
                        or "quota" in resp_txt.lower()
                    )
                    if is_quota:
                        # Error de quota global per clau/projecte: aturar immediatament (fail-fast)
                        # No té sentit esperar 16s ni provar altres models Gemini que comparteixen la mateixa quota
                        quota_exhausted = True
                        last_error = f"HTTP 429 ({current_model}): Quota de Gemini esgotada (RESOURCE_EXHAUSTED)."
                        break
                    else:
                        if attempt < max_attempts - 1:
                            time.sleep(1.5)
                            continue
                        last_error = f"HTTP 429 ({current_model}): Límit de peticions temporal assolit."
                        break
                elif resp.status_code == 503:
                    if attempt < max_attempts - 1:
                        time.sleep(2.0)
                        continue
                    last_error = f"HTTP 503 ({current_model}): Servei temporalment no disponible."
                    break
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
    
    # Si la quota de Gemini està esgotada o ha fallat amb 429, provem fallback automàtic transparent a OpenRouter
    if quota_exhausted or "429" in last_error:
        try:
            import streamlit as st
            openrouter_key = st.secrets.get("OPENROUTER_API_KEY", "")
            if openrouter_key:
                fallback_model = "deepseek/deepseek-chat" if not image_bytes else "nvidia/nemotron-3.5-super-vl:free"
                fb_ok, fb_content, fb_elapsed = _call_openai_compatible(
                    prompt=prompt,
                    api_key=openrouter_key,
                    model_name=fallback_model,
                    provider="openrouter",
                    start_time=start_time,
                    json_mode=json_mode,
                    image_bytes=image_bytes,
                    mime_type=mime_type
                )
                if fb_ok:
                    try:
                        st.toast(f"⚡ Quota de Gemini esgotada (429). S'ha utilitzat automàticament {fallback_model} via OpenRouter!", icon="ℹ️")
                    except Exception:
                        pass
                    return True, fb_content, fb_elapsed
        except Exception:
            pass

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

    # Per OpenRouter, 4000 tokens evita errors 402 si el balanç és reduït
    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 4000
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if provider == "openrouter":
        # Desactivar raonament intern (effort: none) per no malgastar el pressupost de tokens en OCR/JSON
        payload["reasoning"] = {"effort": "none"}
    
    max_attempts = 2
    last_error = ""
    for attempt in range(max_attempts):
        try:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=90)
            elapsed = round(time.time() - start_time, 2)
            
            # Si el model no suporta response_format o reasoning (error 400), retirem el paràmetre no compatible
            if resp.status_code == 400:
                modified = False
                if json_mode and "response_format" in payload:
                    del payload["response_format"]
                    modified = True
                if "reasoning" in payload:
                    del payload["reasoning"]
                    modified = True
                if modified:
                    resp = requests.post(base_url, headers=headers, json=payload, timeout=90)
            
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    first_choice = choices[0]
                    message = first_choice.get("message", {})
                    content = message.get("content")
                    if content is None:
                        # Fallback a reasoning o reasoning_content si content és buit o None
                        content = message.get("reasoning") or message.get("reasoning_content") or ""
                    
                    clean_content = content.strip() if isinstance(content, str) else ""

                    if not clean_content:
                        finish_reason = first_choice.get("finish_reason")
                        if finish_reason == "length":
                            last_error = f"El model {model_name} ha esgotat el límit de tokens (length) abans de produir la resposta."
                        else:
                            last_error = f"Resposta buida de l'API compatible ({model_name})"
                        break

                    if json_mode and clean_content and not clean_content.endswith("}") and not clean_content.endswith("]") and not clean_content.endswith("```"):
                        if attempt < max_attempts - 1:
                            time.sleep(2.0)
                            continue
                        return False, f"La IA ha tallat la resposta prematurament (truncat). Resposta crua:\n{content}", elapsed
                    return True, content, elapsed
                last_error = "Resposta buida de l'API compatible"
                break
            elif resp.status_code == 402:
                # OpenRouter: Balanç de crèdits inferior a max_tokens (ex: "can only afford 1447")
                import re
                match_tokens = re.search(r"can only afford (\d+)", resp.text)
                if match_tokens:
                    afford_tokens = int(match_tokens.group(1))
                    if afford_tokens >= 120:
                        payload["max_tokens"] = max(100, afford_tokens - 20)
                        resp_retry = requests.post(base_url, headers=headers, json=payload, timeout=90)
                        if resp_retry.status_code == 200:
                            data = resp_retry.json()
                            choices = data.get("choices", [])
                            if choices:
                                content = choices[0].get("message", {}).get("content", "")
                                return True, content, round(time.time() - start_time, 2)
                
                # Si no hi ha crèdits suficients a OpenRouter, fallback automàtic a Gemini (gratuït)
                try:
                    import streamlit as st
                    gemini_key = st.secrets.get("GEMINI_API_KEY", "")
                    if gemini_key:
                        return _call_gemini(prompt, gemini_key, "gemini-2.5-flash", start_time, json_mode=json_mode, image_bytes=image_bytes, mime_type=mime_type)
                except Exception:
                    pass

                last_error = f"Balanç de crèdits esgotat a OpenRouter ({model_name}). Recomanació: Selecciona el motor 'Gemini (2.5 Flash)' gratuït a la configuració superior."
                break
            elif resp.status_code == 404 and "Filter by Image Support" in resp.text:
                last_error = f"El model '{model_name}' és només de text i no accepta imatges directes. S'ha d'extreure el text amb OCR prèviament o triar un model multimodal com Gemini."
                break
            elif resp.status_code in [503, 429]:
                if attempt < max_attempts - 1:
                    sleep_time = 1.5 if resp.status_code == 429 else 2.0
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
