jest.dontMock("jquery");
jest.dontMock("../utils");

import {formatSize} from "../utils.js"

describe("utils", function () {
    it("formatSize", function(){
        expect(formatSize(1024)).toEqual("1kb");
        expect(formatSize(0)).toEqual("0");
        expect(formatSize(10)).toEqual("10b");
        expect(formatSize(1025)).toEqual("1.0kb");
        expect(formatSize(1024*1024)).toEqual("1mb");
        expect(formatSize(1024*1024+1)).toEqual("1.0mb");
    });
});

