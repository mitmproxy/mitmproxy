import {rootReducer} from '../../ducks/index'

describe('reduceState in js/ducks/index.js', () => {
    it('should combine flow and header', () => {
        let state = rootReducer(undefined, {type: "other"})
        expect(state.hasOwnProperty('eventLog')).toBeTruthy()
        expect(state.hasOwnProperty('flows')).toBeTruthy()
        expect(state.hasOwnProperty('connection')).toBeTruthy()
        expect(state.hasOwnProperty('ui')).toBeTruthy()
    })
})
