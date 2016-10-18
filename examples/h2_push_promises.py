import netlib


def h2_push_promise(event):
    headers = netlib.http.Headers([[k, v] for k, v in event.headers])
    method = headers[':method']
    path = headers[':path']
    print("PUSH_PROMISE received: {} {}".format(method, path))
