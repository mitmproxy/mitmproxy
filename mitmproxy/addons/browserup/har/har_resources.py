import marshmallow
from marshmallow import Schema, fields
from pathlib import Path
import os
import glob
import json
import falcon
from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes

# HTTP Falcon API

class RespondWithHarMixin:
    def respond_with_har(resp, har, har_file):
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        resp.body = json.dumps({ "path": har_file.name, "json": har }, ensure_ascii=False)


class HarResource(RespondWithHarMixin):
    def apispec(self, spec):
        here = os.path.abspath(os.path.dirname(__file__))
        for filepath in glob.iglob(here + '/schemas/*.json'):
            filename = Path(filepath).resolve().stem
            with open(filepath, encoding='utf-8') as f:
                schema = json.load(f)
            spec.components.schema(filename, component=schema)
            spec.path(resource=self)

    def addon_path(self):
        return "har"

    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

    def on_get(self, req, resp):
        """Get the Har.
        ---
        description: Get the current HAR.
        operationId: getHarLog
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: The current Har file.
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/har"
        """
        clean_har = req.get_param('cleanHar') == 'true'
        har = self.HarCaptureAddon.get_har(clean_har)

        filtered_har = self.HarCaptureAddon.filter_har_for_report(har)
        har_file = self.HarCaptureAddon.save_har(filtered_har)

        if clean_har:
            self.HarCaptureAddon.mark_har_entries_submitted(har)
        self.respond_with_har(resp, har, har_file)


    def on_put(self, req, resp):
        """Starts or resets the Har capture session, returns the last session.
        ---
        description: Starts a fresh HAR capture session.
        operationId: resetHarLog
        tags:
            - BrowserUpProxy
        requestBody:

        responses:
            200:
                description: The current Har file.
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/CustomHarData"
        """
        page_ref = req.get_param('pageRef')
        page_title = req.get_param('pageTitle')

        har = self.HarCaptureAddon.new_har(page_ref, page_title, True)
        har_file = self.HarCaptureAddon.save_har(har)
        self.respond_with_har(resp, har, har_file)

class HarPageResource(RespondWithHarMixin):

    def __init__(self, HarCaptureAddon):
        self.HarCaptureAddon = HarCaptureAddon

    def apispec(self, spec):
        spec.path(resource=self)

    def addon_path(self):
        return "har/page"

    def on_put(self, req, resp):
        """Adds _custom fields to the HAR file.
        ---
        description: Add custom fields to the current HAR.
        operationId: addCustomHarFields
        tags:
            - BrowserUpProxy
        requestBody:
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/CustomData"

        responses:
            204:
                description: The custom fields were added to the HAR.
        """
        page_ref = req.get_param('pageRef')
        page_title = req.get_param('pageTitle')

        har = self.HarCaptureAddon.new_page(page_ref, page_title)
        har_file = self.HarCaptureAddon.save_har(har)
        self.respond_with_har(resp, har, har_file)


    def on_post(self, req, resp):
        """Creates a new Har Page to begin capturing to, with a new title
        ---
        description: Starts a fresh HAR Page in the current active HAR
        operationId: setHarPage
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: The current Har file.
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/har"
        """
        page_ref = req.get_param('pageRef')
        page_title = req.get_param('pageTitle')

        har = self.HarCaptureAddon.new_page(page_ref, page_title)
        har_file = self.HarCaptureAddon.save_har(har)
        self.respond_with_har(resp, har, har_file)

class HarCaptureTypesResource():
    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

    def addon_path(self):
        return "har/capture_types"

    def on_put(self, req, resp):
        """Sets the Har Capture types to capture
        ---
        description: Sets the types the HAR will capture
        operationId: setHarCaptureTypes
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: The current Har file.
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/har"
        """
        capture_types = req.get_param('captureTypes')
        capture_types = capture_types.strip("[]").split(",")

        capture_types_parsed = []
        for ct in capture_types:
            ct = ct.strip(" ")
            if ct == "":
                break

            if not hasattr(HarCaptureTypes, ct):
                resp.status = falcon.HTTP_400
                resp.body = "Invalid HAR Capture type"
                return

            capture_types_parsed.append(HarCaptureTypes[ct])

        self.HarCaptureAddon.har_capture_types = capture_types_parsed
        resp.status = falcon.HTTP_200



import marshmallow
from marshmallow import Schema, fields

class VerifyBase():
    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

class PresentResource(VerifyBase):
    def addon_path(self):
        return "present"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_post(self, req, resp):
        """Verifies traffic matching the criteria Text is present
        ---
        description: Verify at least one matching item is present in the captured traffic
        operationId: present
        tags:
            - BrowserUpProxy
        requestBody:

        responses:
            204:
                description: The traffic matching the match criteria is present
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/MatchCriteria"
        """

class NotPresentResource(VerifyBase):
    def addon_path(self):
        return "not_present"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_post(self, req, resp):
        """Verifies traffic matching the criteria Text  is not present
        ---
        description: Verify no matching item are present in the captured traffic
        operationId: not_present
        tags:
            - BrowserUpProxy
        requestBody:

        responses:
            204:
                description: The traffic matching the match criteria is present
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/MatchCriteria"
        """

class BelowResource(VerifyBase):
    def addon_path(self):
        return "less_than"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_post(self, req, resp):
        """Verifies every value in question is less than the max
        ---
        description: Verify every value in question is less than the max
        operationId: present
        tags:
            - BrowserUpProxy
        requestBody:

        responses:
            204:
                description: The traffic matching the match criteria is present
                content:
                    application/json:
                        schema:
                            $ref: "#/components/schemas/MatchCriteria"
        """


# verify.present(content="foo.com", status=200)
# verify.present(url='cnn.com', websocket_message ='Hello there')
# verify.not_present
# verify.max(response_time: 2.0, )
# verify.max(onload,_2)
# verify.total()
# verify.count()


class MatchCriteriaSchema(Schema):
    status_code = fields.Str(optional=True,  description="Status code to match. Strings of format 2xx or 4xx indicate anything in range")
    url = fields.Str(optional=True, description="Request URL regexp to match")
    content = fields.Str(optional=True, description="Body URL regexp content to match")
    request_header = fields.Str(optional=True, description="Header URL regexp text to match")
    response_header = fields.Str(optional=True, description="Response Header text to match")
    websocket_message = fields.Str(optional=True, description="Websocket message text to match")
    step = fields.Str(optional=True, description="current|all")
    content_type = fields.Str(optional=True, description="Websocket message text to match")

class PageCriteria:
    onload = fields.Int(optional=True, description="Maximum milliseconds to pass")
    first_contentful_paint = fields.Int(optional=True, description="Maximum milliseconds to pass")
    oncontentload = fields.Int(optional=True, description="Maximum milliseconds to pass")

class UrlCriteria:
    time = fields.Int(optional=True, description="Maximum milliseconds to pass")

class AssetCriteria:
    max_size = fields.Int(optional=True, description="Maximum size")
    total_size  = fields.Int(optional=True, description="Total size size")

class HarPageSchema(Schema):
    title = fields.Str(required=True,  description="Page title")
    page_id = fields.Str(optional=True, description="Internal unique ID for har - auto-populated")

class CustomHarDataSchema(Schema):
    page = fields.Dict(required=True,  description="Counters for the page section of the current page")