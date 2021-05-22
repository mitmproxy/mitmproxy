import React from 'react'
import renderer from 'react-test-renderer'
import Button from '../../../components/common/Button'

describe('Button Component', () => {

    it('should render correctly', () => {
        let button = renderer.create(
            <Button className="classname" onClick={() => "onclick"} title="title" icon="icon">
                <a>foo</a>
            </Button>
        ),
            tree = button.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should be able to be disabled', () => {
        let button = renderer.create(
            <Button className="classname" onClick={() => "onclick"} disabled="true" children="children">
                <a>foo</a>
            </Button>
            ),
            tree = button.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
