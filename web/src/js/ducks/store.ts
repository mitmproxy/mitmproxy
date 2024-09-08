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

export const reducer = {
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
};

export const store = configureStore({
    reducer,
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            immutableCheck: { warnAfter: 500_000 },
            serializableCheck: { warnAfter: 500_000 },
        }),
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch;

export type AppThunk<ReturnType = void> = ThunkAction<
    ReturnType,
    RootState,
    unknown,
    UnknownAction
>;
