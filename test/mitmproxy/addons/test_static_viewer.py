import json
from unittest import mock

from mitmproxy.test import taddons
from mitmproxy.test import tflow

from mitmproxy import flowfilter
from mitmproxy.tools.web.app import flow_to_json

from mitmproxy.addons import static_viewer
from mitmproxy.addons import save


def test_save_static(tmpdir):
    tmpdir.mkdir('static')
    static_viewer.save_static(tmpdir)
    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join('index.html').check(file=1)
    assert tmpdir.join('static/static.js').read() == 'MITMWEB_STATIC = true;'


def test_save_filter_help(tmpdir):
    static_viewer.save_filter_help(tmpdir)
    f = tmpdir.join('/filter-help.json')
    assert f.check(file=1)
    assert f.read() == json.dumps(dict(commands=flowfilter.help))


def test_save_flows(tmpdir):
    flows = [tflow.tflow(req=True, resp=None), tflow.tflow(req=True, resp=True)]
    static_viewer.save_flows(tmpdir, flows)
    assert tmpdir.join('flows.json').check(file=1)
    assert tmpdir.join('flows.json').read() == json.dumps([flow_to_json(f) for f in flows])


@mock.patch('mitmproxy.ctx.log')
def test_save_flows_content(ctx, tmpdir):
    flows = [tflow.tflow(req=True, resp=None), tflow.tflow(req=True, resp=True)]
    with mock.patch('time.time', mock.Mock(side_effect=[1, 2, 2] * 4)):
        static_viewer.save_flows_content(tmpdir, flows)
    flows_path = tmpdir.join('flows')
    assert len(flows_path.listdir()) == len(flows)
    for p in flows_path.listdir():
        assert p.join('request').check(dir=1)
        assert p.join('response').check(dir=1)
        assert p.join('request/_content').check(file=1)
        assert p.join('request/content').check(dir=1)
        assert p.join('response/_content').check(file=1)
        assert p.join('response/content').check(dir=1)
        assert p.join('request/content/Auto.json').check(file=1)
        assert p.join('response/content/Auto.json').check(file=1)


def test_static_viewer(tmpdir):
    s = static_viewer.StaticViewer()
    sa = save.Save()
    with taddons.context() as tctx:
        sa.save([tflow.tflow(resp=True)], str(tmpdir.join('foo')))
        tctx.master.addons.add(s)
        tctx.configure(s, web_static_viewer=str(tmpdir), rfile=str(tmpdir.join('foo')))
        assert tmpdir.join('index.html').check(file=1)
        assert tmpdir.join('static').check(dir=1)
        assert tmpdir.join('flows').check(dir=1)
