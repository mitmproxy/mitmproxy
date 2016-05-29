from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):
    def on_start(self):
        ''' on_start is called when a Locust start before any task is scheduled '''
        self.path()

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

    ### Additional tasks can go here ###


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 3000
