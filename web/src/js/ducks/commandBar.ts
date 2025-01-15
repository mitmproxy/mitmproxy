import { createSlice } from "@reduxjs/toolkit";

interface CommandBarState {
    visible: boolean;
}

export const defaultState: CommandBarState = {
    visible: false,
};

export const commandBarSlice = createSlice({
    name: "commandBar",
    initialState: defaultState,
    reducers: {
        toggleVisibility(state) {
            state.visible = !state.visible;
        },
    },
});

const { actions, reducer } = commandBarSlice;
export const { toggleVisibility } = actions;
export default reducer;
