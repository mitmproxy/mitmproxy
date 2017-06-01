import initialize from '../urlState'
import { updateStoreFromUrl, updateUrlFromStore } from '../urlState'

import reduceFlows from '../ducks/flows'
import reduceUI from '../ducks/ui/index'
import reduceEventLog from '../ducks/eventLog'
import * as flowsActions from '../ducks/flows'

import configureStore from 'redux-mock-store'

const mockStore = configureStore()
history.replaceState = jest.fn()

describe('updateStoreFromUrl', () => {

    it('should handle search query', () => {
        window.location.hash = "#/flows?s=foo"
        let store = mockStore()
        updateStoreFromUrl(store)
        expect(store.getActions()).toEqual([{ filter: "foo", type: "FLOWS_SET_FILTER" }])
    })

    it('should handle highlight query', () => {
        window.location.hash = "#/flows?h=foo"
        let store = mockStore()
        updateStoreFromUrl(store)
        expect(store.getActions()).toEqual([{ highlight: "foo", type: "FLOWS_SET_HIGHLIGHT" }])
    })

    it('should handle show event log', () => {
        window.location.hash = "#/flows?e=true"
        let initialState = { eventLog: reduceEventLog(undefined, {}) },
            store = mockStore(initialState)
        updateStoreFromUrl(store)
        expect(store.getActions()).toEqual([{ type: "EVENTS_TOGGLE_VISIBILITY" }])
    })

    it('should handle unimplemented query argument', () => {
        window.location.hash = "#/flows?foo=bar"
        console.error = jest.fn()
        let store = mockStore()
        updateStoreFromUrl(store)
        expect(console.error).toBeCalledWith("unimplemented query arg: foo=bar")
    })

    it('should select flow and tab', () => {
        window.location.hash = "#/flows/123/request"
        let store = mockStore()
        updateStoreFromUrl(store)
        expect(store.getActions()).toEqual([
            {
                flowIds: ["123"],
                type: "FLOWS_SELECT"
            },
            {
                tab: "request",
                type: "UI_FLOWVIEW_SET_TAB"
            }
        ])
    })
})

describe('updateUrlFromStore', () => {
    let initialState = {
        flows:    reduceFlows(undefined, {}),
        ui:       reduceUI(undefined, {}),
        eventLog: reduceEventLog(undefined, {})
    }

    it('should update initial url', () => {
        let store = mockStore(initialState)
        updateUrlFromStore(store)
        expect(history.replaceState).toBeCalledWith(undefined, '', '/#/flows')
    })

    it('should update url', () => {
        let flows = reduceFlows(undefined, flowsActions.select(123)),
            state = {
                ...initialState,
                flows: reduceFlows(flows, flowsActions.setFilter('~u foo'))
            },
            store = mockStore(state)
        updateUrlFromStore(store)
        expect(history.replaceState).toBeCalledWith(undefined, '', '/#/flows/123/request?s=~u foo')
    })
})

describe('initialize', () => {
    let initialState = {
        flows:    reduceFlows(undefined, {}),
        ui:       reduceUI(undefined, {}),
        eventLog: reduceEventLog(undefined, {})
    }

    it('should handle initial state', () => {
        let store = mockStore(initialState)
        initialize(store)
        store.dispatch({ type: "foo" })
    })
})
