import { combineReducers, applyMiddleware, createStore as createReduxStore } from 'redux'
import thunk from 'redux-thunk'

export function createStore(parts) {
    return createReduxStore(
        combineReducers(parts),
        applyMiddleware(...[thunk])
    )
}

export { default as TFlow } from './_tflow'
