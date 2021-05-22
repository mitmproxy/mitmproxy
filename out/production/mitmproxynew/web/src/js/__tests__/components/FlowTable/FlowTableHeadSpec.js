import React from 'react'
import renderer from 'react-test-renderer'
import ConnectedHead, { FlowTableHead } from '../../../components/FlowTable/FlowTableHead'
import { Provider } from 'react-redux'
import { TStore } from '../../ducks/tutils'


describe('FlowTableHead Component', () => {
    let sortFn = jest.fn(),
        store = TStore(),
        flowTableHead = renderer.create(
            <Provider store={store}>
                <FlowTableHead setSort={sortFn} sortDesc={true}/>
            </Provider>),
        tree =flowTableHead.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle click', () => {
        tree.children[0].props.onClick()
        expect(sortFn).toBeCalledWith('TLSColumn', false)
    })

    it('should connect to state', () => {
        let store = TStore(),
            provider = renderer.create(
                <Provider store={store}>
                    <ConnectedHead/>
                </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
