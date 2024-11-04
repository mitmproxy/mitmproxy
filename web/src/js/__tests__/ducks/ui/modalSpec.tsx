import reduceModal, * as ModalActions from "../../../ducks/ui/modal";

describe("modal reducer", () => {
    it("should return the initial state", () => {
        expect(reduceModal(undefined, {})).toEqual({ activeModal: undefined });
    });

    it("should handle setActiveModal action", () => {
        const state = reduceModal(
            undefined,
            ModalActions.setActiveModal("foo"),
        );
        expect(state).toEqual({ activeModal: "foo" });
    });

    it("should handle hideModal action", () => {
        const state = reduceModal(undefined, ModalActions.hideModal());
        expect(state).toEqual({ activeModal: undefined });
    });
});
