import React from 'react'
import renderer from 'react-test-renderer'
import {PureFlowTable as FlowTable} from '../../components/FlowTable'
import TestUtils from 'react-dom/test-utils'
import { TFlow, TStore } from '../ducks/tutils'
import { Provider } from 'react-redux'

window.addEventListener = jest.fn()

describe('FlowTable Component', () => {
    let selectFn = jest.fn(),
        tflow = TFlow(),
        store = TStore()

    it('should render correctly', () => {
        let provider = renderer.create(
                <Provider store={store}>
                    <FlowTable onSelect={selectFn} flows={[tflow]}/>
                </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let provider = TestUtils.renderIntoDocument(
        <Provider store={store} >
            <FlowTable onSelect={selectFn} flows={[tflow]}/>
        </Provider>),
        flowTable = TestUtils.findRenderedComponentWithType(provider, FlowTable)

    it('should handle componentWillUnmount', () => {
        flowTable.componentWillUnmount()
        expect(window.addEventListener).toBeCalledWith('resize', flowTable.onViewportUpdate)
    })

    it('should handle componentDidUpdate', () => {
        // flowTable.shouldScrollIntoView == false
        expect(flowTable.componentDidUpdate()).toEqual(undefined)
        // rowTop - headHeight < viewportTop
        flowTable.shouldScrollIntoView = true
        flowTable.componentDidUpdate()
        // rowBottom > viewportTop + viewportHeight
        flowTable.shouldScrollIntoView = true
        flowTable.componentDidUpdate()
    })

    it('should handle componentWillReceiveProps', () => {
        flowTable.componentWillReceiveProps({selected: tflow})
        expect(flowTable.shouldScrollIntoView).toBeTruthy()
    })
})
