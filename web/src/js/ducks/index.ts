import {
    AnyAction,
    applyMiddleware,
    combineReducers,
    compose,
    createStore as createReduxStore,
    PreloadedState,
    Store
} from "redux"
import eventLog from "./eventLog"
import flows from "./flows"
import ui from "./ui/index"
import connection from "./connection"
import options from './options'
import commandBar from "./commandBar";
import thunk, {ThunkAction, ThunkDispatch, ThunkMiddleware} from "redux-thunk";
import {TypedUseSelectorHook, useDispatch, useSelector} from "react-redux";
import conf from "./conf";
import options_meta from "./options_meta";


// @ts-ignore
const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;

export const rootReducer = combineReducers({
    commandBar,
    eventLog,
    flows,
    connection,
    ui,
    options,
    options_meta,
    conf,
});
export type RootState = ReturnType<typeof rootReducer>


export type AppThunk<ReturnType = void> = ThunkAction<ReturnType,
    RootState,
    unknown,
    AnyAction>

export const createAppStore = (preloadedState?: PreloadedState<RootState>): Store<RootState> => {
    return createReduxStore(
        rootReducer,
        preloadedState,
        composeEnhancers(applyMiddleware(
            thunk as ThunkMiddleware<RootState>
        )))
};

export const store = createAppStore(undefined);

// this would be correct, but PyCharm bails on it
// export type AppDispatch = typeof store.dispatch
// instead:
export type AppDispatch = ThunkDispatch<RootState, void, AnyAction>
export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector
