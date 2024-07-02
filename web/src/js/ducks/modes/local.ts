import { ModeState, updateMode } from "./utils";
import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { getModesOfType } from "./utils";

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

export const getMode = (modes) => {
    const localMode = modes.local;
    if (localMode.active) {
        if (localMode.applications && localMode.applications.length > 0) {
            return [`local:${localMode.applications}`];
        }
        return ["local"];
    }
    return [];
};

export const toggleLocal =
    (updateModeFunc = updateMode) =>
    async (dispatch) => {
        dispatch({ type: MODE_LOCAL_TOGGLE });

        const result = await dispatch(updateModeFunc());

        if (!result.success) {
            if (result.error.includes("local")) {
                dispatch({ type: MODE_LOCAL_ERROR, error: result.error });
            }
        }
    };

export const setApplications =
    (applications, updateModeFunc = updateMode) =>
    async (dispatch) => {
        dispatch({
            type: MODE_LOCAL_SET_APPLICATIONS,
            applications: applications,
        });

        const result = await dispatch(updateModeFunc());

        if (!result.success) {
            if (result.error.includes("local")) {
                dispatch({ type: MODE_LOCAL_ERROR, error: result.error });
            }
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
