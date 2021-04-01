import * as utils from '../../flow/utils'

describe('MessageUtils', () => {
    it('should be possible to get first header', () => {
        let msg = { headers: [["foo", "bar"]]}
        expect(utils.MessageUtils.get_first_header(msg, "foo")).toEqual("bar")
        expect(utils.MessageUtils.get_first_header(msg, "123")).toEqual(undefined)
    })

    it('should be possible to get Content-Type', () => {
        let type = "text/html",
            msg = { headers: [["Content-Type", type]]}
        expect(utils.MessageUtils.getContentType(msg)).toEqual(type)
    })

    it('should be possible to match header', () => {
        let h1 = ["foo", "bar"],
            msg = {headers : [h1]}
        expect(utils.MessageUtils.match_header(msg, /foo/i)).toEqual(h1)
        expect(utils.MessageUtils.match_header(msg, /123/i)).toBeFalsy()
    })

    it('should be possible to get content URL', () => {
        // request
        let msg = "foo", view = "bar",
            flow = { request: msg, id: 1}
        expect(utils.MessageUtils.getContentURL(flow, msg, view)).toEqual(
            "./flows/1/request/content/bar.json"
        )
        expect(utils.MessageUtils.getContentURL(flow, msg, '')).toEqual(
            "./flows/1/request/content.data"
        )
        // response
        flow = {response: msg, id: 2}
        expect(utils.MessageUtils.getContentURL(flow, msg, view)).toEqual(
            "./flows/2/response/content/bar.json"
        )
    })
})

describe('RequestUtils', () => {
    it('should be possible prettify url', () => {
        let request = {port: 4444, scheme: "http", pretty_host: "foo", path: "/bar"}
        expect(utils.RequestUtils.pretty_url(request)).toEqual(
            "http://foo:4444/bar"
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
