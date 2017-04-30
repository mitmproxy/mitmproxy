import initialize from '../urlState'

import reduceFlows from '../ducks/flows'
import reduceUI from '../ducks/ui/index'
import reduceEventLog from '../ducks/eventLog'
import * as flowsActions from '../ducks/flows'

import configureStore from 'redux-mock-store'

const mockStore = configureStore()

describe('updateStoreFromUrl', () => {
    history.replaceState = jest.fn()
    let initialState = {
            flows:    reduceFlows(undefined, {}),
            ui:       reduceUI(undefined, {}),
            eventLog: reduceEventLog(undefined, {})
    }

    it('should handle search query', () => {
        window.location.hash = "#/flows?s=foo"
        let store = mockStore(initialState)
        initialize(store)
        expect(store.getActions()).toEqual([{ filter: "foo", type: "FLOWS_SET_FILTER" }])
    })

    it('should handle highlight query', () => {
        window.location.hash = "#/flows?h=foo"
        let store = mockStore(initialState)
        initialize(store)
        expect(store.getActions()).toEqual([{ highlight: "foo", type: "FLOWS_SET_HIGHLIGHT" }])
    })

    it('should handle show event log', () => {
        window.location.hash = "#/flows?e=true"
        let store = mockStore(initialState)
        initialize(store)
        expect(store.getActions()).toEqual([{ type: "EVENTS_TOGGLE_VISIBILITY" }]) })

    it('should handle unimplemented query argument', () => {
        window.location.hash = "#/flows?foo=bar"
        console.error = jest.fn()
        let store = mockStore(initialState)
        initialize(store)
        expect(console.error).toBeCalledWith("unimplemented query arg: foo=bar")
    })

    it('should select flow and tab', () => {
        window.location.hash = "#/flows/123/request"
        let store = mockStore(initialState)
        initialize(store)
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
    history.replaceState = jest.fn()
    let flows = reduceFlows(undefined, flowsActions.select(123)),
    initialState = {
        flows:    reduceFlows(flows, flowsActions.setFilter('~u foo')),
        ui:       reduceUI(undefined, {}),
        eventLog: reduceEventLog(undefined, {})
    }

    it('should update url', () => {
        let store = mockStore(initialState)
        initialize(store)
        expect(history.replaceState).toBeCalledWith(undefined, '', '/#/flows/123/request?s=~u foo')
    })
})
