jest.unmock('../../ducks/flows');

import reduceFlows, * as flowActions from '../../ducks/flows'
import * as storeActions from '../../ducks/utils/store'


describe('select flow', () => {

    let state = reduceFlows(undefined, {})
    for (let i of [1, 2, 3, 4]) {
        state = reduceFlows(state, storeActions.add({ id: i }))
    }

    it('should be possible to select a single flow', () => {
        expect(reduceFlows(state, flowActions.select(2))).toEqual(
            {
                ...state,
                selected: [2],
            }
        )
    })

    it('should be possible to deselect a flow', () => {
        expect(reduceFlows({ ...state, selected: [1] }, flowActions.select())).toEqual(
            {
                ...state,
                selected: [],
            }
        )
    })
})
