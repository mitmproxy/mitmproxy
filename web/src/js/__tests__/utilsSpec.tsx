import * as utils from "../utils";
import { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

describe("formatSize", () => {
    it("should return 0 when 0 byte", () => {
        expect(utils.formatSize(0)).toEqual("0");
    });

    it("should return formatted size", () => {
        expect(utils.formatSize(27104011)).toEqual("25.8mb");
        expect(utils.formatSize(1023)).toEqual("1023b");
    });
});

describe("formatTimeDelta", () => {
    it("should return formatted time", () => {
        expect(utils.formatTimeDelta(3600100)).toEqual("1h");
    });
});

describe("formatTimeStamp", () => {
    it("should return formatted time", () => {
        expect(
            utils.formatTimeStamp(1483228800, { milliseconds: false }),
        ).toEqual("2017-01-01 00:00:00");
        expect(
            utils.formatTimeStamp(1483228800, { milliseconds: true }),
        ).toEqual("2017-01-01 00:00:00.000");
    });
});

describe("formatAddress", () => {
    it("should return formatted addresses", () => {
        expect(utils.formatAddress(["127.0.0.1", 8080])).toEqual(
            "127.0.0.1:8080",
        );
        expect(utils.formatAddress(["::1", 8080])).toEqual("[::1]:8080");
    });
});

describe("reverseString", () => {
    it("should return reversed string", () => {
        const str1 = "abc";
        const str2 = "xyz";
        expect(
            utils.reverseString(str1) > utils.reverseString(str2),
        ).toBeTruthy();
    });
});

describe("fetchApi", () => {
    it("should handle fetch operation", () => {
        utils.fetchApi("http://foo/bar", { method: "POST" });
        expect(fetchMock.mock.calls[0][0]).toEqual("http://foo/bar");
        fetchMock.mockClear();

        utils.fetchApi("http://foo?bar=1", { method: "POST" });
        expect(fetchMock.mock.calls[0][0]).toEqual("http://foo?bar=1");
    });

    it("should be possible to do put request", () => {
        fetchMock.mockClear();
        utils.fetchApi.put("http://foo", [1, 2, 3], {});
        expect(fetchMock.mock.calls[0]).toEqual([
            "http://foo",
            {
                body: "[1,2,3]",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-XSRFToken": undefined,
                },
                method: "PUT",
            },
        ]);
    });
});

describe("getDiff", () => {
    it("should return json object including only the changed keys value pairs", () => {
        const obj1 = { a: 1, b: { foo: 1 }, c: [3] };
        const obj2 = { a: 1, b: { foo: 2 }, c: [4] };
        expect(utils.getDiff(obj1, obj2)).toEqual({ b: { foo: 2 }, c: [4] });
    });
});
