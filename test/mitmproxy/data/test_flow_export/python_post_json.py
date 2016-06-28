import requests

url = 'http://address/path'

headers = {
    'content-type': 'application/json',
}


json = {
    'email': 'example@example.com',
    'name': 'example',
}


response = requests.request(
    method='POST',
    url=url,
    headers=headers,
    json=json,
)

print(response.text)
