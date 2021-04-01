import React from 'react'
import renderer from 'react-test-renderer'
import FileChooser from '../../../components/common/FileChooser'

describe('FileChooser Component', () => {
    let openFileFunc = jest.fn(),
        createNodeMock = () => { return { click: jest.fn() } },
        fileChooser = renderer.create(
            <FileChooser className="foo" title="bar" onOpenFile={ openFileFunc }/>
        , { createNodeMock })
        //[test refs with react-test-renderer](https://github.com/facebook/react/issues/7371)

    it('should render correctly', () => {
        let tree = fileChooser.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle click action', () => {
        let tree = fileChooser.toJSON(),
            mockEvent = {
                preventDefault: jest.fn(),
                target: {
                    files: [ "foo", "bar" ]
                }
            }
        tree.children[1].props.onChange(mockEvent)
        expect(openFileFunc).toBeCalledWith("foo")
        tree.props.onClick()
        // without files
        mockEvent = {
            ...mockEvent,
            target: { files: [ ]}
        }
        openFileFunc.mockClear()
        tree.children[1].props.onChange(mockEvent)
        expect(openFileFunc).not.toBeCalled()
    })
})
