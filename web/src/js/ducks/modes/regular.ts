import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { ModeState, updateMode } from "./utils";
import { addListenAddr, getModesOfType } from "./utils";

export const MODE_REGULAR_TOGGLE = "MODE_REGULAR_TOGGLE";

interface RegularState extends ModeState {}

export const initialState: RegularState = {
    active: true,
    name: "regular",
};

export const getMode = (modes) => {
    const regularMode = modes.regular;
    return addListenAddr(regularMode);
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
                    listen_host:
                        currentModeConfig && currentModeConfig.listen_host
                            ? currentModeConfig.listen_host
                            : state.listen_host,
                    listen_port:
                        currentModeConfig && currentModeConfig.listen_port
                            ? (currentModeConfig.listen_port as number)
                            : state.listen_port,
                };
            }
            return state;
        default:
            return state;
    }
};

export default regularReducer;
