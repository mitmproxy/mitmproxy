jest.dontMock("jquery");
jest.dontMock("../utils");

describe("utils", function () {
    var utils = require("../utils");
    it("formatSize", function(){
        expect(utils.formatSize(1024)).toEqual("1kb");
        expect(utils.formatSize(0)).toEqual("0");
        expect(utils.formatSize(10)).toEqual("10b");
        expect(utils.formatSize(1025)).toEqual("1.0kb");
        expect(utils.formatSize(1024*1024)).toEqual("1mb");
        expect(utils.formatSize(1024*1024+1)).toEqual("1.0mb");
    });
});

