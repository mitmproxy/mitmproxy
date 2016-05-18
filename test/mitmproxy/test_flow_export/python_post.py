import requests

url = 'http://address/path'

data = '''content'''

response = requests.request(
    method='POST',
    url=url,
    data=data,
)

print(response.text)
