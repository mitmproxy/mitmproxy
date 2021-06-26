import reduceOptions, * as OptionsActions from '../../ducks/options'

import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import * as OptionsEditorActions from '../../ducks/ui/optionsEditor'
import {updateError} from "../../ducks/ui/optionsEditor";

const mockStore = configureStore([ thunk ])

describe('option reducer', () => {
    it('should return initial state', () => {
        expect(reduceOptions(undefined, {})).toEqual(OptionsActions.defaultState)
    })

    it('should handle receive action', () => {
        let action = { type: OptionsActions.RECEIVE, data: {id: {value: 'foo'} } }
        expect(reduceOptions(undefined, action)).toEqual({id: 'foo'})
    })

    it('should handle update action', () => {
        let action = {type: OptionsActions.UPDATE, data: {id: {value: 1} } }
        expect(reduceOptions(undefined, action)).toEqual({...OptionsActions.defaultState, id: 1})
    })
})

let store = mockStore()

describe('option actions', () => {

    it('should be possible to update option', () => {
        let mockResponse = { status: 200 },
            promise = Promise.resolve(mockResponse)
        global.fetch = r => { return promise }
        store.dispatch(OptionsActions.update('foo', 'bar'))
        expect(store.getActions()).toEqual([
            { type: OptionsEditorActions.OPTION_UPDATE_START, option: 'foo', value: 'bar'}
        ])
        store.clearActions()
    })
})

describe('sendUpdate', () => {

    it('should handle error', async () => {
        global.fetch = () => Promise.reject("fooerror");
        await store.dispatch(OptionsActions.pureSendUpdate("bar", "error"))
        expect(store.getActions()).toEqual([
            OptionsEditorActions.updateError("bar", "fooerror")
        ])
    })
})

describe('save', () => {

    it('should dump options', () => {
        global.fetch = jest.fn()
        store.dispatch(OptionsActions.save())
        expect(fetch).toBeCalledWith(
            './options/save?_xsrf=undefined',
            {
                credentials: "same-origin",
                method: "POST"
            }
        )
    })
})
