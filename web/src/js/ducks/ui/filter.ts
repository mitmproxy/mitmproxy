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
        setFilter(
            state,
            action: PayloadAction<{ name: FilterName; expr: string }>,
        ) {
            window.backend.updateFilter(
                action.payload.name,
                action.payload.expr,
            );
            state[action.payload.name] = action.payload.expr;
        },
    },
    /* FIXME remove
    extraReducers: (builder) => {
        builder
            .addCase(FLOWS_RECEIVE, (state, action) => {
                // Awkward workaround to trigger filter updates after RECEIVE.
                if(state[FilterName.Search] !== "") {
                    window.backend.updateFilter(FilterName.Search, state[FilterName.Search]);
                }
                if(state[FilterName.Highlight] !== "") {
                    window.backend.updateFilter(FilterName.Highlight, state[FilterName.Highlight]);
                }
            })
    },*/
});

const { actions, reducer } = filtersSlice;
export const { setFilter } = actions;
export default reducer;
