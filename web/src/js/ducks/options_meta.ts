import {Reducer} from "redux";
import {RECEIVE, UPDATE} from "./options";
import {OptionsState} from "./_options_gen";

interface OptionMeta<T> {
    value: T
    choices?: T[]
    default: T
    help: string
    type: string
}

type OptionsMetaState = Partial<{
    [name in keyof OptionsState]: OptionMeta<OptionsState[name]>
}>

export const defaultState: OptionsMetaState = {
}

const reducer: Reducer<OptionsMetaState> = (state = defaultState, action) => {
    switch (action.type) {

        case RECEIVE:
            return action.data

        case UPDATE:
            return {
                ...state,
                ...action.data,
            }

        default:
            return state
    }
}
export default reducer
