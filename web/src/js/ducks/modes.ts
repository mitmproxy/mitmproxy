import { combineReducers } from "redux";
import regularReducer, {
    getMode as getRegularModeConfig,
} from "./modes/regular";
import { fetchApi } from "../utils";
import localReducer, { getMode as getLocalModeConfig } from "./modes/local";

export interface ModeState {
    active: boolean;
    name: string;
    listen_port?: number;
    listen_host?: string;
    error?: string;
}

export const updateMode = () => {
    return async (_, getState) => {
        try {
            const modes = getState().modes;

            const activeModes: string[] = [
                ...getRegularModeConfig(modes),
                ...getLocalModeConfig(modes),
                //add new modes here
            ];
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
            //TODO: handle error
        }
    };
};

const modes = combineReducers({
    regular: regularReducer,
    local: localReducer,
    //add new modes here
});

export default modes;
