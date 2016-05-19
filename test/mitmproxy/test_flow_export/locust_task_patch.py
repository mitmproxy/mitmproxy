    @task()
    def path(self):
        url = self.locust.host + '/path'

        headers = {
            'header': 'qvalue',
            'content-length': '7',
        }

        params = {
            'query': 'param',
        }

        data = '''content'''

        self.response = self.client.request(
            method='PATCH',
            url=url,
            headers=headers,
            params=params,
            data=data,
        )
