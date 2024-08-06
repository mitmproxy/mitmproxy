import {
    ModeState,
    createModeUpdateThunk,
    getModesOfType,
    includeListenAddress,
    isActiveMode,
    addSetter,
} from "./utils";
import type { ModesState } from "../modes";
import { ReverseProxyProtocols } from "../../backends/consts";
import {
    BackendState,
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { partition } from "../../utils";
import { shallowEqual } from "react-redux";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface ReverseState extends ModeState {
    protocol: ReverseProxyProtocols;
    destination: string;
}

const getSpec = (state: ReverseState): string => {
    return includeListenAddress(
        `reverse:${state.protocol}://${state.destination}`,
        state,
    );
};

export const getSpecs = ({ reverse }: ModesState): string[] => {
    return reverse.filter(isActiveMode).map(getSpec);
};

export const setActive = createModeUpdateThunk<boolean>(
    "modes/reverse/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/reverse/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/reverse/setListenPort",
);
export const setProtocol = createModeUpdateThunk<ReverseProxyProtocols>(
    "modes/reverse/setProtocol",
);
export const setDestination = createModeUpdateThunk<string>(
    "modes/reverse/setDestination",
);

export const defaultReverseServerConfig = (): ReverseState => ({
    active: false,
    protocol: ReverseProxyProtocols.HTTPS,
    destination: "",
    ui_id: Math.random(),
});

export const initialState: ReverseState[] = [defaultReverseServerConfig()];

export const reverseSlice = createSlice({
    name: "modes/reverse",
    initialState,
    reducers: {
        addServer: (state) => {
            state.push(defaultReverseServerConfig());
        },
        removeServer: (state, action: PayloadAction<ReverseState>) => {
            const index = state.findIndex(
                (m) => m.ui_id === action.payload.ui_id,
            );
            if (index !== -1) {
                if (state[index].active)
                    console.error(
                        "servers should be deactivated before removal",
                    );
                state.splice(index, 1);
            }
        },
    },
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        addSetter(builder, "protocol", setProtocol);
        addSetter(builder, "destination", setDestination);

        builder.addCase(RECEIVE_STATE, updateState);
        builder.addCase(UPDATE_STATE, updateState);
        function updateState(
            state: ReverseState[],
            action: PayloadAction<Partial<BackendState>>,
        ) {
            if (action.payload.servers) {
                // action.data.servers does not include servers that are currently inactive,
                // but we want to keep them in the UI. So we need to merge UI state with what we got from the server.

                const activeServers = Object.fromEntries(
                    getModesOfType("reverse", action.payload.servers).map(
                        (x) => [x.full_spec, x],
                    ),
                );

                const nextState: ReverseState[] = [];

                // keep current UI state as is, but correct `active` bit.
                for (const server of state) {
                    const spec = getSpec(server);
                    const active = spec in activeServers;
                    delete activeServers[spec];
                    nextState.push({
                        ...server,
                        active,
                    });
                }

                // add all new specs
                for (const { data, listen_host, listen_port } of Object.values(
                    activeServers,
                )) {
                    let [protocol, destination] = partition(data!, "://") as [
                        ReverseProxyProtocols,
                        string,
                    ];
                    if (!destination) {
                        destination = protocol;
                        protocol = ReverseProxyProtocols.HTTPS;
                    }
                    nextState.push({
                        active: true,
                        protocol,
                        destination,
                        listen_host,
                        listen_port,
                        ui_id: Math.random(),
                    });
                }

                // remove default config if still present.
                if (
                    nextState.length > 1 &&
                    shallowEqual(
                        {
                            ...nextState[0],
                            ui_id: undefined,
                        } as ReverseState,
                        {
                            ...defaultReverseServerConfig(),
                            ui_id: undefined,
                        } as ReverseState,
                    )
                ) {
                    nextState.shift();
                }

                return nextState;
            }
        }
    },
});
export const { addServer, removeServer } = reverseSlice.actions;
export default reverseSlice.reducer;
