import initialize from '../urlState'

import reduceFlows from '../ducks/flows'
import reduceUI from '../ducks/ui/index'
import reduceEventLog from '../ducks/eventLog'

import * as flowsAction from '../ducks/flows'
import * as uiFlowAction from '../ducks/ui/flow'
import * as eventLogAction from '../ducks/eventLog'

import {createStore} from './ducks/tutils'


describe('test updateStoreFromUrl and updateUrlFromStore', () => {

    let store = createStore({
        flows: reduceFlows,
        ui: reduceUI,
        eventLog: reduceEventLog
    })

    history.replaceState = jest.fn()

    it('should handle search query', () => {
        window.location.hash = "#/flows?s=foo"
        let setFilter = jest.spyOn(flowsAction, 'setFilter')

        initialize(store)
        expect(setFilter).toBeCalledWith('foo')
    })

    it('should handle highlight query', () => {
        window.location.hash = "#/flows?h=foo"
        let setHighlight = jest.spyOn(flowsAction, 'setHighlight')

        initialize(store)
        expect(setHighlight).toBeCalledWith('foo')
    })

    it('should handle show event log', () => {
        window.location.hash = "#/flows?e=true"
        let toggleVisibility = jest.spyOn(eventLogAction, 'toggleVisibility')

        initialize(store)
        expect(toggleVisibility).toHaveBeenCalled()
    })

    it('should handle unimplemented query argument', () => {
        window.location.hash = "#/flows?foo=bar"
        console.error = jest.fn()

        initialize(store)
        expect(console.error).toBeCalledWith("unimplemented query arg: foo=bar")
    })

    it('should select flow and tab', () => {
        window.location.hash = "#/flows/123/request"
        let select      = jest.spyOn(flowsAction, 'select'),
            selectTab   = jest.spyOn(uiFlowAction, 'selectTab')

        initialize(store)
        expect(select).toBeCalledWith('123')
        expect(selectTab).toBeCalledWith('request')
    })

})
