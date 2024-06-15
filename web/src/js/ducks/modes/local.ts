import { ModeState, updateMode } from "../modes";

const TOGGLE_LOCAL = "TOGGLE_LOCAL";
const ERROR_LOCAL = "ERROR_LOCAL";

interface LocalState extends ModeState {
    applications?: string[];
}

const initialState: LocalState = {
    active: false,
    applications: [],
};

export const getMode = (modes) => {
    const localMode = modes.local;
    let mode = "local";
    if (localMode.active) {
        if (localMode.applications && localMode.applications.length > 0) {
            mode += `:${localMode.applications.join(",")}`;
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
            console.error("error", result.error);
            dispatch({ type: TOGGLE_LOCAL, error: result.error });
        }
    };
};

const localReducer = (state = initialState, action): LocalState => {
    switch (action.type) {
        case TOGGLE_LOCAL:
            return {
                ...state,
                active: !state.active,
            };
        case ERROR_LOCAL:
            return {
                ...state,
                error: action.error,
            };
        default:
            return state;
    }
};

export default localReducer;
