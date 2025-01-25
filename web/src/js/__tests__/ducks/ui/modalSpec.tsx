import modalReducer, {
    setActiveModal,
    hideModal,
} from "../../../ducks/ui/modal";

describe("modal reducer", () => {
    it("should return the initial state", () => {
        expect(modalReducer(undefined, { type: "unknown" })).toEqual({
            activeModal: undefined,
        });
    });

    it("should handle setActiveModal action", () => {
        const state = modalReducer(undefined, setActiveModal("foo"));
        expect(state).toEqual({ activeModal: "foo" });
    });

    it("should handle hideModal action", () => {
        const state = modalReducer({ activeModal: "foo" }, hideModal());
        expect(state).toEqual({ activeModal: undefined });
    });
});
