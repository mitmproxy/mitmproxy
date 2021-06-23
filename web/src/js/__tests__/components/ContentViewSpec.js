import React from 'react'
import renderer from 'react-test-renderer'
import ContentView from '../../components/ContentView'
import { TStore, TFlow } from '../ducks/tutils'
import { Provider } from 'react-redux'
import mockXMLHttpRequest from 'mock-xmlhttprequest'

window.XMLHttpRequest = mockXMLHttpRequest

describe('ContentView Component', () => {
    let store = TStore()

    it('should render correctly', () => {
        store.getState().ui.flow.contentView = 'Edit'
        let tflow = TFlow(),
            provider = renderer.create(
            <Provider store={store}>
                <ContentView flow={tflow} message={tflow.request}/>
            </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render correctly with empty content', () => {
        let tflow = TFlow()
        tflow.response.contentLength = 0
        let provider = renderer.create(
            <Provider store={store}>
                <ContentView flow={tflow} message={tflow.response} readonly={true}/>
            </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render correctly with missing content', () => {
        let tflow = TFlow()
        tflow.response.contentLength = null
        let provider = renderer.create(
            <Provider store={store}>
                <ContentView flow={tflow} message={tflow.response} readonly={true}/>
            </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render correctly with content too large', () => {
        let tflow = TFlow()
        tflow.response.contentLength = 1024 * 1024 * 100
        let provider = renderer.create(
            <Provider store={store}>
                <ContentView
                    flow={tflow}
                    message={tflow.response}
                    readonly={true}
                    uploadContent={jest.fn()}
                    onOpenFile={jest.fn()}
                />
            </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
