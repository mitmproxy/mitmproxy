    @task()
    def path(self):
        url = self.locust.host + '/path'

        data = '''content'''

        self.response = self.client.request(
            method='POST',
            url=url,
            data=data,
        )
