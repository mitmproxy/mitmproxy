from pathlib import Path
import os
import glob
import json
import falcon
from mitmproxy.addons.browserup.har.har_verifications import HarVerifications
from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes

from mitmproxy.addons.browserup.har.har_schemas import ErrorSchema, CounterSchema, MatchCriteriaSchema
from marshmallow import ValidationError


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
        resp.content_type = falcon.MEDIA_TEXT
        resp.status = falcon.HTTP_200


class RespondWithHarMixin:
    def respond_with_har(self, resp, har, har_file):
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        resp.body = json.dumps(har, ensure_ascii=False)


class ValidateMatchCriteriaMixin:
    def respond_with_error_on_invalid_criteria(self, req, resp):
        try:
            criteria = req.media
            MatchCriteriaSchema().load(criteria)
        except ValidationError as err:
            resp.content_type = falcon.MEDIA_JSON
            raise falcon.HTTPError(falcon.HTTP_422, json.dumps({'error': err.messages}, ensure_ascii=False))


class VerifyResponseMixin:
    def respond_with_bool(self, resp, bool):
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        resp.body = json.dumps({"result": bool}, ensure_ascii=False)


class NoEntriesResponseMixin:
    def respond_with_no_entries_error(self, resp, bool):
        resp.status = falcon.HTTP_500
        resp.content_type = falcon.MEDIA_JSON
        resp.body = json.dumps({"error": 'No traffic entries are present! Is the proxy setup correctly?', }, ensure_ascii=False)


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
        page_title = req.get_param('title')

        har = self.HarCaptureAddon.new_har(page_title)
        har_file = self.HarCaptureAddon.save_har(har)
        self.respond_with_har(resp, har, har_file)


class HarPageResource(RespondWithHarMixin):

    def __init__(self, HarCaptureAddon):
        self.HarCaptureAddon = HarCaptureAddon

    def apispec(self, spec):
        spec.path(resource=self)

    def addon_path(self):
        return "har/page"

    def on_post(self, req, resp):
        """Creates a new Har Page to begin capturing to, with a new title
        ---
        description: Starts a fresh HAR Page (Step) in the current active HAR to group requests.
        operationId: newPage
        parameters:
            - in: path
              name: title
              description: The unique title for this har page/step.
              required: true
              schema:
                type: string
                pattern: /[a-zA-Z-_]{4,25}/
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
        page_title = req.get_param('title')
        har = self.HarCaptureAddon.new_page(page_title)
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


class PresentResource(VerifyResponseMixin, NoEntriesResponseMixin, ValidateMatchCriteriaMixin):
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
                pattern: /[a-zA-Z-_]{4,25}/
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
          422:
            description: The MatchCriteria are invalid.
        """
        self.respond_with_error_on_invalid_criteria(req, resp)
        criteria = req.media
        hv = HarVerifications(self.HarCaptureAddon.har)
        result = hv.present(criteria)
        self.HarCaptureAddon.add_verification_to_har(name, 'present', result)
        if criteria.get('error_if_no_traffic', True) and hv.no_entries():
            self.respond_with_no_entries_error(resp, result)
        else:
            self.respond_with_bool(resp, result)


class NotPresentResource(VerifyResponseMixin, NoEntriesResponseMixin, ValidateMatchCriteriaMixin):
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
                pattern: /[a-zA-Z-_]{4,25}/
        responses:
          200:
            description: The traffic had no matching items
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/VerifyResult"
          422:
            description: The MatchCriteria are invalid.
        """
        self.respond_with_error_on_invalid_criteria(req, resp)
        criteria = req.media
        hv = HarVerifications(self.HarCaptureAddon.har)
        result = hv.not_present(criteria)
        self.HarCaptureAddon.add_verification_to_har(name, 'not_present', result)
        if criteria.get('error_if_no_traffic', True) and hv.no_entries():
            self.respond_with_no_entries_error(resp, result)
        else:
            self.respond_with_bool(resp, result)


class SizeResource(VerifyResponseMixin, NoEntriesResponseMixin, ValidateMatchCriteriaMixin):
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
              description: The size used for comparison, in kilobytes
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
                pattern: /[a-zA-Z-_]{4,25}/
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
          422:
            description: The MatchCriteria are invalid.
        """
        self.respond_with_error_on_invalid_criteria(req, resp)
        criteria = req.media
        size_val = int(size) * 1000
        hv = HarVerifications(self.HarCaptureAddon.har)
        max_size = hv.get_max(criteria, 'response')
        result = size_val <= max_size
        self.HarCaptureAddon.add_verification_to_har(name, 'size', result)
        if criteria.get('error_if_no_traffic', True) and hv.no_entries():
            self.respond_with_no_entries_error(resp, result)
        else:
            self.respond_with_bool(resp, result)


class SLAResource(VerifyResponseMixin, NoEntriesResponseMixin, ValidateMatchCriteriaMixin):
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
                pattern: /[a-zA-Z-_]{4,25}/
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
          422:
            description: The MatchCriteria are invalid.
        """
        self.respond_with_error_on_invalid_criteria(req, resp)
        criteria = req.media
        time_val = int(time)
        hv = HarVerifications(self.HarCaptureAddon.har)
        val = hv.get_max(criteria, 'time')
        result = time_val <= val
        self.HarCaptureAddon.add_verification_to_har(name, 'sla', val)
        if criteria.get('error_if_no_traffic', True) and hv.no_entries():
            self.respond_with_no_entries_error(resp, result)
        else:
            self.respond_with_bool(resp, result)


class CounterResource():
    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

    def addon_path(self):
        return "har/counters"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_post(self, req, resp):
        """Adds a custom counter to the har page/step under _counters
        ---
        description: Add Custom Counter to the captured traffic har
        operationId: addCounter
        tags:
          - BrowserUpProxy
        requestBody:
          description: Receives a new counter to add. The counter is stored, under the hood, in an array in the har under the _counters key
          required: true
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Counter"
        responses:
          204:
            description: The counter was added.
          422:
            description: The counter was invalid.
        """
        try:
            counter = req.media
            CounterSchema().load(counter)
            self.HarCaptureAddon.add_counter_to_har(counter)
        except ValidationError as err:
            resp.status = falcon.HTTP_422
            resp.content_type = falcon.MEDIA_JSON
            resp.body = json.dumps({'error': err.messages}, ensure_ascii=False)
        else:
            resp.status = falcon.HTTP_204


class ErrorResource():
    def __init__(self, HarCaptureAddon):
        self.name = "harcapture"
        self.HarCaptureAddon = HarCaptureAddon

    def addon_path(self):
        return "har/errors"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_post(self, req, resp):
        """Verifies traffic matching the criteria is present
        ---
        description: Add Custom Error to the captured traffic har
        operationId: addError
        tags:
          - BrowserUpProxy
        requestBody:
          description: Receives an error to track. Internally, the error is stored in an array in the har under the _errors key
          required: true
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
        responses:
          204:
            description: The Error was added.
          422:
            description: The Error was invalid.
        """
        try:
            error = req.media
            ErrorSchema().load(error)
            self.HarCaptureAddon.add_error_to_har(error)
        except ValidationError as err:
            resp.status = falcon.HTTP_422
            resp.content_type = falcon.MEDIA_JSON
            resp.body = json.dumps({'error': err.messages}, ensure_ascii=False)
        else:
            resp.status = falcon.HTTP_204
