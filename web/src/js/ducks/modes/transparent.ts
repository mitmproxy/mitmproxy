import { parseRaw, TransparentState } from "../../modes/transparent";
import { STATE_RECEIVE, STATE_UPDATE } from "../backendState";
import { addSetter, createModeUpdateThunk, updateState } from "./utils";
import { createSlice } from "@reduxjs/toolkit";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/transparent/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/transparent/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/transparent/setListenPort",
);

export const initialState: TransparentState[] = [
    {
        active: false,
        ui_id: Math.random(),
    },
];

export const transparentSlice = createSlice({
    name: "modes/transparent",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        builder.addCase(STATE_RECEIVE, updateState("transparent", parseRaw));
        builder.addCase(STATE_UPDATE, updateState("transparent", parseRaw));
    },
});

export default transparentSlice.reducer;
