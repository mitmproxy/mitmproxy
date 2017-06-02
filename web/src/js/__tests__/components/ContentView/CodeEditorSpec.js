jest.mock('react-codemirror')
import React from 'react'
import renderer from 'react-test-renderer'
import CodeEditor from '../../../components/ContentView/CodeEditor'

describe('CodeEditor Component', () => {
    let content = "foo content",
        changeFn = jest.fn(),
        codeEditor = renderer.create(
            <CodeEditor content={content} onChange={changeFn}/>
        ),
        tree = codeEditor.toJSON()
    
    it('should render correctly', () => {
        // This actually does not render properly, but getting a full CodeMirror rendering
        // is cumbersome. This is hopefully good enough.
        // see: https://github.com/mitmproxy/mitmproxy/pull/2365#discussion_r119766850
        expect(tree).toMatchSnapshot()
    })

    it('should handle key down', () => {
        let mockEvent = { stopPropagation: jest.fn() }
        tree.props.onKeyDown(mockEvent)
        expect(mockEvent.stopPropagation).toBeCalled()
    })
})
