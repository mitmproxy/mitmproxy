import React from 'react'
import ReactDOM from 'react-dom'
import renderer from 'react-test-renderer'
import TestUtils from 'react-dom/test-utils'
import Headers, { HeaderEditor } from '../../../components/FlowView/Headers'
import { Key } from '../../../utils'

describe('HeaderEditor Component', () => {

    it('should render correctly', () => {
        let headerEditor = renderer.create(
            <HeaderEditor content="foo" onDone={jest.fn()}/>),
        tree = headerEditor.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let doneFn = jest.fn(),
        removeFn = jest.fn(),
        tabFn = jest.fn(),
        headerEditor = TestUtils.renderIntoDocument(
        <HeaderEditor content="foo" onDone={doneFn} onRemove={removeFn} onTab={tabFn}/>)

    it('should handle focus', () => {
        let focusFn = jest.fn()
        ReactDOM.findDOMNode = jest.fn( node => {
            return {focus: focusFn}
        })
        headerEditor.focus()
        expect(ReactDOM.findDOMNode).toBeCalledWith(headerEditor)
        expect(focusFn).toBeCalled()
    })

    it('should handle keyDown', () => {
        let mockEvent = { keyCode: Key.BACKSPACE },
            getRangeAt = jest.fn( s => {
                return { startOffset: 0, endOffset: 0 }
            })
        window.getSelection = jest.fn(selection => {
            return { getRangeAt }
        })
        // Backspace
        headerEditor.onKeyDown(mockEvent)
        expect(window.getSelection).toBeCalled()
        expect(getRangeAt).toBeCalledWith(0)
        expect(headerEditor.props.onRemove).toBeCalledWith(mockEvent)
        // Enter & Tab
        mockEvent.keyCode = Key.ENTER
        headerEditor.onKeyDown(mockEvent)
        expect(headerEditor.props.onTab).toBeCalledWith(mockEvent)
    })
})

describe('Headers Component', () => {
    let changeFn = jest.fn(),
        mockMessage = { headers: [['k1', 'v1'], ['k2', '']] }
    it('should handle correctly', () => {
        let headers = renderer.create(<Headers onChange={changeFn} message={mockMessage}/>),
            tree = headers.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let headers = TestUtils.renderIntoDocument(<Headers onChange={changeFn} message={mockMessage}/>),
        headerEditors = TestUtils.scryRenderedComponentsWithType(headers, HeaderEditor),
        key1Editor = headerEditors[0],
        value1Editor = headerEditors[1],
        key2Editor = headerEditors[2],
        value2Editor = headerEditors[3]

    it('should handle change on header name', () => {
        key2Editor.props.onDone('')
        expect(changeFn).toBeCalled()
        expect(headers._nextSel).toEqual('0-value')
        changeFn.mockClear()
    })

    it('should handle change on header value', () => {
        value2Editor.props.onDone('')
        expect(changeFn).toBeCalled()
        expect(headers._nextSel).toEqual('0-value')
        changeFn.mockClear()
    })

    let mockEvent = { preventDefault: jest.fn() }
    it('should handle remove on header name', () => {
        key2Editor.props.onRemove(mockEvent)
        expect(mockEvent.preventDefault).toBeCalled()
        mockEvent.preventDefault.mockClear()
    })

    it('should handle remove on header value', () => {
        value2Editor.props.onRemove(mockEvent)
        expect(mockEvent.preventDefault).toBeCalled()
        mockEvent.preventDefault.mockClear()
    })

    it('should handle tab on header name', () => {
        key1Editor.props.onTab(mockEvent)
        expect(headers._nextSel).toEqual('0-value')
    })

    it('should handle tab on header value', () => {
        value1Editor.props.onTab(mockEvent)
        expect(headers._nextSel).toEqual('1-key')

        value2Editor.props.onTab(mockEvent)
        expect(mockEvent.preventDefault).toBeCalled()
        expect(headers._nextSel).toEqual('2-key')
    })

    it('should handle componentDidUpdate', () => {
        headers._nextSel = '1-value'
        headers.refs['1-value'] = { focus: jest.fn() }
        headers.componentDidUpdate()
        expect(headers.refs['1-value'].focus).toBeCalled()
        expect(headers._nextSel).toEqual(undefined)
    })

    it('should handle edit', () => {
        headers.refs['0-key'] = { focus: jest.fn() }
        headers.edit()
        expect(headers.refs['0-key'].focus).toBeCalled()
    })

    it('should not delete last row when handle remove', () => {
        mockMessage = { headers: [['', '']] }
        headers = TestUtils.renderIntoDocument(<Headers onChange={changeFn} message={mockMessage}/>)
        headers.onChange(0, 0, '')
        expect(changeFn).toBeCalledWith([['Name', 'Value']])

    })

})
