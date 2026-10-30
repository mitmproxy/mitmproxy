import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";

interface UiFlowState {
    // Active tab for the single-column (non-HTTP) flow view.
    tab: string;
    // Active tabs for the split HTTP request/response panels.
    tabRequest: string;
    tabResponse: string;
    contentViewFor: { [messageId: string]: string };
}

export const defaultState: UiFlowState = {
    tab: "request",
    tabRequest: "request",
    tabResponse: "response",
    contentViewFor: {},
};

const flowsSlice = createSlice({
    name: "ui/flow",
    initialState: defaultState,
    reducers: {
        selectTab(state, action: PayloadAction<string>) {
            state.tab = action.payload;
        },
        selectRequestTab(state, action: PayloadAction<string>) {
            state.tabRequest = action.payload;
        },
        selectResponseTab(state, action: PayloadAction<string>) {
            state.tabResponse = action.payload;
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
export const {
    selectTab,
    selectRequestTab,
    selectResponseTab,
    setContentViewFor,
} = actions;
export default reducer;
