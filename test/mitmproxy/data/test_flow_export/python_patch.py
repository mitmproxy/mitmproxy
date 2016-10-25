import requests

response = requests.patch(
    'http://address:22/path',
    params=[('query', 'param')],
    headers={'header': 'qvalue'},
    data=b'content'
)

print(response.text)