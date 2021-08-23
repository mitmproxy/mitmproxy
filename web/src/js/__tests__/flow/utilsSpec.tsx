import * as utils from '../../flow/utils'
import {TFlow} from "../ducks/tutils";

describe('MessageUtils', () => {
    it('should be possible to get first header', () => {
        let tflow = TFlow();
        expect(utils.MessageUtils.get_first_header(tflow.request, /header/)).toEqual("qvalue")
        expect(utils.MessageUtils.get_first_header(tflow.request, /123/)).toEqual(undefined)
    })

    it('should be possible to get Content-Type', () => {
        let tflow = TFlow();
        tflow.request.headers = [["Content-Type", "text/html"]];
        expect(utils.MessageUtils.getContentType(tflow.request)).toEqual("text/html");
    })

    it('should be possible to match header', () => {
        let h1 = ["foo", "bar"],
            msg = {headers : [h1]}
        expect(utils.MessageUtils.match_header(msg, /foo/i)).toEqual(h1)
        expect(utils.MessageUtils.match_header(msg, /123/i)).toBeFalsy()
    })

    it('should be possible to get content URL', () => {
        const flow = TFlow();
        // request
        let view = "bar";
        expect(utils.MessageUtils.getContentURL(flow, flow.request, view)).toEqual(
            "./flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/request/content/bar.json"
        )
        expect(utils.MessageUtils.getContentURL(flow, flow.request, '')).toEqual(
            "./flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/request/content.data"
        )
        // response
        expect(utils.MessageUtils.getContentURL(flow, flow.response, view)).toEqual(
            "./flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/response/content/bar.json"
        )
    })
})

describe('RequestUtils', () => {
    it('should be possible prettify url', () => {
        let flow = TFlow();
        expect(utils.RequestUtils.pretty_url(flow.request)).toEqual(
            "http://address:22/path"
        )
    })
})

describe('parseUrl', () => {
    it('should be possible to parse url', () => {
        let url = "http://foo:4444/bar"
        expect(utils.parseUrl(url)).toEqual({
            port: 4444,
            scheme: 'http',
            host: 'foo',
            path: '/bar'
        })

        expect(utils.parseUrl("foo:foo")).toBeFalsy()
    })
})

describe('isValidHttpVersion', () => {
    it('should be possible to validate http version', () => {
        expect(utils.isValidHttpVersion("HTTP/1.1")).toBeTruthy()
        expect(utils.isValidHttpVersion("HTTP//1")).toBeFalsy()
    })
})
