import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { addSetter, createModeUpdateThunk, updateState } from "./utils";
import { createSlice } from "@reduxjs/toolkit";
import { parseRaw, RegularState } from "../../modes/regular";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/regular/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/regular/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/regular/setListenPort",
);

export const initialState: RegularState[] = [
    {
        active: true,
        ui_id: Math.random(),
    },
];

export const regularSlice = createSlice({
    name: "modes/regular",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        builder.addCase(RECEIVE_STATE, updateState("regular", parseRaw));
        builder.addCase(UPDATE_STATE, updateState("regular", parseRaw));
    },
});

export default regularSlice.reducer;
