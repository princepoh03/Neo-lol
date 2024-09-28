import time
import requests
import base64
import re
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify
import asyncio
from aiohttp import ClientSession

app = Flask(__name__)

# Delta configuration
platoboost = "https://gateway.platoboost.com/a/8?id="
discord_webhook_url = "https://discord.com/api/webhooks/1286007233653641246/vjUsAvEcuyxAzJyGh3VZU2txZfa9FO5H1Ohdb1i2WHYlrrrFv-JMfdbveH8xVsBTiAPI"

# Common headers
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'DNT': '1',
    'Connection': 'close',
    'Referer': 'https://linkvertise.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x66) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

# Time conversion function
def time_convert(n):
    hours = n // 60
    minutes = n % 60
    return f"{hours} Hours {minutes} Minutes"

# Discord webhook
def send_discord_webhook(link):
    payload = {
        "embeds": [{
            "title": "Security Check!",
            "description": f"**Please solve the Captcha**: [Open]({link})",
            "color": 5763719
        }]
    }
    try:
        response = requests.post(discord_webhook_url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        print(f"ERROR: {error}")

# Sleep utility
def sleep(ms):
    time.sleep(ms / 1000)

# Turnstile response simulation
def get_turnstile_response():
    time.sleep(1)
    return "turnstile-response"

# Delta bypass
def delta(url):
    start_time = time.time()
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        id = query_params.get('id', [None])[0]

        if not id:
            raise ValueError("Invalid URL: 'id' parameter is missing")

        response = requests.get(f"https://api-gateway.platoboost.com/v1/authenticators/8/{id}")
        response.raise_for_status()
        already_pass = response.json()

        if 'key' in already_pass:
            time_left = time_convert(already_pass['minutesLeft'])
            return {
                "status": "success",
                "key": already_pass['key'],
                "time_left": time_left
            }

        captcha = already_pass.get('captcha')

        if captcha:
            response = requests.post(
                f"https://api-gateway.platoboost.com/v1/sessions/auth/8/{id}",
                json={
                    "captcha": get_turnstile_response(),
                    "type": "Turnstile"
                }
            )
        else:
            response = requests.post(
                f"https://api-gateway.platoboost.com/v1/sessions/auth/8/{id}",
                json={}
            )

        if response.status_code != 200:
            security_check_link = f"{platoboost}{id}"
            send_discord_webhook(security_check_link)
            raise Exception("Security Check, Notified on Discord!")

        loot_link = response.json()
        sleep(1000)
        decoded_lootlink = requests.utils.unquote(loot_link['redirect'])
        parsed_loot_url = urlparse(decoded_lootlink)
        r_param = parse_qs(parsed_loot_url.query)['r'][0]
        decoded_base64 = base64.b64decode(r_param).decode('utf-8')
        tk = parse_qs(urlparse(decoded_base64).query)['tk'][0]
        sleep(5000)

        response = requests.put(f"https://api-gateway.platoboost.com/v1/sessions/auth/8/{id}/{tk}")
        response.raise_for_status()

        response_plato = requests.get(f"https://api-gateway.platoboost.com/v1/authenticators/8/{id}")
        pass_info = response_plato.json()

        if 'key' in pass_info:
            time_left = time_convert(pass_info['minutesLeft'])
            execution_time = time.time() - start_time
            return {
                "status": "success",
                "key": pass_info['key'],
                "time taken": f"{execution_time:.2f} seconds"
            }

    except Exception as error:
        execution_time = time.time() - start_time
        return {
            "status": "error",
            "error": "An issue occurred, please check the logs.",
            "time taken": f"{execution_time:.2f} seconds"
        }

# Async HTTP requests for Fluxus bypass
key_regex_1 = r'let content = "([^"]+)";'  # Original regex
key_regex_2 = r'class="card-key" id="key" value="([^"]+)"'  # New regex

async def fetch(session, url, referer):
    headers["Referer"] = referer
    async with session.get(url, headers=headers) as response:
        content = await response.text()
        if response.status != 200:
            return None, response.status, content
        return content, response.status, None

async def process_link(hwid):
    endpoints = [
        {
            "url": f"https://flux.li/android/external/start.php?HWID={hwid}",
            "referer": "https://linkvertise.com"
        },
        {
            "url": "https://flux.li/android/external/check1.php?hash={hash}",
            "referer": "https://linkvertise.com"
        },
        {
            "url": "https://flux.li/android/external/main.php?hash={hash}",
            "referer": "https://linkvertise.com"
        }
    ]
    
    async with ClientSession() as session:
        for i, endpoint in enumerate(endpoints):
            url = endpoint["url"]
            referer = endpoint["referer"]
            content, status, error_content = await fetch(session, url, referer)
            if error_content:
                return {
                    "status": "error",
                    "message": f"Failed to bypass at step {i} | Status code: {status}",
                    "content": error_content
                }

            if i == len(endpoints) - 1:  # End of the bypass
                match = re.search(key_regex_1, content)
                if not match:
                    match = re.search(key_regex_2, content)
                
                if match:
                    return {
                        "status": "success",
                        "key": match.group(1)
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Bypass not successful! No key found.",
                        "content": content
                    }

@app.route("/")
def home():
    return jsonify({"message": "Invalid Endpoint"})

@app.route("/api/bypass")
async def bypass():
    url = request.args.get("url")
    if url.startswith("https://flux.li/android/external/start.php?HWID="):
        hwid = url.split("HWID=")[-1]
        try:
            result = await process_link(hwid)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        result = delta(url)
        return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
