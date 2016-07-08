jest.unmock('lodash')
jest.unmock('redux')
jest.unmock('redux-thunk')
jest.unmock('../../ducks/ui')
jest.unmock('../../ducks/views/main')

import _ from 'lodash'
import thunk from 'redux-thunk'
import { applyMiddleware, createStore, combineReducers } from 'redux'
import reducer, { setActiveMenu, selectTabRelative } from '../../ducks/ui'
import { SELECT } from '../../ducks/views/main'

describe('ui reducer', () => {
    it('should return the initial state', () => {
        expect(reducer(undefined, {}).activeMenu).toEqual('Start')
    })

    it('should return the state for view', () => {
        expect(reducer(undefined, setActiveMenu('View')).activeMenu).toEqual('View')
    })

    it('should change the state to Start when deselecting a flow and we a currently at the flow tab', () => {
        expect(reducer({ activeMenu: 'Flow' }, {
            type: SELECT,
            currentSelection: 1,
            flowId : undefined,
        }).activeMenu).toEqual('Start')
    })

    it('should change the state to Flow when we selected a flow and no flow was selected before', () => {
        expect(reducer({ activeMenu: 'Start' }, {
            type: SELECT,
            currentSelection: undefined,
            flowId : 1,
        }).activeMenu).toEqual('Flow')
    })

    it('should not change the state to Flow when OPTIONS tab is selected and we selected a flow and a flow as selected before', () => {
        expect(reducer({activeMenu: 'Options'}, {
            type: SELECT,
            currentSelection: 1,
            flowId : '2',
        }).activeMenu).toEqual('Options')
    })

    describe('select tab relative', () => {

        it('should select tab according to flow properties', () => {
            const store = createTestStore(makeState([{ id: 1 }], 1))
            store.dispatch(selectTabRelative(1))
            expect(store.getState().ui.panel).toEqual('details')
        })

        it('should select last tab when first tab is selected', () => {
            const store = createTestStore(makeState([{ id: 1, request: true, response: true, error: true }], 1))
            store.dispatch(selectTabRelative(-1))
            expect(store.getState().ui.panel).toEqual('details')
        })

    })
})

function createTestStore(state) {
    return createStore(
        combineReducers({ ui: reducer, flows: (state = {}) => state }),
        state,
        applyMiddleware(thunk)
    )
}

function makeState(flows, selected) {
    return {
        flows: {
            list: {
                data: flows,
                byId: _.fromPairs(flows.map(flow => [flow.id, flow])),
                indexOf: _.fromPairs(flows.map((flow, index) => [flow.id, index])),
            },
            views: {
                main: {
                    selected: [selected],
                },
            },
        },
    }
}
