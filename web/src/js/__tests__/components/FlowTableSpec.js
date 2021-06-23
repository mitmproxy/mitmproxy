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
                    <FlowTable selectFlow={selectFn} flows={[tflow]}/>
                </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let provider = renderer.create(
        <Provider store={store} >
            <FlowTable selectFlow={selectFn} flows={[tflow]}/>
        </Provider>),
        flowTable = provider.root.findByType(FlowTable)

    it('should handle componentWillUnmount', () => {
        flowTable.instance.UNSAFE_componentWillUnmount()
        expect(window.addEventListener).toBeCalledWith('resize', flowTable.instance.onViewportUpdate)
    })

    it('should handle componentDidUpdate', () => {
        // flowTable.shouldScrollIntoView == false
        expect(flowTable.instance.componentDidUpdate()).toEqual(undefined)
        // rowTop - headHeight < viewportTop
        flowTable.instance.shouldScrollIntoView = true
        flowTable.instance.componentDidUpdate()
        // rowBottom > viewportTop + viewportHeight
        flowTable.instance.shouldScrollIntoView = true
        flowTable.instance.componentDidUpdate()
    })

    it('should handle componentWillReceiveProps', () => {
        flowTable.instance.UNSAFE_componentWillReceiveProps({selected: tflow})
        expect(flowTable.instance.shouldScrollIntoView).toBeTruthy()
    })
})
