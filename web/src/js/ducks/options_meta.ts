import {
    OPTIONS_RECEIVE,
    OPTIONS_UPDATE,
    OptionsStateWithMeta,
} from "./options";
import { createSlice } from "@reduxjs/toolkit";

export type OptionsMetaState = Partial<OptionsStateWithMeta>;

export const defaultState: OptionsMetaState = {};

const optionsMeta = createSlice({
    name: "optionsMeta",
    initialState: defaultState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(OPTIONS_RECEIVE, (state, action) => action.payload)
            .addCase(OPTIONS_UPDATE, (state, action) => ({
                ...state,
                ...action.payload,
            }));
    },
});

export default optionsMeta.reducer;
