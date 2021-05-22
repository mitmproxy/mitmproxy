import React from 'react'
import renderer from 'react-test-renderer'
import ToggleInputButton from '../../../components/common/ToggleInputButton'
import { Key } from '../../../utils'

describe('ToggleInputButton Component', () => {
    let mockFunc = jest.fn(),
        toggleInputButton = undefined,
        tree = undefined

    it('should render correctly', () => {
        toggleInputButton = renderer.create(
            <ToggleInputButton checked={true} name="foo" onToggleChanged={mockFunc}
                               placeholder="bar">text</ToggleInputButton>)
        tree = toggleInputButton.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle keydown and click action', () => {
        toggleInputButton = renderer.create(
            <ToggleInputButton checked={false} name="foo" onToggleChanged={mockFunc}
                               placeholder="bar" txt="txt">text</ToggleInputButton>)
        tree = toggleInputButton.toJSON()
        let mockEvent = {
            keyCode: Key.ENTER,
            stopPropagation: jest.fn()
        }

        tree.children[1].props.onKeyDown(mockEvent)
        expect(mockFunc).toBeCalledWith("txt")

        tree.children[0].props.onClick()
        expect(mockFunc).toBeCalledWith("txt")
    })

    it('should update state onChange', () => {
        // trigger onChange
        tree.children[1].props.onChange({ target: { value: "foo" }})
        // update the tree
        tree = toggleInputButton.toJSON()
        expect(tree.children[1].props.value).toEqual("foo")
    })
})
