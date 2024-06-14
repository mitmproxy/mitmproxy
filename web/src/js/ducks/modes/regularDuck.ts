import { fetchApi } from "../../utils";
import { ModeState, updateMode } from "../modes";

const TOGGLE_REGULAR = "TOGGLE_REGULAR";

interface RegularState extends ModeState {}

const initialState: RegularState = {
    active: true,
};

export const toggleRegular = () => {
    return async (dispatch, getState) => {
        const {active ,listen_port, listen_host} = getState().modes.regular;

        let baseMode = "regular"

        if(listen_host) {
            baseMode += `@${listen_host}`
        }
        
        if(listen_port) {
            baseMode += `:${listen_port}`
        }

        const result = await updateMode(baseMode, active);

        if (result.success) {
            dispatch({ type: TOGGLE_REGULAR });
        } else {
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
        default:
            return state;
    }
};

export default regularReducer;
