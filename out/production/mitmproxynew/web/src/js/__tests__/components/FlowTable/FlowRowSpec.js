import React from 'react'
import renderer from 'react-test-renderer'
import FlowRow from '../../../components/FlowTable/FlowRow'
import { TFlow, TStore } from '../../ducks/tutils'
import { Provider } from 'react-redux'

describe('FlowRow Component', () => {
    let tFlow = new TFlow(),
        selectFn = jest.fn(),
        store = TStore(),
        flowRow = renderer.create(
            <Provider store={store} >
                <FlowRow flow={tFlow} onSelect={selectFn}/>
            </Provider>),
        tree = flowRow.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle click', () => {
        tree.props.onClick()
        expect(selectFn).toBeCalledWith(tFlow.id)
    })

})
