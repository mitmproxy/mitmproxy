import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface UiFlowState {
    tab: string;
    contentViewFor: { [messageId: string]: string };
}

export const defaultState: UiFlowState = {
    tab: "request",
    contentViewFor: {},
};

const flowsSlice = createSlice({
    name: "ui/flow",
    initialState: defaultState,
    reducers: {
        selectTab(state, action: PayloadAction<string>) {
            state.tab = action.payload;
        },
        setContentViewFor(
            state,
            action: PayloadAction<{ messageId: string; contentView: string }>,
        ) {
            state.contentViewFor[action.payload.messageId] =
                action.payload.contentView;
        },
    },
});

const { actions, reducer } = flowsSlice;
export const { selectTab, setContentViewFor } = actions;
export default reducer;
