import { configureStore, UnknownAction } from '@reduxjs/toolkit'
import { ThunkAction } from 'redux-thunk'


import eventLog from "./eventLog";
import flows from "./flows";
import ui from "./ui/index";
import connection from "./connection";
import options from "./options";
import commandBar from "./commandBar";

import backendState from "./backendState";
import options_meta from "./options_meta";


export const reducer = {
    commandBar,
    eventLog,
    flows,
    connection,
    ui,
    options,
    options_meta,
    backendState,
};

export const store = configureStore({reducer});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch

export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  UnknownAction
>