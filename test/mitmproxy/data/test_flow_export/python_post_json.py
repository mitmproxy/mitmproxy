import requests

response = requests.post(
    'http://address:22/path',
    headers={'content-type': 'application/json'},
    json={'email': 'example@example.com', 'name': 'example'}
)

print(response.text)