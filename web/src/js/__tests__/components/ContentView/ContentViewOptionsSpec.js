import React from 'react'
import renderer from 'react-test-renderer'
import ContentViewOptions from '../../../components/ContentView/ContentViewOptions'
import { Provider } from 'react-redux'
import { TFlow, TStore } from '../../ducks/tutils'
import { uploadContent } from '../../../ducks/flows'

let tflow = new TFlow()

describe('ContentViewOptions Component', () => {
    let store = TStore()
    it('should render correctly', () => {
        let provider = renderer.create(
            <Provider store={store}>
                <ContentViewOptions flow={tflow} message={tflow.response} uploadContent={uploadContent}/>
            </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
