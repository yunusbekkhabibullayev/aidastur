import requests, json, sys
url = 'http://127.0.0.1:8000/api/overview'
payload = {'text': "O'zbekiston poytaxti", 'language': 'uz'}
try:
    r = requests.post(url, json=payload, timeout=10)
    print('Status:', r.status_code)
    print('Response:', r.text)
except Exception as e:
    print('Error:', e)
    sys.exit(1)

