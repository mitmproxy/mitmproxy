import {fetchApi} from "../utils"
import * as optionsEditorActions from "./ui/optionsEditor"
import _ from "lodash"
import {Reducer} from "redux";
import {defaultState, Option, OptionsState} from "./_options_gen";
import {AppThunk} from "./index";

export const RECEIVE = 'OPTIONS_RECEIVE'
export const UPDATE = 'OPTIONS_UPDATE'
export const REQUEST_UPDATE = 'REQUEST_UPDATE'

export {Option, defaultState}

const reducer: Reducer<OptionsState> = (state = defaultState, action) => {

    switch (action.type) {
        case RECEIVE:
            let s = <OptionsState>{};
            // @ts-ignore
            for (const [name, {value}] of Object.entries(action.data)) {
                s[name] = value
            }
            return s;

        case UPDATE:
            let s2 = {...state}
            // @ts-ignore
            for (const [name, {value}] of Object.entries(action.data)) {
                s2[name] = value
            }
            return s2

        default:
            return state
    }
}
export default reducer

export function pureSendUpdate(option: Option, value, dispatch) {
    return async dispatch => {
        try {
            const response = await fetchApi.put('/options', {[option]: value});
            if (response.status === 200) {
                dispatch(optionsEditorActions.updateSuccess(option))
            } else {
                throw await response.text()
            }
        } catch (error) {
            return dispatch(optionsEditorActions.updateError(option, error))
        }
    }
}

let sendUpdate = _.throttle(pureSendUpdate, 500, {leading: true, trailing: true})

export function update(name: Option, value: any): AppThunk {
    return dispatch => {
        dispatch(optionsEditorActions.startUpdate(name, value))
        sendUpdate(name, value, dispatch);
    }
}

export function save() {
    return dispatch => fetchApi('/options/save', {method: 'POST'})
}

export function addInterceptFilter(example) {
    return (dispatch, getState) => {
        let intercept = getState().options.intercept;
        if (intercept && intercept.includes(example)) {
            return
        }
        if (!intercept) {
            intercept = example
        } else {
            intercept = `${intercept} | ${example}`
        }
        dispatch(update("intercept", intercept));
    }
}
