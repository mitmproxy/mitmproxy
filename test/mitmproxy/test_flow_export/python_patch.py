import requests

url = 'http://address/path'

headers = {
    'header': 'qvalue',
    'content-length': '7',
}

params = {
    'query': 'param',
}

data = '''content'''

response = requests.request(
    method='PATCH',
    url=url,
    headers=headers,
    params=params,
    data=data,
)

print(response.text)
