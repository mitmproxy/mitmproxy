import flowReducer, {
    selectTab,
    selectRequestTab,
    selectResponseTab,
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

    it("sets the request and response panel tabs independently", () => {
        let state = flowReducer(defaultState, selectRequestTab("timing"));
        expect(state.tabRequest).toEqual("timing");
        expect(state.tabResponse).toEqual("response");

        state = flowReducer(state, selectResponseTab("websocket"));
        expect(state.tabResponse).toEqual("websocket");
        expect(state.tabRequest).toEqual("timing");
        expect(state.tab).toEqual(defaultState.tab);
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
