import requests

url = 'http://address/path'

headers = {
    'header': 'qvalue',
    'content-length': '7',
}

params = {
    'a': ['foo', 'bar'],
    'b': 'baz',
}

response = requests.request(
    method='GET',
    url=url,
    headers=headers,
    params=params,
)

print(response.text)
