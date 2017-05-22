import React from 'react'
import renderer from 'react-test-renderer'
import FlowRow from '../../../components/FlowTable/FlowRow'
import { TFlow } from '../../ducks/tutils'

describe('FlowRow Component', () => {
    let tFlow = new TFlow(),
        selectFn = jest.fn(),
        flowRow = renderer.create(<FlowRow flow={tFlow} onSelect={selectFn}/>),
        tree = flowRow.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle click', () => {
        tree.props.onClick()
        expect(selectFn).toBeCalledWith(tFlow.id)
    })

})
