def replace_with_test(context, flow):
    flow.request.content = 'test'


def start(ctx, argv):
    ctx.plugins.register_action('test',
                                title='test',
                                actions=[{
                                    'title': 'test',
                                    'id': 'replace_with_test',
                                    'state': {
                                        'every_flow': True,
                                    },
                                    'possible_hooks': ['request', 'response'],
                                }
                                ])
