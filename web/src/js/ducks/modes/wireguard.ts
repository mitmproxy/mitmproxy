import { parseRaw, WireguardState } from "../../modes/wireguard";
import { STATE_RECEIVE, STATE_UPDATE } from "../backendState";
import { addSetter, createModeUpdateThunk, updateState } from "./utils";
import { createSlice } from "@reduxjs/toolkit";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/wireguard/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/wireguard/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/wireguard/setListenPort",
);
export const setFilePath = createModeUpdateThunk<string | undefined>(
    "modes/wireguard/setFilePath",
);

export const initialState: WireguardState[] = [
    {
        active: false,
        ui_id: Math.random(),
    },
];

export const wireguardSlice = createSlice({
    name: "modes/wireguard",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        addSetter(builder, "file_path", setFilePath);
        builder.addCase(STATE_RECEIVE, updateState("wireguard", parseRaw));
        builder.addCase(STATE_UPDATE, updateState("wireguard", parseRaw));
    },
});

export default wireguardSlice.reducer;
