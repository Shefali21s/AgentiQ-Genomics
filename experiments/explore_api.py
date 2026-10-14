import requests
import re

BASE_URL = "http://geco.deib.polimi.it/gmql-rest"

guest_resp = requests.get(f"{BASE_URL}/guest")
token = re.search(r"<authToken>Some\((.*?)\)</authToken>", guest_resp.text).group(1)
headers = {"X-AUTH-TOKEN": token}

# Try /datasets with explicit query parameters some GMQL deployments require
for url in [
    f"{BASE_URL}/datasets",
    f"{BASE_URL}/datasets?owner=public",
    f"{BASE_URL}/datasets/public",
]:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"{url} -> {r.status_code}")
    print(r.text[:300])
    print("---")
    