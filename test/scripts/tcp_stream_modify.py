def tcp_message(ctx, tm):
    if tm.sender == tm.server_conn:
        tm.message = tm.message.replace("foo", "bar")
