import { Reducer } from "redux";
import { Option, RECEIVE, UPDATE } from "./options";
import { OptionsState } from "./_options_gen";

interface OptionMeta<T> {
    value: T;
    choices?: T[];
    default: T;
    help: string;
    type: string;
}

type OptionsMetaState = Partial<{
    [name in Option]: OptionMeta<OptionsState[name]>;
}>;

export const defaultState: OptionsMetaState = {};

const reducer: Reducer<OptionsMetaState> = (
    state = defaultState,
    action,
): OptionsMetaState => {
    switch (action.type) {
        case RECEIVE:
            return action.data as OptionsMetaState;

        case UPDATE:
            return {
                ...state,
                ...(action.data as OptionsMetaState),
            };

        default:
            return state;
    }
};
export default reducer;
