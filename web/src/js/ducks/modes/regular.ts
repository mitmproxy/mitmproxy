import { fetchApi } from "../../utils";
import { ModeState, updateMode } from "../modes";

const TOGGLE_REGULAR = "TOGGLE_REGULAR";
const ERROR_REGULAR = "ERROR_REGULAR";

interface RegularState extends ModeState {}

const initialState: RegularState = {
    active: true,
};

export const toggleRegular = () => {
    return async (dispatch) => {
        dispatch({ type: TOGGLE_REGULAR });

        const result = await dispatch(updateMode());

        if (!result.success) {
            console.error("error", result.error);
            dispatch({ type: ERROR_REGULAR, error: result.error });
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
        case ERROR_REGULAR:
            return {
                ...state,
                error: action.error,
            };
        default:
            return state;
    }
};

export default regularReducer;
