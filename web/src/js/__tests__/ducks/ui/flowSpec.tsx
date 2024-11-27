import reduceFlow, * as FlowActions from "../../../ducks/ui/flow";

describe("option reducer", () => {
    it("should return initial state", () => {
        expect(reduceFlow(undefined, { type: "other" })).toEqual(
            FlowActions.defaultState,
        );
    });

    it("should handle set tab", () => {
        expect(
            reduceFlow(undefined, FlowActions.selectTab("response")).tab,
        ).toEqual("response");
    });

    it("should handle set content view", () => {
        expect(
            reduceFlow(undefined, FlowActions.setContentViewFor("foo", "Raw"))
                .contentViewFor["foo"],
        ).toEqual("Raw");
    });
});
