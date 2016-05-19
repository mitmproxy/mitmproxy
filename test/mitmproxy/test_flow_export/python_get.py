import requests

url = 'http://address/path'

headers = {
    'header': 'qvalue',
    'content-length': '7',
}

response = requests.request(
    method='GET',
    url=url,
    headers=headers,
)

print(response.text)
