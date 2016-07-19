jest.unmock('../../../ducks/views/main');
jest.unmock('../../../ducks/utils/view');
jest.unmock('redux-thunk')
jest.unmock('redux')

import reduce, { selectRelative } from '../../../ducks/views/main';
import thunk from 'redux-thunk'
import { applyMiddleware, createStore, combineReducers } from 'redux'

describe('main reduce', () => {

    describe('select previous', () => {

        it('should not changed when first flow is selected', () => {
            const flows = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }]
            const store = createTestStore(makeState(flows, 1))
            store.dispatch(selectRelative(-1))
            expect(store.getState().flows.views.main.selected).toEqual([1])
        })

        it('should select last flow if no flow is selected', () => {
            const flows = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }]
            const store = createTestStore(makeState(flows))
            store.dispatch(selectRelative(-1))
            expect(store.getState().flows.views.main.selected).toEqual([4])
        })

    })

    describe('select next', () => {

        it('should not change when last flow is selected', () => {
            const flows = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }]
            const store = createTestStore(makeState(flows, 4))
            store.dispatch(selectRelative(1))
            expect(store.getState().flows.views.main.selected).toEqual([4])
        })

        it('should select first flow if no flow is selected', () => {
            const flows = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }]
            const store = createTestStore(makeState(flows, 1))
            store.dispatch(selectRelative(1))
            expect(store.getState().flows.views.main.selected).toEqual([2])
        })

    })
})

function createTestStore(defaultState) {
    return createStore(
        (state = defaultState, action) => ({
            flows: {
                ...state.flows,
                views: {
                    main: reduce(state.flows.views.main, action)
                }
            }
        }),
        defaultState,
        applyMiddleware(thunk)
    )
}

// TODO: We should not duplicate our reducer logic here.
function makeState(flows, selected) {
    const list = {
        data: flows,
        byId: _.fromPairs(flows.map(flow => [flow.id, flow])),
        indexOf: _.fromPairs(flows.map((flow, index) => [flow.id, index])),
    }

    return {
        flows: {
            list,
            views: {
                main: {
                    selected: [selected],
                    view: list,
                }
            }
        }
    }
}
