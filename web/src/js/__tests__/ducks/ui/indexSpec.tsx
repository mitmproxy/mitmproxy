import reduceUI from "../../../ducks/ui/index";

describe("reduceUI in js/ducks/ui/index.js", () => {
    it("should combine flow and header", () => {
        const state = reduceUI(undefined, { type: "other" });
        expect(
            Object.prototype.hasOwnProperty.call(state, "flow"),
        ).toBeTruthy();
    });
});
