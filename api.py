import time
import requests
import re
import asyncio
from flask import Flask, request, jsonify
from aiohttp import ClientSession

app = Flask(__name__)

# Regular expression to extract key from the content
fluxus_key_regex = r'let content = "([^"]+)"'  # Updated regex for Fluxus
relz_key_regex = r'Relz[^"\s]*'  # Updated regex for Relz

def fetch(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch URL: {url}. Error: {e}")

def bypass_fluxus(url):
    try:
        hwid = url.split("HWID=")[-1]
        if not hwid:
            raise Exception("Invalid HWID in URL")

        start_time = time.time()
        flux_url = f"https://flux.li/android/external/start.php?HWID={hwid}"

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'close',
            'Referer': 'https://linkvertise.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x66) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }

        response_text = fetch(flux_url, headers)
        match = re.search(fluxus_key_regex, response_text)
        if match:
            end_time = time.time()
            time_taken = end_time - start_time
            return match.group(1), time_taken
        else:
            raise Exception("Failed to find content key")
    except Exception as e:
        raise Exception(f"Failed to bypass link. Error: {e}")

async def fetch_relz(session, url, referer):
    headers = {
        "Referer": referer,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    async with session.get(url, headers=headers) as response:
        content = await response.text()
        if response.status != 200:
            return None, response.status, content
        return content, response.status, None

async def process_relz(url):
    referer = "https://linkvertise.com"
    endpoints = [
        {"url": url, "referer": referer},
        {"url": "https://getkey.relzscript.xyz/check1.php", "referer": referer},
        {"url": "https://getkey.relzscript.xyz/check2.php", "referer": referer},
        {"url": "https://getkey.relzscript.xyz/check3.php", "referer": referer},
        {"url": "https://getkey.relzscript.xyz/finished.php", "referer": referer}
    ]
    
    async with ClientSession() as session:
        for i, endpoint in enumerate(endpoints):
            content, status, error_content = await fetch_relz(session, endpoint["url"], endpoint["referer"])
            if error_content:
                return {
                    "status": "error",
                    "message": f"Failed to bypass at step {i} | Status code: {status}",
                    "content": error_content
                }

            if i == len(endpoints) - 1:
                match = re.search(relz_key_regex, content)
                if match:
                    return {
                        "status": "success",
                        "key": match.group(0)
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Bypass not successful! No key found.",
                        "content": content
                    }

@app.route("/api/fluxus")
def fluxus_bypass():
    url = request.args.get("url")
    if url.startswith("https://flux.li/android/external/start.php?HWID="):
        try:
            content, time_taken = bypass_fluxus(url)
            return jsonify({"key": content, "time_taken": time_taken, "credit": "FeliciaXxx"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Invalid Fluxus URL"}), 400

@app.route("/api/relz")
def relz_endpoint():
    url = request.args.get('url')
    if not url:
        return jsonify({"status": "error", "message": "Missing 'url' parameter."}), 400

    start_time = time.time()
    result = asyncio.run(process_relz(url))
    end_time = time.time()
    execution_time = end_time - start_time
    result['execution_time'] = execution_time

    return jsonify(result)

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the Fluxus and Relz Bypass API"})

if __name__ == "__main__":
    app.run(debug=True)
