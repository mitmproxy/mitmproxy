import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { ModeState, updateMode } from "./utils";
import { includeModeState, getModesOfType } from "./utils";

export const MODE_REGULAR_TOGGLE = "MODE_REGULAR_TOGGLE";

interface RegularState extends ModeState {}

export const initialState: RegularState = {
    active: true,
    listen_port: 8080,
};

export const getMode = (modes) => {
    const regularMode = modes.regular;
    return includeModeState("regular", regularMode);
};

export const toggleRegular =
    (updateModeFunc = updateMode) =>
    async (dispatch) => {
        dispatch({ type: MODE_REGULAR_TOGGLE });

        const result = await dispatch(updateModeFunc());

        if (!result.success) {
            // TODO: handle error
        }
    };

const regularReducer = (state = initialState, action): RegularState => {
    switch (action.type) {
        case MODE_REGULAR_TOGGLE:
            return {
                ...state,
                active: !state.active,
            };
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const currentModeConfig = getModesOfType(
                    "regular",
                    action.data.mode.value,
                )[0];
                const isActive = currentModeConfig !== undefined;
                return {
                    ...state,
                    active: isActive,
                    listen_host: isActive
                        ? currentModeConfig.listen_host
                        : state.listen_host,
                    listen_port: isActive
                        ? (currentModeConfig.listen_port as number) || 8080
                        : state.listen_port,
                };
            }
            return state;
        default:
            return state;
    }
};

export default regularReducer;
