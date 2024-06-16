import { combineReducers } from "redux";
import regularReducer, {
    getMode as getRegularModeConfig,
} from "./modes/regular";
import { fetchApi } from "../utils";
import localReducer, { getMode as getLocalModeConfig } from "./modes/local";
import wireguardReducer, {getMode as getWireguardModeConfig} from "./modes/wireguard";
import reverseReducer, {getMode as getReverseModeConfig} from "./modes/reverse";

export interface ModeState {
    active: boolean;
    listen_port?: number;
    listen_host?: string;
    error?: string;
}

export const updateMode = () => {
    return async (_, getState) => {
        try {
            const modes = getState().modes;

            const activeModes: string[] = [
                getRegularModeConfig(modes),
                getLocalModeConfig(modes),
                getWireguardModeConfig(modes),
                getReverseModeConfig(modes),
            ].filter((mode) => mode !== "");
            console.log(activeModes);
            const response = await fetchApi.put("/options", {
                mode: activeModes,
            });
            if (response.status === 200) {
                return { success: true };
            } else {
                const errorText = await response.text();
                return { success: false, error: errorText };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    };
};

const modes = combineReducers({
    regular: regularReducer,
    local: localReducer,
    wireguard: wireguardReducer,
    reverse: reverseReducer,
    //add new modes here
});

export default modes;
