import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface UiFlowState {
    tabResponse: string;
    tabRequest?: string;
    contentViewFor: { [messageId: string]: string };
}

export const defaultState: UiFlowState = {
    tabResponse: "request",
    contentViewFor: {},
};

const flowsSlice = createSlice({
    name: "ui/flow",
    initialState: defaultState,
    reducers: {
        selectTab(state, action: PayloadAction<string>) {
            state.tabResponse = action.payload;
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
