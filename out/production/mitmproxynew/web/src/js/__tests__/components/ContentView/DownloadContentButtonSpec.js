import React from 'react'
import renderer from 'react-test-renderer'
import DownloadContentButton from '../../../components/ContentView/DownloadContentButton'
import { TFlow } from '../../ducks/tutils'

let tflow = new TFlow()
describe('DownloadContentButton Component', () => {
    it('should render correctly', () => {
        let downloadContentButton = renderer.create(
            <DownloadContentButton flow={tflow} message={tflow.response}/>
        ),
            tree = downloadContentButton.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
