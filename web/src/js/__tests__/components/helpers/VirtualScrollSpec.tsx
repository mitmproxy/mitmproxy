import { calcVScroll } from "../../../components/helpers/VirtualScroll";

describe("VirtualScroll", () => {
    it("should return default state without options", () => {
        expect(calcVScroll()).toEqual({
            start: 0,
            end: 0,
            paddingTop: 0,
            paddingBottom: 0,
        });
    });

    it("should calculate position without itemHeights", () => {
        expect(
            calcVScroll({
                itemCount: 0,
                rowHeight: 32,
                viewportHeight: 400,
                viewportTop: 0,
            }),
        ).toEqual({
            start: 0,
            end: 0,
            paddingTop: 0,
            paddingBottom: 0,
        });
    });

    it("should calculate position with itemHeights", () => {
        expect(
            calcVScroll({
                itemCount: 5,
                itemHeights: [100, 100, 100, 100, 100],
                viewportHeight: 300,
                viewportTop: 0,
                rowHeight: 100,
            }),
        ).toEqual({
            start: 0,
            end: 4,
            paddingTop: 0,
            paddingBottom: 100,
        });
    });

    it("should handle the case where lots of existing rows are removed without itemHeights", () => {
        expect(
            calcVScroll({
                itemCount: 10,
                rowHeight: 32,
                viewportHeight: 400,
                viewportTop: 12_000,
            }),
        ).toEqual({
            start: 0,
            end: 10,
            paddingTop: 0,
            paddingBottom: 0,
        });
    });

    it("should handle the case where lots of existing rows are removed with itemHeights", () => {
        expect(
            calcVScroll({
                itemCount: 4,
                itemHeights: [100, 100, 100, 100],
                viewportHeight: 400,
                viewportTop: 12_000,
                rowHeight: 32,
            }),
        ).toEqual({
            start: 0,
            end: 4,
            paddingTop: 0,
            paddingBottom: 0,
        });
    });
});
