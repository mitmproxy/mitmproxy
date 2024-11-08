import { createSlice } from "@reduxjs/toolkit";

const defaultState: { activeModal: string | undefined } = {
    activeModal: undefined,
};

const modalSlice = createSlice({
    name: "ui/modal",
    initialState: defaultState,
    reducers: {
        setActiveModal(state, action) {
            state.activeModal = action.payload;
        },
        hideModal(state) {
            state.activeModal = undefined;
        },
    },
});

const { actions, reducer } = modalSlice;
export const HIDE_MODAL = modalSlice.actions.hideModal.type;
export const { setActiveModal, hideModal } = actions;
export default reducer;
