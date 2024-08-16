import { DnsState, parseRaw } from "../../modes/dns";
import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { addSetter, createModeUpdateThunk, updateState } from "./utils";
import { createSlice } from "@reduxjs/toolkit";

export const setActive = createModeUpdateThunk<boolean>("modes/dns/setActive");
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/dns/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/dns/setListenPort",
);

export const initialState: DnsState[] = [
    {
        active: true,
        ui_id: Math.random(),
    },
];

export const dnsSlice = createSlice({
    name: "modes/dns",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        builder.addCase(RECEIVE_STATE, updateState("dns", parseRaw));
        builder.addCase(UPDATE_STATE, updateState("dns", parseRaw));
    },
});

export default dnsSlice.reducer;
