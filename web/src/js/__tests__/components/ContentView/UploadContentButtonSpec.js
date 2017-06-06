import React from 'react'
import renderer from 'react-test-renderer'
import UploadContentButton from '../../../components/ContentView/UploadContentButton'

describe('UpdateContentButton Component', () => {
    it('should render correctly', () => {
        let uploadContentFn = jest.fn(),
            uploadContentButton = renderer.create(<UploadContentButton uploadContent={uploadContentFn}/>),
            tree = uploadContentButton.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
