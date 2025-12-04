import requests
import json

# Test simple
url = 'http://localhost:8000/graphql'
query = '{ pattern(id: "42") { id geometry { lat lon } stops { name } } }'

print(f"Testing: {query}")
try:
    r = requests.post(url, json={'query': query})
    print(f"Status: {r.status_code}")
    print(f"Response: {json.dumps(r.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
