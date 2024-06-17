import { ModeState, updateMode } from "../modes";
import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";

export const TOGGLE_LOCAL = "TOGGLE_LOCAL";
export const SET_APPLICATIONS = "SET_APPLICATIONS";

interface LocalState extends ModeState {
    applications?: string;
}

export const initialState: LocalState = {
    active: false,
    applications: "",
};

export const getMode = (modes) => {
    const localMode = modes.local;
    let mode = "local";
    if (localMode.active) {
        if (localMode.applications && localMode.applications.length > 0) {
            mode += `:${localMode.applications}`;
        }
        return mode;
    }
    return "";
};

export const toggleLocal = () => {
    return async (dispatch) => {
        dispatch({ type: TOGGLE_LOCAL });

        const result = await dispatch(updateMode());

        if (!result.success) {
            //TODO: handle error
            console.error("error", result.error);
        }
    };
};

const sanitizeInput = (input: string) => {
    return input.replace(/,$/, ""); // Remove trailing comma
};

export const setApplications = (applications: string) => {
    return async (dispatch) => {
        const sanitizeApplications = sanitizeInput(applications);
        dispatch({
            type: SET_APPLICATIONS,
            applications: sanitizeApplications,
        });
        const result = await dispatch(updateMode());

        if (!result.success) {
            //TODO: handle error
            console.error("error", result.error);
        }
    };
};

const localReducer = (state = initialState, action): LocalState => {
    switch (action.type) {
        case TOGGLE_LOCAL:
            return {
                ...state,
                active: !state.active,
                error: undefined,
            };
        case SET_APPLICATIONS:
            return {
                ...state,
                applications: action.applications,
                error: undefined,
            };
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const modes = action.data.mode.value;
                const isActive = modes.some((mode) => mode.includes("local"));
                let extractedApplications = "";
                modes.forEach((mode) => {
                    if (mode.startsWith("local:")) {
                        extractedApplications = mode.substring("local:".length);
                    }
                });
                return {
                    ...state,
                    active: isActive,
                    applications:
                        extractedApplications !== ""
                            ? extractedApplications
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
