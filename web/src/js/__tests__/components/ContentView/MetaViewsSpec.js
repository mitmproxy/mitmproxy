import React from 'react'
import renderer from 'react-test-renderer'
import { ContentEmpty, ContentMissing, ContentTooLarge } from '../../../components/ContentView/MetaViews'
import { TFlow } from '../../ducks/tutils'

let tflow = new TFlow()

describe('ContentEmpty Components', () => {
    it('should render correctly', () => {
        let contentEmpty = renderer.create(<ContentEmpty flow={tflow} message={tflow.response}/>),
            tree = contentEmpty.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

describe('ContentMissing Components', () => {
    it('should render correctly', () => {
        let contentMissing = renderer.create(<ContentMissing flow={tflow} message={tflow.response}/>),
            tree = contentMissing.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

describe('ContentTooLarge Components', () => {
    it('should render correctly', () => {
        let clickFn = jest.fn(),
            uploadContentFn = jest.fn(),
            contentTooLarge = renderer.create(<ContentTooLarge
                flow={tflow}
                message={tflow.response}
                onClick={clickFn}
                uploadContent={uploadContentFn}
            />),
            tree = contentTooLarge.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
