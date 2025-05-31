import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export enum FilterName {
    Search = "search",
    Highlight = "highlight",
}

export const initialState: Record<FilterName, string> = {
    [FilterName.Search]: "",
    [FilterName.Highlight]: "",
};

const filtersSlice = createSlice({
    name: "ui/filters",
    initialState,
    reducers: {
        setFilter(state, action: PayloadAction<string>) {
            state[FilterName.Search] = action.payload;
        },
        setHighlight(state, action: PayloadAction<string>) {
            state[FilterName.Highlight] = action.payload;
        },
    },
});

const { actions, reducer } = filtersSlice;
export const { setFilter, setHighlight } = actions;
export default reducer;
