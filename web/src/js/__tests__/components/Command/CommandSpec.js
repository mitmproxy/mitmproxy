import React from 'react'
import renderer from 'react-test-renderer'
import CommandBar from '../../../components/CommandBar'

describe('CommandBar Component', () => {
    let commandBar = renderer.create(
            <CommandBar />),
        tree = commandBar.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })
})
