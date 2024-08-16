import { createModeUpdateThunk, addSetter, updateState } from "./utils";
import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { createSlice } from "@reduxjs/toolkit";
import { parseRaw } from "../../modes/upstream";
import { UpstreamProxyProtocols, UpstreamState } from "../../modes/upstream";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/upstream/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/upstream/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/upstream/setListenPort",
);
export const setProtocol = createModeUpdateThunk<UpstreamProxyProtocols>(
    "modes/upstream/setProtocol",
);
export const setDestination = createModeUpdateThunk<string>(
    "modes/upstream/setDestination",
);

export const initialState: UpstreamState[] = [
    {
        active: false,
        protocol: UpstreamProxyProtocols.HTTPS,
        destination: "",
        ui_id: Math.random(),
    },
];

export const upstreamSlice = createSlice({
    name: "modes/upstream",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        addSetter(builder, "protocol", setProtocol);
        addSetter(builder, "destination", setDestination);

        builder.addCase(RECEIVE_STATE, updateState("upstream", parseRaw));
        builder.addCase(UPDATE_STATE, updateState("upstream", parseRaw));
    },
});

export default upstreamSlice.reducer;
