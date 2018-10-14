import urwid
import typing

from mitmproxy import exceptions
from mitmproxy.net.http import Headers
from mitmproxy.tools.console import layoutwidget
from mitmproxy.tools.console import signals
from mitmproxy.tools.console.grideditor import base
from mitmproxy.tools.console.grideditor import col_bytes
from mitmproxy.tools.console.grideditor import col_subgrid
from mitmproxy.tools.console.grideditor import col_text
from mitmproxy.tools.console.grideditor import col_viewany


class QueryEditor(base.FocusEditor):
    title = "Edit Query"
    columns = [
        col_text.Column("Key"),
        col_text.Column("Value")
    ]

    def get_data(self, flow):
        return flow.request.query.items(multi=True)

    def set_data(self, vals, flow):
        flow.request.query = vals


class HeaderEditor(base.FocusEditor):
    columns = [
        col_bytes.Column("Key"),
        col_bytes.Column("Value")
    ]


class RequestHeaderEditor(HeaderEditor):
    title = "Edit Request Headers"

    def get_data(self, flow):
        return flow.request.headers.fields

    def set_data(self, vals, flow):
        flow.request.headers = Headers(vals)


class ResponseHeaderEditor(HeaderEditor):
    title = "Edit Response Headers"

    def get_data(self, flow):
        return flow.response.headers.fields

    def set_data(self, vals, flow):
        flow.response.headers = Headers(vals)


class RequestFormEditor(base.FocusEditor):
    title = "Edit URL-encoded Form"
    columns = [
        col_text.Column("Key"),
        col_text.Column("Value")
    ]

    def get_data(self, flow):
        return flow.request.urlencoded_form.items(multi=True)

    def set_data(self, vals, flow):
        flow.request.urlencoded_form = vals


class PathEditor(base.FocusEditor):
    # TODO: Next row on enter?
    title = "Edit Path Components"
    columns = [
        col_text.Column("Component"),
    ]

    def data_in(self, data):
        return [[i] for i in data]

    def data_out(self, data):
        return [i[0] for i in data]

    def get_data(self, flow):
        return self.data_in(flow.request.path_components)

    def set_data(self, vals, flow):
        flow.request.path_components = self.data_out(vals)


class CookieEditor(base.FocusEditor):
    title = "Edit Cookies"
    columns = [
        col_text.Column("Name"),
        col_text.Column("Value"),
    ]

    def get_data(self, flow):
        return flow.request.cookies.items(multi=True)

    def set_data(self, vals, flow):
        flow.request.cookies = vals


class CookieAttributeEditor(base.FocusEditor):
    title = "Editing Set-Cookie attributes"
    columns = [
        col_text.Column("Name"),
        col_text.Column("Value"),
    ]
    grideditor: base.BaseGridEditor = None

    def data_in(self, data):
        return [(k, v or "") for k, v in data]

    def data_out(self, data):
        ret = []
        for i in data:
            if not i[1]:
                ret.append([i[0], None])
            else:
                ret.append(i)
        return ret

    def layout_pushed(self, prev):
        if self.grideditor.master.view.focus.flow:
            self._w = base.BaseGridEditor(
                self.grideditor.master,
                self.title,
                self.columns,
                self.grideditor.walker.get_current_value(),
                self.grideditor.set_subeditor_value,
                self.grideditor.walker.focus,
                self.grideditor.walker.focus_col
            )
        else:
            self._w = urwid.Pile([])


class SetCookieEditor(base.FocusEditor):
    title = "Edit SetCookie Header"
    columns = [
        col_text.Column("Name"),
        col_text.Column("Value"),
        col_subgrid.Column("Attributes", CookieAttributeEditor),
    ]

    def data_in(self, data):
        flattened = []
        for key, (value, attrs) in data:
            flattened.append([key, value, attrs.items(multi=True)])
        return flattened

    def data_out(self, data):
        vals = []
        for key, value, attrs in data:
            vals.append(
                [
                    key,
                    (value, attrs)
                ]
            )
        return vals

    def get_data(self, flow):
        return self.data_in(flow.response.cookies.items(multi=True))

    def set_data(self, vals, flow):
        flow.response.cookies = self.data_out(vals)


class OptionsEditor(base.GridEditor, layoutwidget.LayoutWidget):
    title: str = None
    columns = [
        col_text.Column("")
    ]

    def __init__(self, master, name, vals):
        self.name = name
        super().__init__(master, [[i] for i in vals], self.callback)

    def callback(self, vals):
        try:
            setattr(self.master.options, self.name, [i[0] for i in vals])
        except exceptions.OptionsError as v:
            signals.status_message.send(message=str(v))

    def is_error(self, col, val):
        pass


class DataViewer(base.GridEditor, layoutwidget.LayoutWidget):
    title: str = None

    def __init__(
            self,
            master,
            vals: typing.Union[
                typing.List[typing.List[typing.Any]],
                typing.List[typing.Any],
                str,
            ]) -> None:
        if vals:
            # Whatever vals is, make it a list of rows containing lists of column values.
            if isinstance(vals, str):
                vals = [vals]
            if not isinstance(vals[0], list):
                vals = [[i] for i in vals]

            self.columns = [col_viewany.Column("")] * len(vals[0])
        super().__init__(master, vals, self.callback)

    def callback(self, vals):
        pass

    def is_error(self, col, val):
        pass
