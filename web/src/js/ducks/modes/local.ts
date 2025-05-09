import { STATE_RECEIVE, STATE_UPDATE } from "../backendState";
import { addSetter, createModeUpdateThunk, updateState } from "./utils";
import { createSlice } from "@reduxjs/toolkit";
import { LocalState, parseRaw } from "../../modes/local";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/local/setActive",
);
export const setSelectedProcesses = createModeUpdateThunk<string | undefined>(
    "modes/local/setSelectedProcesses",
);

export const initialState: LocalState[] = [
    {
        active: false,
        selectedProcesses: "",
        ui_id: Math.random(),
    },
];

export const localSlice = createSlice({
    name: "modes/local",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "selectedProcesses", setSelectedProcesses);
        builder.addCase(STATE_RECEIVE, updateState("local", parseRaw));
        builder.addCase(STATE_UPDATE, updateState("local", parseRaw));
    },
});

export default localSlice.reducer;
