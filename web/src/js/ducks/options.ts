import { fetchApi } from "../utils";
import * as optionsEditorActions from "./ui/optionsEditor";
import { defaultState, Option, OptionsState } from "./_options_gen";
import { AppThunk } from "./index";
import { createAction, createSlice } from "@reduxjs/toolkit";

export interface OptionMeta<T> {
    value: T;
    choices?: T[];
    default: T;
    help: string;
    type: string;
}

export type OptionsStateWithMeta = {
    [name in Option]: OptionMeta<OptionsState[name]>;
};

export const OPTIONS_RECEIVE =
    createAction<OptionsStateWithMeta>("OPTIONS_RECEIVE");
export const OPTIONS_UPDATE =
    createAction<Partial<OptionsStateWithMeta>>("OPTIONS_UPDATE");

export { Option, defaultState };

const optionsSlice = createSlice({
    name: "options",
    initialState: defaultState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(OPTIONS_RECEIVE, (state, action) => {
                const s = <OptionsState>{};
                for (const [name, { value }] of Object.entries(
                    action.payload,
                )) {
                    s[name] = value;
                }
                return s;
            })
            .addCase(OPTIONS_UPDATE, (state, action) => {
                for (const [name, { value }] of Object.entries(
                    action.payload,
                )) {
                    state[name] = value;
                }
            });
    },
});

export default optionsSlice.reducer;

export async function pureSendUpdate(option: Option, value, dispatch) {
    try {
        const response = await fetchApi.put("/options", {
            [option]: value,
        });
        if (response.status === 200) {
            dispatch(optionsEditorActions.updateSuccess({ option }));
        } else {
            throw await response.text();
        }
    } catch (error) {
        dispatch(
            optionsEditorActions.updateError({
                option,
                error: error.toString(),
            }),
        );
    }
}

const sendUpdate = pureSendUpdate; // _.throttle(pureSendUpdate, 500, {leading: true, trailing: true})

export function update(name: Option, value: any): AppThunk {
    return (dispatch) => {
        dispatch(optionsEditorActions.startUpdate({ option: name, value }));
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
