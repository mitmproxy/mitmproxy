import { createSlice } from "@reduxjs/toolkit"

export enum Tab {
    Capture,
    FlowList,
    Options,
    Flow,
}

const tabsSlice = createSlice({
    name: 'ui/tabs',
    initialState: {
        current: Tab.Capture,
    },
    reducers: {
      setActive(state, action) {
        state.current = action.payload;
      },
    },
});

const { actions, reducer } = tabsSlice
export const { setActive: setCurrent } = actions
export default reducer
