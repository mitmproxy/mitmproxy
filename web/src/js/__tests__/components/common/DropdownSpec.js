import React from 'react'
import renderer from 'react-test-renderer'
import Dropdown, { Divider } from '../../../components/common/Dropdown'

describe('Dropdown Component', () => {
    let dropup = renderer.create(<Dropdown dropup btnClass="foo">
            <a href="#">1</a>
            <Divider/>
            <a href="#">2</a>
        </Dropdown>),
        dropdown = renderer.create(<Dropdown btnClass="foo">
            <a href="#">1</a>
            <a href="#">2</a>
        </Dropdown>)

    it('should render correctly', () => {
        let tree = dropup.toJSON()
        expect(tree).toMatchSnapshot()

        tree = dropdown.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle open/close action', () => {
        document.body.addEventListener('click', ()=>{})
        let tree = dropup.toJSON(),
            e = { preventDefault: jest.fn(), stopPropagation: jest.fn() }
        tree.children[0].props.onClick(e)
        expect(tree).toMatchSnapshot()

        // click action when the state is open
        tree.children[0].props.onClick(e)

        // close
        document.body.click()
        expect(tree).toMatchSnapshot()
    })
})
