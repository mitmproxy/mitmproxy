import { createModeUpdateThunk, addSetter, updateState } from "./utils";
import { STATE_RECEIVE, STATE_UPDATE } from "../backendState";
import { createSlice } from "@reduxjs/toolkit";
import { parseRaw } from "../../modes/upstream";
import { UpstreamState } from "../../modes/upstream";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/upstream/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/upstream/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/upstream/setListenPort",
);

export const setDestination = createModeUpdateThunk<string>(
    "modes/upstream/setDestination",
);

export const initialState: UpstreamState[] = [
    {
        active: false,
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
        addSetter(builder, "destination", setDestination);

        builder.addCase(STATE_RECEIVE, updateState("upstream", parseRaw));
        builder.addCase(STATE_UPDATE, updateState("upstream", parseRaw));
    },
});

export default upstreamSlice.reducer;
