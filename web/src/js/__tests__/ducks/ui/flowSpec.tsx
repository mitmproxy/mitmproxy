import flowReducer, {
    selectTab,
    setContentViewFor,
    defaultState,
} from "../../../ducks/ui/flow";

describe("option reducer", () => {
    it("should return initial state", () => {
        expect(flowReducer(undefined, { type: "other" })).toEqual(defaultState);
    });

    it("should handle set tab", () => {
        expect(flowReducer(undefined, selectTab("response")).tab).toEqual(
            "response",
        );
    });

    it("should handle set content view", () => {
        expect(
            flowReducer(
                undefined,
                setContentViewFor({ messageId: "foo", contentView: "Raw" }),
            ).contentViewFor["foo"],
        ).toEqual("Raw");
    });
});
