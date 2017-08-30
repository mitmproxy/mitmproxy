import reduceOptions, * as OptionsActions from '../../ducks/options'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import * as OptionsEditorActions from '../../ducks/ui/optionsEditor'

const mockStore = configureStore([ thunk ])

describe('option reducer', () => {
    it('should return initial state', () => {
        expect(reduceOptions(undefined, {})).toEqual({})
    })

    it('should handle receive action', () => {
        let action = { type: OptionsActions.RECEIVE, data: 'foo' }
        expect(reduceOptions(undefined, action)).toEqual('foo')
    })

    it('should handle update action', () => {
        let action = {type: OptionsActions.UPDATE, data: {id: 1} }
        expect(reduceOptions(undefined, action)).toEqual({id: 1})
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

    it('should handle error', () => {
        let mockResponse = { status: 400, text: p => Promise.resolve('error') },
            promise = Promise.resolve(mockResponse)
        global.fetch = r => { return promise }
        OptionsActions.pureSendUpdate('bar', 'error')
        expect(store.getActions()).toEqual([
            { type: OptionsEditorActions.OPTION_UPDATE_SUCCESS, option: 'foo'}
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
