import falcon
import _thread

from mitmproxy import ctx

from wsgiref.simple_server import make_server

import os
import json

from pathlib import Path

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from falcon_apispec import FalconPlugin

class BrowserUpAddonsManagerAddOn:
    initialized = False

    def load(self, l):
        ctx.log.info('Loading addons manager add-on...')
        l.add_option(
            "addons_management_port", int, 8088, "REST api management port.",
        )

    def running(self):
        global initialized
        if not self.initialized and self.is_script_loader_initialized():
            ctx.log.info('Scanning for custom add-ons resources...')
            ctx.log.info('Starting falcon REST service...')
            _thread.start_new_thread(self.start_falcon())
            initialized = True


    def is_script_loader_initialized(self):
        script_loader = ctx.master.addons.get("scriptloader")

        for custom_addon in script_loader.addons:
            if len(custom_addon.addons) == 0:
                return False

        return True

    def basic_spec(self, app):
        return APISpec(
            title='BrowserUp Proxy',
            version='1.0.0',
            tags = [{ "name": 'proxy', "description": "BrowserUp Proxy Control API" }],
            info= { "description": "BrowserUp Proxy Control API" },
            openapi_version='3.0.3',
            plugins=[
                FalconPlugin(app),
                MarshmallowPlugin(),
            ],
        )

    def write_spec(self, spec):
        pretty_json = json.dumps(spec.to_dict(), indent=2)
        root = Path(__file__).parent.parent.parent.parent
        schema_path = os.path.join(root, 'browserup-proxy.schema.json')
        f = open(schema_path, 'w')
        f.write(pretty_json)
        f.close()


    def get_resources(self, app, spec):
        addons = ctx.master.addons
        resources = []
        get_resource_fun_name = "get_resource"
        for custom_addon in addons.chain:
            if hasattr(custom_addon, get_resource_fun_name):
                resource = getattr(custom_addon, get_resource_fun_name)()
                resources.append(resource)
                route = "/" + resource.addon_path()
                app.add_route(route, resource)

                if 'apispec' in dir(resource):
                    resource.apispec(spec)

        self.write_spec(spec)
        return resources


    def start_falcon(self):
        app = falcon.API()
        spec = self.basic_spec(app)
        for resource in self.get_resources(app, spec ):
            route = "/" + resource.addon_path() + "/{method_name}"
            print("Adding route: " + route)
            app.add_route(route, resource)

        with make_server('', ctx.options.addons_management_port, app) as httpd:
            print('Starting REST API management on port: {}'.format(ctx.options.addons_management_port))
            httpd.serve_forever()

            #
            # https://marshmallow.readthedocs.io/en/stable/quickstart.html
            # Schema.loads(json_path)

addons = [
    BrowserUpAddonsManagerAddOn()
]