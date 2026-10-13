import os, json, requests

BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
HEADERS = {"Authorization": f"Bearer {os.environ['GEMINI_API_KEY']}"}
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

# Step 1: list the models your key can use (look for "lite")
r = requests.get(f"{BASE}/models", headers=HEADERS, timeout=60)
print("models status:", r.status_code)
if r.status_code == 200:
    ids = [m["id"] for m in r.json().get("data", [])]
    print([i for i in ids if "lite" in i])

# Step 2: one tool-calling request
body = {
    "model": MODEL,
    "temperature": 0,
    "messages": [{"role": "user",
                  "content": "Which datasets use the hg38 assembly?"}],
    "tools": [{
        "type": "function",
        "function": {
            "name": "list_datasets",
            "description": "List genomic datasets, optionally filtered by assembly.",
            "parameters": {
                "type": "object",
                "properties": {"assembly": {"type": "string",
                                            "enum": ["hg19", "hg38"]}},
                "required": []
            }
        }
    }],
    "tool_choice": "auto"
}
r = requests.post(f"{BASE}/chat/completions", headers=HEADERS, json=body, timeout=60)
print("chat status:", r.status_code)
if r.status_code != 200:
    print(r.text); raise SystemExit
msg = r.json()["choices"][0]["message"]
print(json.dumps(msg.get("tool_calls"), indent=2))