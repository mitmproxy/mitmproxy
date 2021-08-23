import reduceUI from '../../../ducks/ui/index'

describe('reduceUI in js/ducks/ui/index.js', () => {
    it('should combine flow and header', () => {
        let state = reduceUI(undefined, {type: "other"})
        expect(state.hasOwnProperty('flow')).toBeTruthy()
    })
})
