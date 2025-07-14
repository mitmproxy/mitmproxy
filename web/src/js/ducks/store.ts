import { configureStore, UnknownAction } from "@reduxjs/toolkit";
import { ThunkAction } from "redux-thunk";

import eventLog from "./eventLog";
import flows from "./flows";
import ui from "./ui/index";
import connection from "./connection";
import options from "./options";
import commandBar from "./commandBar";

import backendState from "./backendState";
import options_meta from "./options_meta";
import modes from "./modes";
import processes from "./processes";

import { Version, createVersionSlice } from "./version";

const createReducer = (value: Version) => {
    const { reducer: versionReducer } = createVersionSlice({ value });

    return {
        commandBar,
        eventLog,
        flows,
        connection,
        modes,
        ui,
        options,
        options_meta,
        backendState,
        processes,
        version: versionReducer, // we don't really use this reducer, but it's needed to construct the initial state.
    };
};

export const middlewares = {
    immutableCheck: { warnAfter: 500_000 },
    serializableCheck: { warnAfter: 500_000, ignoredPaths: ["flows"] },
};

export const createStore = (value: Version) => {
    const reducer = createReducer(value);

    return configureStore({
        reducer,
        middleware: (getDefaultMiddleware) => getDefaultMiddleware(middlewares),
        devTools:
            process.env.NODE_ENV !== "production"
                ? { serialize: { options: { map: true } } }
                : false,
    });
};

// Export default store and reducer for mitmweb.
// Mitmwebnext will use the factory functions above to create a different configuration instead.
export const reducer = createReducer("web");
export const store = createStore("web");

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch;

export type RootStore = typeof store;

export type AppThunk<ReturnType = void> = ThunkAction<
    ReturnType,
    RootState,
    unknown,
    UnknownAction
>;
