    @task()
    def path(self):
        url = self.locust.host + '/path'

        headers = {
            'header': 'qvalue',
            'content-length': '7',
        }

        params = {
            'a': ['foo', 'bar'],
            'b': 'baz',
        }

        self.response = self.client.request(
            method='GET',
            url=url,
            headers=headers,
            params=params,
        )
