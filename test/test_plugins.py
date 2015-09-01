import argparse
from libmproxy import script, flow
import tutils
from libmproxy.proxy.server import DummyServer
from libmproxy.proxy import ProxyConfig
import netlib.utils
from netlib import odict
from netlib.http.semantics import CONTENT_MISSING, HDR_FORM_URLENCODED, HDR_FORM_MULTIPART


def test_plugins():
    plugins = flow.Plugins()
    assert plugins

    # two types: view and action
    assert len(dict(plugins).items()) == 2


def test_plugins_views():
    plugins = flow.Plugins()

    # two types: view and action
    assert 'view_plugins' in dict(plugins).keys()

    view_plugins = plugins['view_plugins']
    assert len(view_plugins) == 0

    plugins.register_view('noop',
                          title='Noop View Plugin',
                          transformer=lambda x: x)

    assert len(view_plugins) == 1
    assert view_plugins['noop']['title'] == 'Noop View Plugin'


def test_plugins_actions():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    f = tutils.tflow(req=netlib.tutils.treq(), resp=True)

    plugins = fm.plugins

    assert 'action_plugins' in dict(plugins).keys()
    action_plugins = dict(plugins)['action_plugins']

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

    assert len(action_plugins) == 1

    assert f.request.content == "content"


def test_action_plugin_simple():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    fm.load_script(tutils.test_data.path("scripts/test_plugin.py"))
    f = tutils.tflow(req=netlib.tutils.treq(), resp=True)

    plugins = fm.plugins
    action_plugins = plugins['action_plugins']

    assert len(action_plugins) == 1
    assert f.request.content == 'content'

    fm.handle_clientconnect(f.client_conn)
    fm.handle_serverconnect(f.server_conn)
    fm.handle_request(f)

    assert f.request.content == 'test'
