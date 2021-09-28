import * as React from "react"
import renderer from 'react-test-renderer'
import ToggleButton from '../../../components/common/ToggleButton'

describe('ToggleButton Component', () => {
    let mockFunc = jest.fn()

    it('should render correctly', () => {
        let checkedButton = renderer.create(
                <ToggleButton checked={true} onToggle={mockFunc} text="foo"/>),
        tree = checkedButton.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle click action', () => {
        let uncheckButton = renderer.create(
            <ToggleButton checked={false} onToggle={mockFunc} text="foo"/>),
        tree = uncheckButton.toJSON()
        tree.props.onClick()
        expect(mockFunc).toBeCalled()
    })
})
