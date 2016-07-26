jest.unmock('redux')
jest.unmock('redux-thunk')

import { combineReducers, applyMiddleware, createStore as createReduxStore } from 'redux'
import thunk from 'redux-thunk'

export function createStore(parts) {
    return createReduxStore(
        combineReducers(parts),
        applyMiddleware(...[thunk])
    )
}
