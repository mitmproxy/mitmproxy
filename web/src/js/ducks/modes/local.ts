import { ModeState, updateMode } from "../modes";
import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { getModesOfType } from "./utils";

export const MODE_LOCAL_TOGGLE = "MODE_LOCAL_TOGGLE";
export const MODE_LOCAL_SET_APPLICATIONS = "MODE_LOCAL_SET_APPLICATIONS";

interface LocalState extends ModeState {
    applications?: string;
}

export const initialState: LocalState = {
    active: false,
    name: "local",
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
            // TODO: handle error
        }
    };

export const sanitizeInput = (input: string) => {
    return input.replace(/,$/, ""); // Remove trailing comma
};

export const setApplications =
    (applications, updateModeFunc = updateMode) =>
    async (dispatch) => {
        const sanitizeApplications = sanitizeInput(applications);
        dispatch({
            type: MODE_LOCAL_SET_APPLICATIONS,
            applications: sanitizeApplications,
        });

        const result = await dispatch(updateModeFunc());

        if (!result.success) {
            // TODO: handle error
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
            console.log(action.applications);
            return {
                ...state,
                applications: action.applications,
                error: undefined,
            };
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const currentModeConfig = getModesOfType(
                    "local",
                    action.data.mode.value
                )[0];
                const isActive = currentModeConfig !== undefined;
                return {
                    ...state,
                    active: isActive,
                    applications: isActive
                        ? currentModeConfig.applications
                        : state.applications,
                    error: undefined,
                };
            }
            return state;
        default:
            return state;
    }
};

export default localReducer;
