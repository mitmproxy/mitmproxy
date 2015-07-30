import argparse
from libmproxy import web, flow
import tutils
from libmproxy.proxy.server import DummyServer
from libmproxy.proxy import ProxyConfig


def test_web_plugins():
    plugins = web.WebPlugins()
    assert plugins

    # two types: view and action
    assert len(dict(plugins).items()) == 2


def test_web_plugins_views():
    plugins = web.WebPlugins()

    # two types: view and action
    assert len(dict(plugins).items()[1]) == 2
    assert dict(plugins).items()[1][0] == 'view_plugins'
    assert len(dict(plugins).items()[1][1]) == 0

    plugins.register_view('noop',
                          title='Noop View Plugin',
                          transformer=lambda x: x)

    assert len(dict(plugins).items()[1][1]) == 1
    assert len(dict(plugins).items()[0][1]) == 0


def test_web_plugins_actions():
    r = tutils.treq()
    f = tutils.tflow(resp=True)
    s = flow.ServerPlaybackState(
        None,
        [],
        False,
        False,
        None,
        False,
        None,
        False)
    fm = web.WebMaster(DummyServer(ProxyConfig()), web.Options())

    plugins = fm.plugins

    assert len(dict(plugins).items()[0]) == 2
    assert dict(plugins).items()[0][0] == 'action_plugins'
    assert len(dict(plugins).items()[0][1]) == 0

    plugins.register_action('noop',
                            title='noop',
                            options=[{
                                'title': 'nooption',
                                'id': 'nooption',
                                'state': {
                                    'value': 'noop',
                                },
                                'type': 'text',
                            }],
                            actions=[{
                                'title': 'noopaction',
                                'id': 'noopaction',
                                'state': {
                                    'every_flow': True,
                                },
                                'possible_hooks': ['request', 'response'],
                            }
                            ])

    assert len(dict(plugins).items()[0][1]) == 1
    assert len(dict(plugins).items()[1][1]) == 0

    assert f.request.content == "content"

    # now let's try one that should change it
    plugins.register_action('test',
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

    fm.handle_clientconnect(f.client_conn)
    fm.handle_serverconnect(f.server_conn)
    fm.handle_request(f)
    #fm.replay_request(f, run_scripthooks=True)
    #assert f.request.content == 'test'
