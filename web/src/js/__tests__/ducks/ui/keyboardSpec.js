jest.mock('../../../utils')

import { Key } from '../../../utils'
import { onKeyDown } from '../../../ducks/ui/keyboard'
import reduceFlows from '../../../ducks/flows'
import reduceUI from '../../../ducks/ui/index'
import * as flowsActions from '../../../ducks/flows'
import * as UIActions from '../../../ducks/ui/flow'
import configureStore from 'redux-mock-store'
import { createStore } from '../tutils'
import { fetchApi } from '../../../utils'

const mockStore = configureStore()
console.debug = jest.fn()

describe('onKeyDown', () => {
    let flows = undefined
    for( let i=1; i <= 12; i++ ) {
        flows = reduceFlows(flows, {type: flowsActions.ADD, data: {id: i}, cmd: 'add'})
    }
    let store = mockStore({ flows, ui: reduceUI(undefined, {}) })
    let createKeyEvent = (keyCode, shiftKey = undefined, ctrlKey = undefined) => {
            return { keyCode, shiftKey, ctrlKey, preventDefault: jest.fn() }
    }

    it('should handle cursor up', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select(2))
        onKeyDown(createKeyEvent(Key.K))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [1], type: flowsActions.SELECT })

        onKeyDown(createKeyEvent(Key.UP))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [1], type: flowsActions.SELECT })
    })

    it('should handle cursor down', () => {
        onKeyDown(createKeyEvent(Key.J))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [3], type: flowsActions.SELECT })

        onKeyDown(createKeyEvent(Key.DOWN))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [3], type: flowsActions.SELECT })
    })

    it('should handle page down', () => {
        onKeyDown(createKeyEvent(Key.SPACE))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [12], type: flowsActions.SELECT })

        store.getState().flows = reduceFlows(flows, flowsActions.select(1))
        onKeyDown(createKeyEvent(Key.PAGE_DOWN))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [11], type: flowsActions.SELECT })
    })

    it('should handle page up', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select(11))
        onKeyDown(createKeyEvent(Key.PAGE_UP))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [1], type: flowsActions.SELECT })
    })

    it('should handle select first', () => {
        onKeyDown(createKeyEvent(Key.HOME))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [1], type: flowsActions.SELECT })
    })

    it('should handle select last', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select(1))
        onKeyDown(createKeyEvent(Key.END))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [12], type: flowsActions.SELECT })
    })

    it('should handle deselect', () => {
        onKeyDown(createKeyEvent(Key.ESC))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ flowIds: [], type: flowsActions.SELECT })
    })

    it('should handle switch to left tab', () => {
        onKeyDown(createKeyEvent(Key.LEFT))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ tab: 'details', type: UIActions.SET_TAB })
    })

    it('should handle switch to right tab', () => {
        onKeyDown(createKeyEvent(Key.TAB))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ tab: 'details', type: UIActions.SET_TAB })
    })

    it('should handle switch to left tab', () => {
        onKeyDown(createKeyEvent(Key.LEFT))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ tab: 'details', type: UIActions.SET_TAB })
    })

    it('should handle switch to right tab', () => {
        onKeyDown(createKeyEvent(Key.TAB))(store.dispatch, store.getState)
        expect(store.getActions().pop()).toEqual({ tab: 'details', type: UIActions.SET_TAB })
    })

    let tStore = createStore({ reduceFlows })
    // we need to use the real dispatch to test the actions below

    it('should handle delete action', () => {
        onKeyDown(createKeyEvent(Key.D))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/flows/1', { method: 'DELETE' })
    })

    it('should handle duplicate action', () => {
        onKeyDown(createKeyEvent(Key.D, true))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/flows/1/duplicate', { method: 'POST' })
    })

    it('should handle resume action', () => {
        // resume all
        onKeyDown(createKeyEvent(Key.A, true))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/flows/resume', { method: 'POST' })
        // resume
        store.getState().flows.byId[store.getState().flows.selected[0]].intercepted = true
        onKeyDown(createKeyEvent(Key.A))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/flows/1/resume', { method: 'POST' })
    })

    it('should handle replay action', () => {
        onKeyDown(createKeyEvent(Key.R))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/flows/1/replay', { method: 'POST' })
    })

    it('should handle revert action', () => {
        store.getState().flows.byId[store.getState().flows.selected[0]].modified = true
        onKeyDown(createKeyEvent(Key.V))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/flows/1/revert', { method: 'POST' })
    })

    it('should handle kill action', () => {
        // kill all
        onKeyDown(createKeyEvent(Key.X, true))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/flows/kill', { method: 'POST' })
        // kill
        onKeyDown(createKeyEvent(Key.X))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/flows/1/kill', { method: 'POST' })
    })

    it('should handle clear action', () => {
        onKeyDown(createKeyEvent(Key.Z))(tStore.dispatch, store.getState)
        expect(fetchApi).toBeCalledWith('/clear', { method: 'POST' })
    })

    it('should stop on some action with no flow is selected', () => {
        fetchApi.mockClear()
        store.getState().flows = reduceFlows(undefined, {})
        onKeyDown(createKeyEvent(Key.LEFT))(tStore.dispatch, store.getState)
        onKeyDown(createKeyEvent(Key.TAB))(tStore.dispatch, store.getState)
        onKeyDown(createKeyEvent(Key.RIGHT))(tStore.dispatch, store.getState)
        onKeyDown(createKeyEvent(Key.D))(tStore.dispatch, store.getState)
        expect(fetchApi).not.toBeCalled()
    })

    it('should do nothing when Ctrl and undefined key is pressed ', () => {
        onKeyDown(createKeyEvent(Key.BACKSPACE, false, true))(tStore.dispatch, store.getState)
        onKeyDown(createKeyEvent(0))(tStore.dispatch, store.getState)
        expect(fetchApi).not.toBeCalled()
    })

})
