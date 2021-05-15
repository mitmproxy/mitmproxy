from pathlib import Path
import os
import glob
import json
import falcon
from  mitmproxy.addons.browserup.har.har_verifications import HarVerifications
from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes


class HealthCheckResource:
    def addon_path(self):
        return "healthcheck"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_get(self, req, resp):
        """Gets the Healthcheck.
        ---
        description: Get the healthcheck
        operationId: healthcheck
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: OK means all is well.
        """
        resp.body = 'OK'
        resp.status = falcon.HTTP_200

class RespondWithHarMixin:
    def respond_with_har(self, resp, har, har_file):
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        resp.body = json.dumps({ "path": har_file.name, "json": har }, ensure_ascii=False)

class VerifyResponseMixin:
    def respond_with_bool(self, resp, bool):
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        resp.body = json.dumps(bool, ensure_ascii=False)

class HarResource(RespondWithHarMixin):
    def apispec(self, spec):
        path = os.path.abspath(os.path.dirname(__file__) + '/../schemas/*.json')
        files = glob.glob(path)
        for filepath in files:
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
                  $ref: "#/components/schemas/Har"
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
        responses:
          200:
            description: The current Har file.
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/Har"
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
                        $ref: "#/components/schemas/CustomHarData"

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
                            $ref: "#/components/schemas/Har"
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
                            $ref: "#/components/schemas/Har"
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


class PresentResource(VerifyResponseMixin):
    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

    def addon_path(self):
        return "verify/present/{name}"

    def apispec(self, spec):
        spec.path(resource=self)


    def on_post(self, req, resp, name):
        """Verifies traffic matching the criteria is present
        ---
        description: Verify at least one matching item is present in the captured traffic
        operationId: verifyPresent
        tags:
          - BrowserUpProxy
        parameters:
            - in: path
              name: name
              description: The unique name for this verification operation
              required: true
              schema:
                type: string
                pattern: /[a-zA-Z0-9_]{4,16}/
        requestBody:
          description: Match criteria to select requests - response pairs for size tests
          required: true
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/MatchCriteria"

        responses:
          200:
            description: The traffic conformed to the time criteria.
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/VerifyResult"
        """
        criteria = req.media
        hv = HarVerifications(self.HarCaptureAddon.har)
        val = hv.present(criteria)
        self.HarCaptureAddon.add_verification_to_har(name, 'present', val)
        self.respond_with_bool(resp, val)

class NotPresentResource(VerifyResponseMixin):
    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

    def addon_path(self):
        return "verify/not_present/{name}"

    def apispec(self, spec):
        spec.path(resource=self)


    def on_post(self, req, resp, name):
        """Verifies traffic matching the criteria Text is not present
        ---
        description: Verify no matching items are present in the captured traffic
        operationId: verifyNotPresent
        tags:
          - BrowserUpProxy
        requestBody:
          description: Match criteria to select requests - response pairs for size tests
          required: true
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/MatchCriteria"
        parameters:
            - in: path
              name: name
              description: The unique name for this verification operation
              required: true
              schema:
                type: string
                pattern: /[a-zA-Z0-9_]{4,16}/
        responses:
          200:
            description: The traffic had no matching items
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/VerifyResult"
        """
        criteria = req.media
        hv = HarVerifications(self.HarCaptureAddon.har)
        val = hv.not_present(criteria)
        self.HarCaptureAddon.add_verification_to_har(name, 'not_present', val)
        self.respond_with_bool(resp, val)


class SizeResource(VerifyResponseMixin):
    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

    def addon_path(self):
        return "verify/size/{size}/{name}"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_post(self, req, resp, size, name):
        """Compares the size of the traffic matching the criteria by comparing it to the passed value
        ---
        description: Verify matching items in the captured traffic meet the size criteria
        operationId: verifySize
        tags:
          - BrowserUpProxy
        parameters:
            - in: path
              name: size
              description: The size used for comparison
              required: true
              schema:
                type: integer
                minimum: 0
            - in: path
              name: name
              description: The unique name for this verification operation
              required: true
              schema:
                type: string
                pattern: /[a-zA-Z0-9_]{4,16}/
        requestBody:
          description: Match criteria to select requests - response pairs for size tests
          required: true
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/MatchCriteria"
        responses:
          200:
            description: The traffic conformed to the size criteria.
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/VerifyResult"
        """
        criteria = req.media
        size_val = int(size)
        hv = HarVerifications(self.HarCaptureAddon.har)
        max_size = hv.get_max(criteria, 'response')
        result = size_val <= max_size
        self.HarCaptureAddon.add_verification_to_har(name, 'size', result)
        self.respond_with_bool(resp, result)

class SLAResource(VerifyResponseMixin):
    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

    def addon_path(self):
        return "verify/sla/{time}/{name}"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_post(self, req, resp, time, name):
        """Verifies compares the traffic matching the criteria using the comparison (less_than)
        ---
        description: Verify each traffic item matching the criteria meets is below SLA time
        operationId: verifySLA
        tags:
          - BrowserUpProxy
        parameters:
            - in: path
              name: time
              description: The time used for comparison
              required: true
              schema:
                type: integer
                minimum: 0
            - in: path
              name: name
              description: The unique name for this verification operation
              required: true
              schema:
                type: string
                pattern: /[a-zA-Z0-9_]{4,16}/
        requestBody:
          description: Match criteria to select requests - response pairs for size tests
          required: true
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/MatchCriteria"
        responses:
          200:
            description: The traffic conformed to the time criteria.
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/VerifyResult"
        """
        criteria = req.media
        time_val = int(time)
        hv = HarVerifications(self.HarCaptureAddon.har)
        val = hv.get_max(criteria, 'time')
        result = time_val <= val
        self.HarCaptureAddon.add_verification_to_har(name, 'sla', val)
        self.respond_with_bool(resp, result)