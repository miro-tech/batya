import urllib.request
import urllib.parse
import json
import ssl
import sys
import random
import socket
import re
import os

# Настройки
API_BASE = "https://batyavpn-tg.online"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def get_subscription_url(telegram_id):
    url = f"{API_BASE}/api/users/check/device/{urllib.parse.quote(str(telegram_id))}?guest=true&platform=android"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=20) as r:
            response = json.loads(r.read().decode())
        return response.get("remnawave", {}).get("subscription_url") if response.get("success") else None
    except Exception as e:
        print(f"[-] Ошибка API: {e}")
        return None

def process_config_data(data):
    cache = {}
    ipv4_pattern = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

    def resolve_and_replace(obj):
        if isinstance(obj, dict):
            keys = list(obj.keys())
            for k in keys:
                v = obj[k]
                if k == "address" and isinstance(v, str):
                    if not v.startswith("https://") and not ipv4_pattern.match(v):
                        if v not in cache:
                            try:
                                ip = socket.gethostbyname(v)
                                cache[v] = ip
                            except Exception:
                                cache[v] = v
                        obj[k] = cache[v]
                elif k == "alpn":
                    del obj[k]
                elif k in ["sni", "serverName"]:
                    obj[k] = "rbc.ru"
                resolve_and_replace(v)
        elif isinstance(obj, list):
            for item in obj:
                resolve_and_replace(item)
    resolve_and_replace(data)
    return data

def update_gist(content, gist_id, token):
    url = f"https://api.github.com/gists/{gist_id}"
    data = {"files": {"config.json": {"content": content}}}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), method='PATCH')
    req.add_header("Authorization", f"token {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return r.status == 200

def main():
    # Генерируем случайный ID каждый раз
    tg_id = str(random.randint(100_000_000, 999_999_999))
    print(f"[*] Идентификация с ID: {tg_id}")
    
    sub_url = get_subscription_url(tg_id)
    if not sub_url:
        print("[-] Ошибка: Не удалось получить подписку.")
        return

    try:
        json_url = f"{sub_url}/json"
        req = urllib.request.Request(json_url)
        with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
            config_data = json.loads(r.read().decode("utf-8"))
        
        processed_data = process_config_data(config_data)
        content = json.dumps(processed_data, indent=4, ensure_ascii=False)
        
        gist_id = os.environ.get("GIST_ID")
        gh_token = os.environ.get("GH_TOKEN")
        
        if gist_id and gh_token:
            if update_gist(content, gist_id, gh_token):
                print("[+] Успешно обновлено в Gist!")
        else:
            print("[-] Ошибка: GIST_ID или GH_TOKEN не заданы.")
    except Exception as e:
        print(f"[-] Ошибка: {e}")

if __name__ == "__main__":
    main()
