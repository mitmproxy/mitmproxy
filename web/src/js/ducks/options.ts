import { fetchApi } from "../utils";
import * as optionsEditorActions from "./ui/optionsEditor";
import { defaultState, Option, OptionsState } from "./_options_gen";
import { AppThunk } from "./index";

export const RECEIVE = "OPTIONS_RECEIVE";
export const UPDATE = "OPTIONS_UPDATE";
export const REQUEST_UPDATE = "REQUEST_UPDATE";

export { Option, defaultState };

export default function reducer(state = defaultState, action): OptionsState {
    switch (action.type) {
        case RECEIVE: {
            const s = <OptionsState>{};
            // @ts-expect-error untyped action
            for (const [name, { value }] of Object.entries(action.data)) {
                s[name] = value;
            }
            return s;
        }
        case UPDATE: {
            const s2 = { ...state };
            // @ts-expect-error untyped action
            for (const [name, { value }] of Object.entries(action.data)) {
                s2[name] = value;
            }
            return s2;
        }
        default:
            return state;
    }
}

export async function pureSendUpdate(option: Option, value, dispatch) {
    try {
        const response = await fetchApi.put("/options", {
            [option]: value,
        });
        if (response.status === 200) {
            dispatch(optionsEditorActions.updateSuccess(option));
        } else {
            throw await response.text();
        }
    } catch (error) {
        dispatch(optionsEditorActions.updateError(option, error));
    }
}

const sendUpdate = pureSendUpdate; // _.throttle(pureSendUpdate, 500, {leading: true, trailing: true})

export function update(name: Option, value: any): AppThunk {
    return (dispatch) => {
        dispatch(optionsEditorActions.startUpdate(name, value));
        sendUpdate(name, value, dispatch);
    };
}

export function save() {
    return () => fetchApi("/options/save", { method: "POST" });
}

export function addInterceptFilter(example) {
    return (dispatch, getState) => {
        let intercept = getState().options.intercept;
        if (intercept && intercept.includes(example)) {
            return;
        }
        if (!intercept) {
            intercept = example;
        } else {
            intercept = `${intercept} | ${example}`;
        }
        dispatch(update("intercept", intercept));
    };
}
