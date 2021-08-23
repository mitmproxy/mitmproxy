import reduceEventLog, * as eventLogActions from '../../ducks/eventLog'
import {reduce} from '../../ducks/utils/store'

describe('event log reducer', () => {
    it('should return initial state', () => {
        expect(reduceEventLog(undefined, {})).toEqual({
            visible: false,
            filters: { debug: false, info: true, web: true, warn: true, error: true },
            ...reduce(undefined, {}),
        })
    })

    it('should be possible to toggle filter', () => {
        let state = reduceEventLog(undefined, eventLogActions.add('foo'))
        expect(reduceEventLog(state, eventLogActions.toggleFilter('info'))).toEqual({
            visible: false,
            filters: { ...state.filters, info: false},
            ...reduce(state, {})
        })
    })

    it('should be possible to toggle visibility', () => {
        let state = reduceEventLog(undefined, {})
        expect(reduceEventLog(state, eventLogActions.toggleVisibility())).toEqual({
            visible: true,
            filters: {...state.filters},
            ...reduce(undefined, {})
        })
    })

    it('should be possible to add message', () => {
        let state = reduceEventLog(undefined, eventLogActions.add('foo'))
        expect(state.visible).toBeFalsy()
        expect(state.filters).toEqual({
            debug: false, info: true, web: true, warn: true, error: true
        })
    })
})
