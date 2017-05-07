import reducer, { setActiveMenu } from '../../../ducks/ui/header'
import * as flowActions from '../../../ducks/flows'

describe('header reducer', () => {
    it('should return the initial state', () => {
        expect(reducer(undefined, {}).activeMenu).toEqual('Start')
    })

    it('should return the state for view', () => {
        expect(reducer(undefined, setActiveMenu('View')).activeMenu).toEqual('View')
    })

    it('should change the state to Start when deselecting a flow and we a currently at the flow tab', () => {
        expect(reducer(
            { activeMenu: 'Flow', isFlowSelected: true },
            flowActions.select(undefined)).activeMenu
        ).toEqual('Start')
    })

    it('should change the state to Flow when we selected a flow and no flow was selected before', () => {
        expect(reducer(
            { activeMenu: 'Start', isFlowSelected: false },
            flowActions.select(1)).activeMenu
        ).toEqual('Flow')
    })

    it('should not change the state to Flow when OPTIONS tab is selected and we selected a flow and a flow as selected before', () => {
        expect(reducer(
            { activeMenu: 'Options', isFlowSelected: true },
            flowActions.select(1)
        ).activeMenu).toEqual('Options')
    })
})
