import requests

url = 'http://address/path'

headers = {
    'content-type': 'application/json',
}

json = {
    "name": "example",
    "email": "example@example.com"
}

response = requests.request(
    method='POST',
    url=url,
    headers=headers,
    json=json,
)

print(response.text)
