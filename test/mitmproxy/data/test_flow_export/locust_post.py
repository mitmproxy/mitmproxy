from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):
    def on_start(self):
        ''' on_start is called when a Locust start before any task is scheduled '''
        self.path()

    @task()
    def path(self):
        url = self.locust.host + '/path'

        data = '''content'''

        self.response = self.client.request(
            method='POST',
            url=url,
            data=data,
        )

    ### Additional tasks can go here ###


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 3000
