import requests
from app.mcp_server import widget_url

url = widget_url()
print("widget_url", url)
try:
    r = requests.get(url, timeout=5)
    print("status", r.status_code)
    print(r.headers)
    print(r.text[:200])
except Exception as e:
    print("error fetching widget:", e)
