import reduceUI from '../../../ducks/ui/index'

describe('reduceUI in js/ducks/ui/index.js', () => {
    it('should combine flow and header', () => {
        let state = reduceUI(undefined, {})
        expect(state.hasOwnProperty('flow')).toBeTruthy()
        expect(state.hasOwnProperty('header')).toBeTruthy()
    })
})
