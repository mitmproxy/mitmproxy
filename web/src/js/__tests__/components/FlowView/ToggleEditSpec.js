// jest.mock('../../../ducks/ui/flow')
import React from 'react'
import renderer from 'react-test-renderer'
import ToggleEdit from '../../../components/FlowView/ToggleEdit'
import { Provider } from 'react-redux'
import { startEdit, stopEdit } from '../../../ducks/ui/flow'
import { TFlow, TStore } from '../../ducks/tutils'

global.fetch = jest.fn()
let tflow = new TFlow()

describe('ToggleEdit Component', () => {
    let store = TStore(),
        provider = renderer.create(
        <Provider store={store}>
            <ToggleEdit/>
        </Provider>),
        tree = provider.toJSON()

    afterEach(() => { store.clearActions() })

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle click on stopEdit', () => {
        tree.children[0].props.onClick()
        expect(fetch).toBeCalled()
    })

    it('should handle click on startEdit', () => {
        store.getState().ui.flow.modifiedFlow = false
        let provider = renderer.create(
            <Provider store={store}>
                <ToggleEdit/>
            </Provider>),
            tree = provider.toJSON()
        tree.children[0].props.onClick()
        expect(store.getActions()).toEqual([startEdit(tflow)])
    })
})
