import requests

response = requests.post(
    'http://address:22/path',
    data=b'content'
)

print(response.text)
