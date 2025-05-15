import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export enum FilterName {
    Search = "search",
    Highlight = "highlight",
}

const filtersSlice = createSlice({
    name: "ui/filters",
    initialState: {
        [FilterName.Search]: "",
        [FilterName.Highlight]: "",
    },
    reducers: {
        setFilter(state, action: PayloadAction<string>) {
            window.backend.updateFilter(FilterName.Search, action.payload);
            state[FilterName.Search] = action.payload;
        },
        setHighlight(state, action: PayloadAction<string>) {
            window.backend.updateFilter(FilterName.Highlight, action.payload);
            state[FilterName.Highlight] = action.payload;
        },
    },
});

const { actions, reducer } = filtersSlice;
export const { setFilter, setHighlight } = actions;
export default reducer;
