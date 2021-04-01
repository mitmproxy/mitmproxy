import * as utils from '../utils'

global.fetch = jest.fn()

describe('formatSize', () => {
    it('should return 0 when 0 byte', () => {
        expect(utils.formatSize(0)).toEqual('0')
    })

    it('should return formatted size', () => {
        expect(utils.formatSize(27104011)).toEqual("25.8mb")
        expect(utils.formatSize(1023)).toEqual("1023b")
    })
})

describe('formatTimeDelta', () => {
    it('should return formatted time', () => {
        expect(utils.formatTimeDelta(3600100)).toEqual("1h")
    })
})

describe('formatTimeSTamp', () => {
    it('should return formatted time', () => {
        expect(utils.formatTimeStamp(1483228800, false)).toEqual("2017-01-01 00:00:00.000")
    })
})

describe('reverseString', () => {
    it('should return reversed string', () => {
        let str1 = "abc", str2="xyz"
        expect(utils.reverseString(str1) > utils.reverseString(str2)).toBeTruthy()
    })
})

describe('fetchApi', () => {
    it('should handle fetch operation', () => {
        utils.fetchApi('http://foo/bar', {method: "POST"})
        expect(fetch.mock.calls[0][0]).toEqual(
            "http://foo/bar?_xsrf=undefined"
        )
        fetch.mockClear()

        utils.fetchApi('http://foo?bar=1', {method: "POST"})
        expect(fetch.mock.calls[0][0]).toEqual(
            "http://foo?bar=1&_xsrf=undefined"
        )

    })

    it('should be possible to do put request', () => {
        fetch.mockClear()
        utils.fetchApi.put("http://foo", [1, 2, 3], {})
        expect(fetch.mock.calls[0]).toEqual(
            [
                "http://foo?_xsrf=undefined",
                {
                    body: "[1,2,3]",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json" },
                    method: "PUT"
                },
            ]
        )
    })
})

describe('getDiff', () => {
    it('should return json object including only the changed keys value pairs', () => {
        let obj1 = {a: 1, b:{ foo: 1} , c: [3]},
            obj2 = {a: 1, b:{ foo: 2} , c: [4]}
        expect(utils.getDiff(obj1, obj2)).toEqual({ b: {foo: 2}, c:[4]})
    })
})

describe('pure', () => {
    let tFunc = function({ className }) {
        return (<p className={ className }>foo</p>)
    },
        puredFunc = utils.pure(tFunc),
        f = new puredFunc('bar')

    it('should display function name', () => {
        expect(utils.pure(tFunc).displayName).toEqual('tFunc')
    })

    it('should render properties', () => {
        expect(f.render()).toEqual(tFunc('bar'))
    })

})
