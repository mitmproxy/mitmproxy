import { createSlice } from "@reduxjs/toolkit";

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
        isInitial: true,
    },
    reducers: {
        setCurrent(state, action) {
            state.current = action.payload;
            state.isInitial = false;
        },
    },
});

const { actions, reducer } = tabsSlice;
export const { setCurrent } = actions;
export default reducer;
