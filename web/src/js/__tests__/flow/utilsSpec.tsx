import * as utils from "../../flow/utils";
import { TFlow, TTCPFlow, TUDPFlow } from "../ducks/tutils";
import { TDNSFlow, THTTPFlow } from "../ducks/_tflow";
import { HTTPFlow } from "../../flow";

describe("MessageUtils", () => {
    it("should be possible to get first header", () => {
        const tflow = TFlow();
        expect(
            utils.MessageUtils.get_first_header(tflow.request, /header/),
        ).toEqual("qvalue");
        expect(
            utils.MessageUtils.get_first_header(tflow.request, /123/),
        ).toEqual(undefined);
    });

    it("should be possible to get Content-Type", () => {
        const tflow = TFlow();
        tflow.request.headers = [["Content-Type", "text/html"]];
        expect(utils.MessageUtils.getContentType(tflow.request)).toEqual(
            "text/html",
        );
    });

    it("should be possible to match header", () => {
        const h1 = ["foo", "bar"];
        const msg = { headers: [h1] };
        expect(utils.MessageUtils.match_header(msg, /foo/i)).toEqual(h1);
        expect(utils.MessageUtils.match_header(msg, /123/i)).toBeFalsy();
    });

    it("should be possible to get content URL", () => {
        const flow = TFlow();
        // request
        const view = "bar";
        expect(
            utils.MessageUtils.getContentURL(flow, flow.request, view),
        ).toEqual(
            "./flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/request/content/bar.json",
        );
        expect(
            utils.MessageUtils.getContentURL(flow, flow.request, ""),
        ).toEqual(
            "./flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/request/content.data",
        );
        // response
        expect(
            utils.MessageUtils.getContentURL(flow, flow.response, view),
        ).toEqual(
            "./flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/response/content/bar.json",
        );
    });
});

describe("RequestUtils", () => {
    it("should be possible prettify url", () => {
        const flow = TFlow();
        expect(utils.RequestUtils.pretty_url(flow.request)).toEqual(
            "http://address:22/path",
        );
    });
});

describe("parseUrl", () => {
    it("should be possible to parse url", () => {
        const url = "http://foo:4444/bar";
        expect(utils.parseUrl(url)).toEqual({
            port: 4444,
            scheme: "http",
            host: "foo",
            path: "/bar",
        });

        expect(utils.parseUrl("foo:foo")).toBeFalsy();
    });
});

describe("isValidHttpVersion", () => {
    it("should be possible to validate http version", () => {
        expect(utils.isValidHttpVersion("HTTP/1.1")).toBeTruthy();
        expect(utils.isValidHttpVersion("HTTP//1")).toBeFalsy();
    });
});

it("should be possible to get a start time", () => {
    expect(utils.startTime(THTTPFlow())).toEqual(946681200);
    expect(utils.startTime(TTCPFlow())).toEqual(946681200);
    expect(utils.startTime(TUDPFlow())).toEqual(946681200);
    expect(utils.startTime(TDNSFlow())).toEqual(946681200);
});

it("should be possible to get an end time", () => {
    const f: HTTPFlow = THTTPFlow();
    expect(utils.endTime(f)).toEqual(946681205);
    f.websocket = undefined;
    expect(utils.endTime(f)).toEqual(946681203);
    expect(utils.endTime(TTCPFlow())).toEqual(946681205);
    expect(utils.endTime(TUDPFlow())).toEqual(946681204.5);
    expect(utils.endTime(TDNSFlow())).toEqual(946681201);
});

it("should be possible to get a total size", () => {
    expect(utils.getTotalSize(THTTPFlow())).toEqual(43);
    expect(utils.getTotalSize(TTCPFlow())).toEqual(12);
    expect(utils.getTotalSize(TUDPFlow())).toEqual(12);
    expect(utils.getTotalSize(TDNSFlow())).toEqual(8);
});
