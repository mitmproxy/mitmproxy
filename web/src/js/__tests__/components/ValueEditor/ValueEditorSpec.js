import React from 'react'
import renderer from 'react-test-renderer'
import TestUtils from 'react-dom/test-utils'
import ValueEditor from '../../../components/ValueEditor/ValueEditor'
import { Key } from '../../../utils'

describe('ValueEditor Component', () => {

    let mockFn = jest.fn()
    it ('should render correctly', () => {
        let valueEditor = renderer.create(
            <ValueEditor content="foo" onDone={mockFn}/>
        ),
            tree = valueEditor.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let valueEditor = TestUtils.renderIntoDocument(
        <ValueEditor content="<script>foo</script>" onDone={mockFn}/>
    )
    it('should handle this.blur', () => {
        valueEditor.input.blur = jest.fn()
        valueEditor.blur()
        expect(valueEditor.input.blur).toHaveBeenCalled()
    })

    it('should handle reset', () => {
        valueEditor.reset()
        expect(valueEditor.input.innerHTML).toEqual(
            "&lt;script&gt;foo&lt;/script&gt;"
        )
    })

    it('should handle paste', () => {
        let mockEvent = {
            preventDefault: jest.fn(),
            clipboardData: { getData: (t) => "foo content"}
        }
        document.execCommand = jest.fn()
        valueEditor.onPaste(mockEvent)
        expect(document.execCommand).toBeCalledWith('insertHTML', false, "foo content")
    })

    it('should handle mouseDown', () => {
        window.addEventListener = jest.fn()
        valueEditor.onMouseDown({})
        expect(valueEditor._mouseDown).toBeTruthy()
        expect(window.addEventListener).toBeCalledWith('mouseup', valueEditor.onMouseUp)
    })

    it('should handle mouseUp', () => {
        window.removeEventListener = jest.fn()
        valueEditor.onMouseUp()
        expect(window.removeEventListener).toBeCalledWith('mouseup', valueEditor.onMouseUp)
    })

    it('should handle focus', () => {
        let mockEvent = { clientX: 1, clientY: 2 },
            mockSelection = {
                rangeCount: 1,
                getRangeAt: jest.fn( (index) => {return { selectNodeContents: jest.fn() }}),
                removeAllRanges: jest.fn(),
                addRange: jest.fn()
            },
            clearState = (v) => {
                v._mouseDown = false
                v._ignore_events = false
                v.state.editable = false
            }
        window.getSelection = () => mockSelection

        // return undefined when mouse down
        valueEditor.onMouseDown()
        expect(valueEditor.onFocus(mockEvent)).toEqual(undefined)
        valueEditor.onMouseUp()

        // sel.rangeCount > 0
        valueEditor.onFocus(mockEvent)
        expect(mockSelection.getRangeAt).toBeCalledWith(0)
        expect(valueEditor.state.editable).toBeTruthy()
        expect(mockSelection.removeAllRanges).toBeCalled()
        expect(mockSelection.addRange).toBeCalled()
        clearState(valueEditor)

        // document.caretPositionFromPoint
        mockSelection.rangeCount = 0
        let mockRange = { setStart: jest.fn(), selectNodeContents: jest.fn() }

        document.caretPositionFromPoint = jest.fn((x, y) => {
            return { offsetNode: 0, offset: x + y}
        })
        document.createRange = jest.fn(() => mockRange)
        valueEditor.onFocus(mockEvent)
        expect(mockRange.setStart).toBeCalledWith(0, 3)
        clearState(valueEditor)
        document.caretPositionFromPoint = null

        //document.caretRangeFromPoint
        document.caretRangeFromPoint = jest.fn(() => mockRange)
        valueEditor.onFocus(mockEvent)
        expect(document.caretRangeFromPoint).toBeCalledWith(1, 2)
        clearState(valueEditor)
        document.caretRangeFromPoint = null

        //else
        valueEditor.onFocus(mockEvent)
        expect(mockRange.selectNodeContents).toBeCalledWith(valueEditor.input)
        clearState(valueEditor)
    })

    it('should handle click', () => {
        valueEditor.onMouseUp = jest.fn()
        valueEditor.onFocus = jest.fn()
        valueEditor.onClick('foo')
        expect(valueEditor.onMouseUp).toBeCalled()
        expect(valueEditor.onFocus).toBeCalledWith('foo')
    })

    it('should handle blur', () => {
        // return undefined
        valueEditor._ignore_events = true
        expect(valueEditor.onBlur({})).toEqual(undefined)
        // else
        valueEditor._ignore_events = false
        valueEditor.onBlur({})
        expect(valueEditor.state.editable).toBeFalsy()
        expect(valueEditor.props.onDone).toBeCalledWith(valueEditor.input.textContent)
    })

    it('should handle key down', () => {
        let mockKeyEvent = (keyCode, shiftKey=false) => {
            return {
                keyCode: keyCode,
                shiftKey: shiftKey,
                stopPropagation: jest.fn(),
                preventDefault: jest.fn()
            }
        }
        valueEditor.reset = jest.fn()
        valueEditor.blur = jest.fn()
        valueEditor.onKeyDown(mockKeyEvent(Key.ESC))
        expect(valueEditor.reset).toBeCalled()
        expect(valueEditor.blur).toBeCalled()
        valueEditor.blur.mockReset()

        valueEditor.onKeyDown(mockKeyEvent(Key.ENTER))
        expect(valueEditor.blur).toBeCalled()

        valueEditor.onKeyDown(mockKeyEvent(Key.SPACE))
    })

    it('should handle input', () => {
        valueEditor.onInput()
    })
})
