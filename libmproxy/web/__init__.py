from __future__ import absolute_import, print_function
import collections
import tornado.ioloop
import tornado.httpserver
import os
import sys
import inspect
from .. import controller, flow, filt
from . import app


class Stop(Exception):
    pass


class WebError(Exception):
    pass


class WebFlowView(flow.FlowView):
    def __init__(self, store):
        super(WebFlowView, self).__init__(store, None)

    def _add(self, f):
        super(WebFlowView, self)._add(f)
        app.ClientConnection.broadcast(
            type="flows",
            cmd="add",
            data=f.get_state(short=True)
        )

    def _update(self, f):
        super(WebFlowView, self)._update(f)
        app.ClientConnection.broadcast(
            type="flows",
            cmd="update",
            data=f.get_state(short=True)
        )

    def _remove(self, f):
        super(WebFlowView, self)._remove(f)
        app.ClientConnection.broadcast(
            type="flows",
            cmd="remove",
            data=f.id
        )

    def _recalculate(self, flows):
        super(WebFlowView, self)._recalculate(flows)
        app.ClientConnection.broadcast(
            type="flows",
            cmd="reset"
        )


class WebState(flow.State):
    def __init__(self):
        super(WebState, self).__init__()
        self.view._close()
        self.view = WebFlowView(self.flows)

        self._last_event_id = 0
        self.events = collections.deque(maxlen=1000)

    def add_event(self, e, level):
        self._last_event_id += 1
        entry = {
            "id": self._last_event_id,
            "message": e,
            "level": level
        }
        self.events.append(entry)
        app.ClientConnection.broadcast(
            type="events",
            cmd="add",
            data=entry
        )

    def clear(self):
        super(WebState, self).clear()
        self.events.clear()
        app.ClientConnection.broadcast(
            type="events",
            cmd="reset",
            data=[]
        )


class Options(object):
    attributes = [
        "app",
        "app_domain",
        "app_ip",
        "anticache",
        "anticomp",
        "client_replay",
        "eventlog",
        "keepserving",
        "kill",
        "intercept",
        "no_server",
        "refresh_server_playback",
        "rfile",
        "scripts",
        "showhost",
        "replacements",
        "rheaders",
        "setheaders",
        "server_replay",
        "stickycookie",
        "stickyauth",
        "stream_large_bodies",
        "verbosity",
        "wfile",
        "nopop",
        "filtstr",

        "wdebug",
        "wport",
        "wiface",
    ]

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.attributes:
            if not hasattr(self, i):
                setattr(self, i, None)


class WebPlugins(object):
    def __init__(self):
        self._view_plugins = {}
        self._action_plugins = {}

    def __iter__(self):
        for plugin_type in ('view_plugins', 'action_plugins'):
            yield (plugin_type, getattr(self, '_' + plugin_type))

    def get_option_value(self, action_plugin_id, option_id):
        plugin = self._action_plugins.get(action_plugin_id)
        if not plugin:
            raise WebError("No action plugin %s" % action_plugin_id)

        if not plugin.get('options'):
            raise WebError("No action plugin %s with option %s" % (action_plugin_id, option_id))

        for option in plugin['options']:
            if option.get('id') == option_id:
                return str(option['state']['value'].encode('utf-8'))

        raise WebError("No action plugin %s with option %s" % (action_plugin_id, option_id))

    def register_view(self, id, **kwargs):
        if self._view_plugins.get(id):
            raise WebError("Duplicate view registration for %s" % (id, ))

        if not kwargs.get('transformer') or not \
                callable(kwargs['transformer']):
            raise WebError("No transformer method passed for view %s" % (id, ))

        script_path = inspect.stack()[1][1]

        self._view_plugins[id] = {}
        self._view_plugins[id]['title'] = kwargs.get('title') or id
        self._view_plugins[id]['transformer'] = kwargs['transformer']
        self._view_plugins[id]['script_path'] = script_path

        print("Registered view plugin %s form script %s" % (kwargs['title'], script_path))

    def register_action(self, id, **kwargs):
        if self._action_plugins.get(id):
            raise WebError("Duplicate action registration for %s" % (id, ))

        script_path = inspect.stack()[1][1]

        self._action_plugins[id] = {}
        self._action_plugins[id]['title'] = kwargs.get('title') or id
        self._action_plugins[id]['script_path'] = script_path
        self._action_plugins[id]['actions'] = kwargs.get('actions')
        self._action_plugins[id]['options'] = kwargs.get('options')

        for action in self._action_plugins[id]['actions']:
            if not action.get('state'):
                action['state'] = {}

            if not action['state'].get('every_flow'):
                action['state']['every_flow'] = False

            if not action.get('possible_hooks'):
                action['possible_hooks'] = []

        print("Registered action plugin %s from script %s" % (kwargs['title'], script_path))


class WebMaster(flow.FlowMaster):
    def __init__(self, server, options, outfile=sys.stdout):
        self.outfile = outfile
        self.options = options
        self.plugins = None
        super(WebMaster, self).__init__(server, WebState())
        self.app = app.Application(self, self.options.wdebug)
        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except flow.FlowReadError as v:
                self.add_event(
                    "Could not read flow file: %s" % v,
                    "error"
                )

        if options.filtstr:
            self.filt = filt.parse(options.filtstr)
        else:
            self.filt = None

        if options.outfile:
            path = os.path.expanduser(options.outfile[0])
            try:
                f = file(path, options.outfile[1])
                self.start_stream(f, self.filt)
            except IOError as v:
                raise WebError(v.strerror)

        self.plugins = WebPlugins()

        scripts = options.scripts or []
        for command in scripts:
            err = self.load_script(command)
            if err:
                raise WebError(err)

        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except flow.FlowReadError as v:
                self.add_event("Flow file corrupted.", "error")
                raise WebError(v)

        if self.options.app:
            self.start_app(self.options.app_host, self.options.app_port)

    def tick(self):
        flow.FlowMaster.tick(self, self.masterq, timeout=0)

    def run(self):  # pragma: no cover
        self.server.start_slave(
            controller.Slave,
            controller.Channel(self.masterq, self.should_exit)
        )
        iol = tornado.ioloop.IOLoop.instance()

        http_server = tornado.httpserver.HTTPServer(self.app)
        http_server.listen(self.options.wport)

        tornado.ioloop.PeriodicCallback(self.tick, 5).start()
        try:
            iol.start()
        except (Stop, KeyboardInterrupt):
            self.shutdown()

    def _process_flow(self, f):
        if self.state.intercept and self.state.intercept(
                f) and not f.request.is_replay:
            f.intercept(self)
        else:
            f.reply()

    def _handle_plugin_hooks(self, f, hook):
        if self.plugins:
            for plugin_type, plugin_dicts in dict(self.plugins).items():
                if plugin_type != 'action_plugins':
                    continue

                for _plugin_id, plugin_dict in plugin_dicts.items():
                    plugin = plugin_dict

                    for action in plugin_dict['actions']:
                        if hook in action['possible_hooks']:
                            if action['state']['every_flow']:
                                found = False
                                script = None
                                for _script in self.scripts:
                                    if _script.args[0] != plugin['script_path']:
                                        continue

                                    found = True
                                    script = _script
                                    break

                                if not found:
                                    self._process_flow(f)
                                    return

                                self.add_event("Running on every %s: %s" % (hook, action['id']), "debug")
                                self._run_single_script_hook(script, action['id'], f)

    def handle_request(self, f):
        self._handle_plugin_hooks(f, 'request')

        super(WebMaster, self).handle_request(f)

        self._process_flow(f)

    def handle_response(self, f):
        self._handle_plugin_hooks(f, 'response')

        super(WebMaster, self).handle_response(f)

        self._process_flow(f)

    def handle_error(self, f):
        super(WebMaster, self).handle_error(f)
        self._process_flow(f)

    def add_event(self, e, level="info"):
        super(WebMaster, self).add_event(e, level)
        self.state.add_event(e, level)
