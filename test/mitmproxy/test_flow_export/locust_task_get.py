    @task()
    def path(self):
        url = self.locust.host + '/path'

        headers = {
            'header': 'qvalue',
            'content-length': '7',
        }

        self.response = self.client.request(
            method='GET',
            url=url,
            headers=headers,
        )
