import { parseRaw, SocksState } from "../../modes/socks";
import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { addSetter, createModeUpdateThunk, updateState } from "./utils";
import { createSlice } from "@reduxjs/toolkit";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/socks5/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/socks5/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/socks5/setListenPort",
);

export const initialState: SocksState[] = [
    {
        active: false,
        ui_id: Math.random(),
    },
];

export const socksSlice = createSlice({
    name: "modes/socks5",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        builder.addCase(RECEIVE_STATE, updateState("socks5", parseRaw));
        builder.addCase(UPDATE_STATE, updateState("socks5", parseRaw));
    },
});

export default socksSlice.reducer;
