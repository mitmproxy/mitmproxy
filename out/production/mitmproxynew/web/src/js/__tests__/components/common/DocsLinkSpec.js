import React from 'react'
import renderer from 'react-test-renderer'
import DocsLink from '../../../components/common/DocsLink'

describe('DocsLink Component', () => {
    it('should be able to be rendered with children nodes', () => {
        let docsLink = renderer.create(<DocsLink children="foo" resource="bar"></DocsLink>),
            tree = docsLink.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should be able to be rendered without children nodes', () => {
        let docsLink  = renderer.create(<DocsLink resource="bar"></DocsLink>),
            tree = docsLink.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
