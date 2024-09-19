import time
import requests
import json
import os
from urllib.parse import urlparse, parse_qs
import base64
from flask import Flask, request, jsonify
import re

app = Flask(__name__)

# Delta configuration
platoboost = "https://gateway.platoboost.com/a/8?id="
discord_webhook_url = "https://discord.com/api/webhooks/1286007233653641246/vjUsAvEcuyxAzJyGh3VZU2txZfa9FO5H1Ohdb1i2WHYlrrrFv-JMfdbveH8xVsBTiAPI"  # enter your webhook if security check detected

def time_convert(n):
    hours = n // 60
    minutes = n % 60
    return f"{hours} Hours {minutes} Minutes"

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

def sleep(ms):
    time.sleep(ms / 1000)

def get_turnstile_response():
    time.sleep(1)
    return "turnstile-response"

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

# Fluxus configuration
key_regex = r'let content = "([^"]+)";'

def fetch(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch URL: {url}. Error: {e}")

def bypass_link(url):
    try:
        hwid = url.split("HWID=")[-1]
        if not hwid:
            raise Exception("Invalid HWID in URL")

        start_time = time.time()
        endpoints = [
            {
                "url": f"https://flux.li/android/external/start.php?HWID={hwid}",
                "referer": ""
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

        for endpoint in endpoints:
            url = endpoint["url"]
            referer = endpoint["referer"]
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'close',
                'Referer': referer,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x66) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
            }
            response_text = fetch(url, headers)
            if endpoint == endpoints[-1]:
                match = re.search(key_regex, response_text)
                if match:
                    end_time = time.time()
                    time_taken = end_time - start_time
                    return match.group(1), time_taken
                else:
                    raise Exception("Failed to find content key")
    except Exception as e:
        raise Exception(f"Failed to bypass link. Error: {e}")

@app.route('/api/bypass', methods=['GET'])
def bypass():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    if url.startswith("https://flux.li/android/external/start.php?HWID="):
        try:
            content, time_taken = bypass_link(url)
            return jsonify({"key": content, "time_taken": time_taken, "credit": "FeliciaXxx"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        result = delta(url)
        return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
