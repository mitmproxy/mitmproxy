import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export enum Tab {
    Capture,
    FlowList,
    Options,
    Flow,
}

const tabsSlice = createSlice({
    name: "ui/tabs",
    initialState: {
        current: Tab.FlowList,
    },
    reducers: {
        setCurrent(state, action: PayloadAction<Tab>) {
            state.current = action.payload;
        },
    },
});

const { actions, reducer } = tabsSlice;
export const { setCurrent } = actions;
export default reducer;
