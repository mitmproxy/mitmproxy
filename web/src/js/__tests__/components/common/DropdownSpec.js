import React from 'react'
import renderer from 'react-test-renderer'
import Dropdown, { Divider } from '../../../components/common/Dropdown'

describe('Dropdown Component', () => {
    let dropdown = renderer.create(<Dropdown text="open me">
            <a href="#">1</a>
            <a href="#">2</a>
        </Dropdown>)

    it('should render correctly', () => {
        let tree = dropdown.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle open/close action', () => {
        let tree = dropdown.toJSON(),
            e = { preventDefault: jest.fn(), stopPropagation: jest.fn() }
        tree.children[0].props.onClick(e)
        expect(tree).toMatchSnapshot()

        // click action when the state is open
        tree.children[0].props.onClick(e)

        // open again
        tree.children[0].props.onClick(e)

        // close
        document.body.click()
        expect(tree).toMatchSnapshot()
    })
})
