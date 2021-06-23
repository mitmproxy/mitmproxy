import React from 'react'
import renderer from 'react-test-renderer'
import TestUtils from 'react-dom/test-utils'
import { Provider } from 'react-redux'
import { ViewServer, ViewImage, PureViewServer, Edit } from '../../../components/ContentView/ContentViews'
import { TFlow, TStore } from '../../ducks/tutils'
import mockXMLHttpRequest from 'mock-xmlhttprequest'

window.XMLHttpRequest = mockXMLHttpRequest
let tflow = new TFlow()

describe('ViewImage Component', () => {
    let viewImage = renderer.create(<ViewImage flow={tflow} message={tflow.response}/>),
        tree = viewImage.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })
})

describe('ViewServer Component', () => {
    let store = TStore(),
    setContentViewDescFn = jest.fn(),
    setContentFn = jest.fn()

    it('should render correctly and connect to state', () => {
        let provider = renderer.create(
            <Provider store={store}>
                <ViewServer
                    setContentViewDescription={setContentViewDescFn}
                    setContent={setContentFn}
                    flow={tflow}
                    message={tflow.response}
                />
            </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()

        let viewServer = renderer.create(
            <PureViewServer
                showFullContent={true}
                maxLines={10}
                setContentViewDescription={setContentViewDescFn}
                setContent={setContentViewDescFn}
                flow={tflow}
                message={tflow.response}
                content={JSON.stringify({lines: [['k1', 'v1']]})}
            />
        )
        tree = viewServer.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle componentWillReceiveProps', () => {
        // case of fail to parse content
        let viewSever = TestUtils.renderIntoDocument(
            <PureViewServer
                showFullContent={true}
                maxLines={10}
                setContentViewDescription={setContentViewDescFn}
                setContent={setContentViewDescFn}
                flow={tflow}
                message={tflow.response}
                content={JSON.stringify({lines: [['k1', 'v1']]})}
            />
        )
        viewSever.componentWillReceiveProps({...viewSever.props, content: '{foo' })
        let e = ''
        try {JSON.parse('{foo') } catch(err){ e = err.message}
        expect(viewSever.data).toEqual({ description: e, lines: [] })
    })
})

describe('Edit Component', () => {
    it('should render correctly', () => {
        let edit = renderer.create(<Edit
                content="foo"
                onChange={jest.fn}
                flow={tflow}
                message={tflow.response}
            />),
            tree = edit.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
