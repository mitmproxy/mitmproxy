from a_helper import parser

var = 0


def replace_with_test(context, flow):
    flow.request.content = 'test'


def start(ctx, argv):
    global var
    var = parser.parse_args(argv[1:]).var
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


def here(ctx):
    global var
    var += 1
    return var


def errargs():
    pass
