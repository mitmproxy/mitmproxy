import falcon
import _thread

from mitmproxy import ctx

from wsgiref.simple_server import make_server

import re
import json

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from falcon_apispec import FalconPlugin
from marshmallow import Schema, fields

#class BlockList(Schema):
#    urlPattern = fields.Str(required=True)
#    statusCode = fields.Str(required=True)
#    httpMethodPattern = fields.Str(required=True)


#regex - A comma separated list of regular expressions.
#status - The HTTP status code to return for URLs that do not match the whitelist.

from marshmallow import Schema, fields

class AllowList(Schema):
    urlPattern = fields.Str(required=True)
    statusCode = fields.Str(required=True)

class BuAddonsManagerAddOn:
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
            resources = self.get_resources()
            ctx.log.info('Found resources:')
            for r in resources:
                ctx.log.info('  - ' + str(r.__class__))
            ctx.log.info('Starting falcon REST service...')
            _thread.start_new_thread(self.start_falcon, tuple([resources]))
            initialized = True


    def is_script_loader_initialized(self):
        script_loader = ctx.master.addons.get("scriptloader")

        for custom_addon in script_loader.addons:
            if len(custom_addon.addons) == 0:
                return False

        return True


    def get_resources(self):
        addons = ctx.master.addons
        resources = []
        get_resource_fun_name = "get_resource"

        for custom_addon in addons.chain:
            if hasattr(custom_addon, get_resource_fun_name):
                resources.append(getattr(custom_addon, get_resource_fun_name)())
            if 'add_apispec' in dir(custom_addon):
                # Register entities and paths
                custom_addon.add_apispec(spec)

        return resources


    def start_falcon(self, resources):
        app = falcon.API()
        for resource in resources:
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
    BuAddonsManagerAddOn()
]