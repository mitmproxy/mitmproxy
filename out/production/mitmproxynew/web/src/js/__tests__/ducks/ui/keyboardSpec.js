jest.mock('../../../utils')

import { Key } from '../../../utils'
import { onKeyDown } from '../../../ducks/ui/keyboard'
import reduceFlows from '../../../ducks/flows'
import reduceUI from '../../../ducks/ui/index'
import * as flowsActions from '../../../ducks/flows'
import * as UIActions from '../../../ducks/ui/flow'
import * as modalActions from '../../../ducks/ui/modal'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { fetchApi } from '../../../utils'

const mockStore = configureStore([ thunk ])
console.debug = jest.fn()

describe('onKeyDown', () => {
    let flows = undefined
    for( let i=1; i <= 12; i++ ) {
        flows = reduceFlows(flows, {type: flowsActions.ADD, data: {id: i, request: true, response: true}, cmd: 'add'})
    }
    let store = mockStore({ flows, ui: reduceUI(undefined, {}) })
    let createKeyEvent = (keyCode, shiftKey = undefined, ctrlKey = undefined) => {
            return onKeyDown({ keyCode, shiftKey, ctrlKey, preventDefault: jest.fn() })
    }

    afterEach(() => {
        store.clearActions()
        fetchApi.mockClear()
    });

    it('should handle cursor up', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select(2))
        store.dispatch(createKeyEvent(Key.K))
        expect(store.getActions()).toEqual([{ flowIds: [1], type: flowsActions.SELECT }])

        store.clearActions()
        store.dispatch(createKeyEvent(Key.UP))
        expect(store.getActions()).toEqual([{ flowIds: [1], type: flowsActions.SELECT }])
    })

    it('should handle cursor down', () => {
        store.dispatch(createKeyEvent(Key.J))
        expect(store.getActions()).toEqual([{ flowIds: [3], type: flowsActions.SELECT }])

        store.clearActions()
        store.dispatch(createKeyEvent(Key.DOWN))
        expect(store.getActions()).toEqual([{ flowIds: [3], type: flowsActions.SELECT }])
    })

    it('should handle page down', () => {
        store.dispatch(createKeyEvent(Key.SPACE))
        expect(store.getActions()).toEqual([{ flowIds: [12], type: flowsActions.SELECT }])

        store.getState().flows = reduceFlows(flows, flowsActions.select(1))
        store.clearActions()
        store.dispatch(createKeyEvent(Key.PAGE_DOWN))
        expect(store.getActions()).toEqual([{ flowIds: [11], type: flowsActions.SELECT }])
    })

    it('should handle page up', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select(11))
        store.dispatch(createKeyEvent(Key.PAGE_UP))
        expect(store.getActions()).toEqual([{ flowIds: [1], type: flowsActions.SELECT }])
    })

    it('should handle select first', () => {
        store.dispatch(createKeyEvent(Key.HOME))
        expect(store.getActions()).toEqual([{ flowIds: [1], type: flowsActions.SELECT }])
    })

    it('should handle select last', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select(1))
        store.dispatch(createKeyEvent(Key.END))
        expect(store.getActions()).toEqual([{ flowIds: [12], type: flowsActions.SELECT }])
    })

    it('should handle deselect', () => {
        store.dispatch(createKeyEvent(Key.ESC))
        expect(store.getActions()).toEqual([{ flowIds: [], type: flowsActions.SELECT }])
    })

    it('should handle switch to left tab', () => {
        store.dispatch(createKeyEvent(Key.LEFT))
        expect(store.getActions()).toEqual([{ tab: 'details', type: UIActions.SET_TAB }])
    })

    it('should handle switch to right tab', () => {
        store.dispatch(createKeyEvent(Key.TAB))
        expect(store.getActions()).toEqual([{ tab: 'response', type: UIActions.SET_TAB }])

        store.clearActions()
        store.dispatch(createKeyEvent(Key.RIGHT))
        expect(store.getActions()).toEqual([{ tab: 'response', type: UIActions.SET_TAB }])
    })

    it('should handle delete action', () => {
        store.dispatch(createKeyEvent(Key.D))
        expect(fetchApi).toBeCalledWith('/flows/1', { method: 'DELETE' })

    })

    it('should handle duplicate action', () => {
        store.dispatch(createKeyEvent(Key.D, true))
        expect(fetchApi).toBeCalledWith('/flows/1/duplicate', { method: 'POST' })
    })

    it('should handle resume action', () => {
        // resume all
        store.dispatch(createKeyEvent(Key.A, true))
        expect(fetchApi).toBeCalledWith('/flows/resume', { method: 'POST' })
        // resume
        store.getState().flows.byId[store.getState().flows.selected[0]].intercepted = true
        store.dispatch(createKeyEvent(Key.A))
        expect(fetchApi).toBeCalledWith('/flows/1/resume', { method: 'POST' })
    })

    it('should handle replay action', () => {
        store.dispatch(createKeyEvent(Key.R))
        expect(fetchApi).toBeCalledWith('/flows/1/replay', { method: 'POST' })
    })

    it('should handle revert action', () => {
        store.getState().flows.byId[store.getState().flows.selected[0]].modified = true
        store.dispatch(createKeyEvent(Key.V))
        expect(fetchApi).toBeCalledWith('/flows/1/revert', { method: 'POST' })
    })

    it('should handle kill action', () => {
        // kill all
        store.dispatch(createKeyEvent(Key.X, true))
        expect(fetchApi).toBeCalledWith('/flows/kill', { method: 'POST' })
        // kill
        store.dispatch(createKeyEvent(Key.X))
        expect(fetchApi).toBeCalledWith('/flows/1/kill', { method: 'POST' })
    })

    it('should handle clear action', () => {
        store.dispatch(createKeyEvent(Key.Z))
        expect(fetchApi).toBeCalledWith('/clear', { method: 'POST' })
    })

    it('should stop on some action with no flow is selected', () => {
        store.getState().flows = reduceFlows(undefined, {})
        store.dispatch(createKeyEvent(Key.LEFT))
        store.dispatch(createKeyEvent(Key.TAB))
        store.dispatch(createKeyEvent(Key.RIGHT))
        store.dispatch(createKeyEvent(Key.D))
        expect(fetchApi).not.toBeCalled()
    })

    it('should do nothing when Ctrl and undefined key is pressed ', () => {
        store.dispatch(createKeyEvent(Key.BACKSPACE, false, true))
        store.dispatch(createKeyEvent(0))
        expect(fetchApi).not.toBeCalled()
    })

    it('should close modal', () => {
        store.getState().ui.modal.activeModal = true
        store.dispatch(createKeyEvent(Key.ESC))
        expect(store.getActions()).toEqual([ {type: modalActions.HIDE_MODAL} ])
    })

})
