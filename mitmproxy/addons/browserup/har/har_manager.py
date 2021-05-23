from mitmproxy import ctx
from datetime import datetime
from datetime import timezone
from mitmproxy.net.http import cookies
from mitmproxy.addons.browserup.har.har_builder import HarBuilder
from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes
import json
import copy

DEFAULT_PAGE_REF = "Default"
DEFAULT_PAGE_TITLE = "Default"
REQUEST_SUBMITTED_FLAG = "_request_submitted"


class HarManagerMixin():
    # Used to manage a single active har, gets mixed into har_capture_addon

    def __init__(self):
        self.num = 0
        self.har = HarBuilder.har()
        self.har_page_count = 0
        self.har_capture_types = [
            HarCaptureTypes.REQUEST_HEADERS,
            HarCaptureTypes.REQUEST_COOKIES,
            HarCaptureTypes.REQUEST_CONTENT,
            HarCaptureTypes.REQUEST_BINARY_CONTENT,
            HarCaptureTypes.RESPONSE_HEADERS,
            HarCaptureTypes.RESPONSE_COOKIES,
            HarCaptureTypes.RESPONSE_CONTENT,
            HarCaptureTypes.RESPONSE_BINARY_CONTENT,
            HarCaptureTypes.WEBSOCKET_MESSAGES,
        ]
        self.current_har_page = None
        self.http_connect_timings = {}

    def create_har_entry(self, flow):
        har = self.get_or_create_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE, True)
        entry = HarBuilder.entry()
        har['log']['entries'].append(entry)
        return entry

    def get_har(self, clean_har):
        if clean_har:
            return self.new_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE)
        return self.har

    def get_default_har_page(self):
        for hp in self.har['log']['pages']:
            if hp['title'] == DEFAULT_PAGE_TITLE:
                return hp
        return None

    def get_or_create_har(self, page_ref, page_title, create_page=False):
        if self.har is None:
            self.new_har(page_ref, page_title, create_page)
            if create_page:
                self.get_or_create_default_page()
        return self.har

    def new_page(self, page_ref, page_title):
        ctx.log.info(
            'Creating new page with initial page ref: {}, title: {}'.
            format(page_ref, page_title))

        har = self.get_or_create_har(page_ref, page_title, False)

        end_of_page_har = None

        if self.current_har_page is not None:
            current_page_ref = self.current_har_page['id']
            self.end_page()

            end_of_page_har = self.copy_har_through_page_ref(har, current_page_ref)

        if page_ref is None:
            self.har_page_count += 1
            page_ref = "Page " + str(self.har_page_count)

        if page_title is None:
            page_title = page_ref

        new_page = HarBuilder.page(title=page_title, id=page_ref)
        har['log']['pages'].append(new_page)

        self.current_har_page = new_page
        return end_of_page_har

    def get_current_page_ref(self):
        har_page = self.current_har_page
        if har_page is None:
            har_page = self.get_or_create_default_page()
        return har_page['id']

    def get_or_create_current_page(self):
        har_page = self.current_har_page
        if har_page is None:
            har_page = self.get_or_create_default_page()
        return har_page

    def get_or_create_default_page(self):
        default_page = self.get_default_page()
        if default_page is None:
            default_page = self.add_default_page()
        return default_page

    def add_default_page(self):
        self.get_or_create_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE, False)
        new_page = HarBuilder.page(title=DEFAULT_PAGE_REF, id=DEFAULT_PAGE_REF)
        self.har['log']['pages'].append(new_page)
        return new_page

    def get_default_page(self):
        for p in self.har['log']['pages']:
            if p['id'] == DEFAULT_PAGE_REF:
                return p
        return None

    def new_har(self, initial_page_ref=DEFAULT_PAGE_REF, initial_page_title=DEFAULT_PAGE_TITLE, create_page=False):

        if create_page:
            ctx.log.info(
                'Creating new har with initial page ref: {}, title: {}'.
                format(initial_page_ref, initial_page_title))
        else:
            ctx.log.info('Creating new har without initial page')

        old_har = self.end_har()

        self.har_page_count = 0
        self.har = HarBuilder.har()

        if create_page:
            self.new_page(initial_page_ref, initial_page_title)

        self.copy_entries_without_response(old_har)

        return old_har

    def add_verification_to_har(self, verification_name, verification_type, result):
        page = self.get_or_create_current_page()
        page.setdefault('_verifications', {}).setdefault(
            verification_name, {"type": verification_type, "passed": result})

    def end_har(self):
        ctx.log.info('Ending current har...')
        old_har = self.har
        if old_har is None:
            return

        self.end_page()
        self.har = None

        return old_har

    def copy_entries_without_response(self, old_har):
        if old_har is not None:
            for entry in old_har['log']['entries']:
                if not self.har_entry_has_response(entry):
                    self.har['log']['entries'].append(entry)

    def add_har_page(self, pageRef, pageTitle):
        ctx.log.debug('Adding har page with ref: {} and title: {}'.format(pageRef, pageTitle))
        har_page = HarBuilder.page(id=pageRef, title=pageTitle)
        self.har['log']['pages'].append(har_page)
        return har_page

    def end_page(self):
        ctx.log.info('Ending current page...')

        previous_har_page = self.current_har_page
        self.current_har_page = None

        if previous_har_page is None:
            return

    def is_har_entry_submitted(self, har_entry):
        return REQUEST_SUBMITTED_FLAG in har_entry

    def har_entry_has_response(self, har_entry):
        return bool(har_entry['response'])

    def har_entry_clear_request(self, har_entry):
        har_entry['request'] = {}

    def filter_har_for_report(self, har):
        if har is None:
            return har

        har_copy = copy.deepcopy(har)
        entries_to_report = []
        for entry in har_copy['log']['entries']:
            if self.is_har_entry_submitted(entry):
                if self.har_entry_has_response(entry):
                    del entry[REQUEST_SUBMITTED_FLAG]
                    self.har_entry_clear_request(entry)
                    entries_to_report.append(entry)
            else:
                entries_to_report.append(entry)
        har_copy['log']['entries'] = entries_to_report

        return har_copy

    def mark_har_entries_submitted(self, har):
        if har is not None:
            for entry in har['log']['entries']:
                entry[REQUEST_SUBMITTED_FLAG] = True

    def copy_har_through_page_ref(self, har, page_ref):
        if har is None:
            return None

        if har['log'] is None:
            return HarBuilder.har()

        page_refs_to_copy = []

        for page in har['log']['pages']:
            page_refs_to_copy.append(page['id'])
            if page_ref == page['id']:
                break

        log_copy = HarBuilder.log()

        for entry in har['log']['entries']:
            if entry['pageref'] in page_refs_to_copy:
                log_copy['entries'].append(entry)

        for page in har['log']['pages']:
            if page['id'] in page_refs_to_copy:
                log_copy['pages'].append(page)

        har_copy = HarBuilder.har()
        har_copy['log'] = log_copy

        return har_copy

    def format_cookies(self, cookie_list):
        rv = []

        for name, value, attrs in cookie_list:
            cookie_har = {
                "name": name,
                "value": value,
            }

            # HAR only needs some attributes
            for key in ["path", "domain", "comment"]:
                if key in attrs:
                    cookie_har[key] = attrs[key]

            # These keys need to be boolean!
            for key in ["httpOnly", "secure"]:
                cookie_har[key] = bool(key in attrs)

            # Expiration time needs to be formatted
            expire_ts = cookies.get_expiration_ts(attrs)
            if expire_ts is not None:
                cookie_har["expires"] = datetime.fromtimestamp(expire_ts, timezone.utc).isoformat()

            rv.append(cookie_har)

        return rv

    def save_har(self, full_path):
        json_dump: str = json.dumps(self.har, indent=2)

        with open(full_path, "wb") as file:
            raw: bytes = json_dump.encode()
            file.write(raw)
            file.flush()
            file.close()

    def format_request_cookies(self, fields):
        return self.format_cookies(cookies.group_cookies(fields))

    def format_response_cookies(self, fields):
        return self.format_cookies((c[0], c[1][0], c[1][1]) for c in fields)

    def name_value(self, obj):
        """
            Convert (key, value) pairs to HAR format.
        """
        return [{"name": k, "value": v} for k, v in obj.items()]
