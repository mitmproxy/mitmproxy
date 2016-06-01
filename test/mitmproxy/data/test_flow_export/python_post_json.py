import requests

url = 'http://address/path'

headers = {
    'content-type': 'application/json',
}


json = {
    u'email': u'example@example.com',
    u'name': u'example',
}


response = requests.request(
    method='POST',
    url=url,
    headers=headers,
    json=json,
)

print(response.text)
