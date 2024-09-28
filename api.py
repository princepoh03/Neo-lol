import time
import requests
import base64
import re
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify
import asyncio
from aiohttp import ClientSession

app = Flask(__name__)

# Fluxus configuration
key_regex_1 = r'let content = "([^"]+)";'
key_regex_2 = r'class="card-key" id="key" value="([^"]+)"'

async def fetch(session, url, referer):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'close',
        'Referer': referer,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    async with session.get(url, headers=headers) as response:
        content = await response.text()
        if response.status != 200:
            return None, response.status, content
        return content, response.status, None

async def process_link():
    endpoints = [
        {
            "url": "https://getkey.relzscript.xyz/redirect.php?hwid=12627128828282272",
            "referer": "https://loot-links.com"
        },
        {
            "url": "https://getkey.relzscript.xyz/check1.php",
            "referer": "https://linkvertise.com"
        },
        {
            "url": "https://getkey.relzscript.xyz/check2.php",
            "referer": "https://linkvertise.com"
        },
        {
            "url": "https://getkey.relzscript.xyz/check3.php",
            "referer": "https://linkvertise.com"
        },
        {
            "url": "https://getkey.relzscript.xyz/finished.php",
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

            if i == len(endpoints) - 1:
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
def bypass():
    url = request.args.get("url")
    if url.startswith("https://flux.li/android/external/start.php?HWID="):
        try:
            start_time = time.time()
            result = asyncio.run(process_link())
            end_time = time.time()
            result['execution_time'] = end_time - start_time
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "Invalid URL for bypass."}), 400

if __name__ == "__main__":
    app.run(debug=True)
