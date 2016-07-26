jest.unmock('../../ducks/flows')
jest.unmock('../../ducks/flowView')
jest.unmock('../../ducks/utils/view')
jest.unmock('../../ducks/utils/list')
jest.unmock('./tutils')

import { createStore } from './tutils'

import flows, * as flowActions from '../../ducks/flows'
import flowView, * as flowViewActions from '../../ducks/flowView'


function testStore() {
    let store = createStore({
        flows,
        flowView
    })
    for (let i of [1, 2, 3, 4]) {
        store.dispatch(
            flowActions.addFlow({ id: i })
        )
    }
    return store
}

describe('select relative', () => {

    function testSelect(start, relative, result) {
        const store = testStore()
        store.dispatch(flowActions.select(start))
        expect(store.getState().flows.selected).toEqual(start ? [start] : [])
        store.dispatch(flowViewActions.selectRelative(relative))
        expect(store.getState().flows.selected).toEqual([result])
    }

    describe('previous', () => {

        it('should select the previous flow', () => {
            testSelect(3, -1, 2)
        })

        it('should not changed when first flow is selected', () => {
            testSelect(1, -1, 1)
        })

        it('should select first flow if no flow is selected', () => {
            testSelect(undefined, -1, 1)
        })

    })

    describe('next', () => {

        it('should select the next flow', () => {
            testSelect(2, 1, 3)
        })

        it('should not changed when last flow is selected', () => {
            testSelect(4, 1, 4)
        })

        it('should select last flow if no flow is selected', () => {
            testSelect(undefined, 1, 4)
        })

    })
})
