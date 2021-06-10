import React from 'react'
import renderer from 'react-test-renderer'
import TestUtils from 'react-dom/test-utils'
import ValidateEditor from '../../../components/ValueEditor/ValidateEditor'

describe('ValidateEditor Component', () => {
    let validateFn = jest.fn( content => content.length == 3),
        doneFn = jest.fn()

    it('should render correctly', () => {
        let validateEditor = renderer.create(
            <ValidateEditor content="foo" onDone={doneFn} isValid={validateFn}/>
        ),
            tree = validateEditor.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let validateEditor = TestUtils.renderIntoDocument(
        <ValidateEditor content="foo" onDone={doneFn} isValid={validateFn}/>
    )
    it('should handle componentWillReceiveProps', () => {
        let mockProps = {
            isValid: s => s.length == 3,
            content: "bar"
        }
        validateEditor.UNSAFE_componentWillReceiveProps(mockProps)
        expect(validateEditor.state.valid).toBeTruthy()
        validateEditor.UNSAFE_componentWillReceiveProps({...mockProps, content: "bars"})
        expect(validateEditor.state.valid).toBeFalsy()

    })

    it('should handle input', () => {
        validateEditor.onInput("foo bar")
        expect(validateFn).toBeCalledWith("foo bar")
    })

    it('should handle done', () => {
        // invalid
        validateEditor.editor.reset = jest.fn()
        validateEditor.onDone("foo bar")
        expect(validateEditor.editor.reset).toBeCalled()
        // valid
        validateEditor.onDone("bar")
        expect(doneFn).toBeCalledWith("bar")
    })
})
