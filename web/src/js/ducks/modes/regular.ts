import {
    RECEIVE as RECEIVE_OPTIONS,
    UPDATE as UPDATE_OPTIONS,
} from "../options";
import { ModeState, updateMode } from "../modes";
import { addListenAddr } from "./utils";

export const TOGGLE_REGULAR = "TOGGLE_REGULAR";

interface RegularState extends ModeState {}

export const initialState: RegularState = {
    active: true,
    name: "regular",
};

export const getMode = (modes) => {
    const regularMode = modes.regular;
    return addListenAddr(regularMode);
};

export const toggleRegular = () => {
    return async (dispatch) => {
        dispatch({ type: TOGGLE_REGULAR });

        const result = await dispatch(updateMode());

        if (!result.success) {
            //TODO: handle error
            console.error("error", result.error);
        }
    };
};

const regularReducer = (state = initialState, action): RegularState => {
    switch (action.type) {
        case TOGGLE_REGULAR:
            return {
                ...state,
                active: !state.active,
            };
        case UPDATE_OPTIONS:
        case RECEIVE_OPTIONS:
            if (action.data && action.data.mode) {
                const isActive = action.data.mode.value.includes("regular");
                return {
                    ...state,
                    active: isActive,
                };
            }
            return state;
        default:
            return state;
    }
};

export default regularReducer;
