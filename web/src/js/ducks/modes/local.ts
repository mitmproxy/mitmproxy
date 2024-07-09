import {
    getModesOfType,
    includeModeState,
    ModeState,
    updateMode,
} from "./utils";
import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import type { ModesState } from "../modes";

export const MODE_LOCAL_TOGGLE = "MODE_LOCAL_TOGGLE";
export const MODE_LOCAL_SET_APPLICATIONS = "MODE_LOCAL_SET_APPLICATIONS";
export const MODE_LOCAL_ERROR = "MODE_LOCAL_ERROR";

interface LocalState extends ModeState {
    applications?: string;
}

export const initialState: LocalState = {
    active: false,
    applications: "",
};

export const getMode = (modes: ModesState): string[] => {
    const mode = modes.local.applications
        ? `local:${modes.local.applications}`
        : "local";
    return includeModeState(mode, modes.local);
};

export const toggleLocal = () => async (dispatch) => {
    dispatch({ type: MODE_LOCAL_TOGGLE });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({ type: MODE_LOCAL_ERROR, error: e.message });
    }
};

export const setApplications = (applications) => async (dispatch) => {
    dispatch({
        type: MODE_LOCAL_SET_APPLICATIONS,
        applications: applications,
    });

    try {
        await dispatch(updateMode());
    } catch (e) {
        dispatch({ type: MODE_LOCAL_ERROR, error: e.message });
    }
};

const localReducer = (state = initialState, action): LocalState => {
    switch (action.type) {
        case MODE_LOCAL_TOGGLE:
            return {
                ...state,
                active: !state.active,
                error: undefined,
            };
        case MODE_LOCAL_SET_APPLICATIONS:
            return {
                ...state,
                applications: action.applications,
                error: undefined,
            };
        case UPDATE_STATE:
        case RECEIVE_STATE:
            if (action.data && action.data.servers) {
                const currentModeConfig = getModesOfType(
                    "local",
                    action.data.servers,
                )[0];
                const isActive = currentModeConfig !== undefined;
                return {
                    ...state,
                    active: isActive,
                    applications: isActive
                        ? currentModeConfig.data
                        : state.applications,
                    error: isActive ? undefined : state.error,
                };
            }
            return state;
        case MODE_LOCAL_ERROR:
            return {
                ...state,
                error: action.error,
            };
        default:
            return state;
    }
};

export default localReducer;
