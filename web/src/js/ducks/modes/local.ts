import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { addSetter, createModeUpdateThunk, updateState } from "./utils";
import { createSlice } from "@reduxjs/toolkit";
import { LocalState, parseRaw } from "../../modes/local";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/local/setActive",
);
export const setApplications = createModeUpdateThunk<string | undefined>(
    "modes/local/setApplications",
);

export const initialState: LocalState[] = [
    {
        active: false,
        applications: "",
        ui_id: Math.random(),
    },
];

export const localSlice = createSlice({
    name: "modes/local",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "applications", setApplications);
        builder.addCase(RECEIVE_STATE, updateState("local", parseRaw));
        builder.addCase(UPDATE_STATE, updateState("local", parseRaw));
    },
});

export default localSlice.reducer;
