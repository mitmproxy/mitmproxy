import {applyMiddleware, combineReducers, compose, createStore} from "redux"
import eventLog from "./eventLog"
import flows from "./flows"
import settings from "./settings"
import ui from "./ui/index"
import connection from "./connection"
import options from './options'
import thunk from "redux-thunk";
import {logger} from 'redux-logger'
import {TypedUseSelectorHook, useDispatch, useSelector} from "react-redux";


const middlewares = [thunk];

// logger must be last
if (process.env.NODE_ENV !== 'production') {
    middlewares.push(logger);
}

// @ts-ignore
const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;


export const rootReducer = combineReducers({
    eventLog,
    flows,
    settings,
    connection,
    ui,
    options,
});

export const store = createStore(
    rootReducer,
    composeEnhancers(applyMiddleware(...middlewares))
)
export type RootState = ReturnType<typeof rootReducer>
export type AppDispatch = typeof store.dispatch

export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector
