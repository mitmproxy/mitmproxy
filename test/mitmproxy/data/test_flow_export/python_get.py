import requests

response = requests.get(
    'http://address:22/path',
    params={'a': ['foo', 'bar'], 'b': 'baz'},
    headers={'header': 'qvalue'}
)

print(response.text)