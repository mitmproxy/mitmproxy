jest.mock('../../../components/ContentView')
import React from 'react'
import renderer from 'react-test-renderer'
import TestUtils from 'react-dom/test-utils'
import { Request, Response, ErrorView } from '../../../components/FlowView/Messages'
import { Provider } from 'react-redux'
import { TFlow, TStore } from '../../ducks/tutils'
import { updateEdit } from '../../../ducks/ui/flow'
import { parseUrl } from '../../../flow/utils'
import ContentView from '../../../components/ContentView'
import ContentViewOptions from '../../../components/ContentView/ContentViewOptions'
import Headers from '../../../components/FlowView/Headers'
import ValueEditor from '../../../components/ValueEditor/ValueEditor'

global.fetch = jest.fn()

let tflow = new TFlow(),
    store = TStore()
store.getState().ui.flow.modifiedFlow = false

describe('Request Component', () => {

    afterEach(() => {store.clearActions()})

    it('should render correctly', () => {
        let provider = renderer.create(
            <Provider store={store}>
                <Request/>
            </Provider>
            ),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let provider = TestUtils.renderIntoDocument(
        <Provider store={store}>
            <Request/>
        </Provider>),
        valueEditors = TestUtils.scryRenderedComponentsWithType(provider, ValueEditor)

    it('should handle done on flow request method', () => {
        let valueEditor = valueEditors[0]
        valueEditor.props.onDone('foo')
        expect(store.getActions()).toEqual([updateEdit({ request: { method: 'foo' }})])
    })

    it('should handle done on flow request url', () => {
        let valueEditor = valueEditors[1],
            url = 'http://foo/bar'
        valueEditor.props.onDone(url)
        expect(store.getActions()).toEqual([updateEdit({ request: { path: '', ...parseUrl(url)}})])
    })

    it('should handle done on flow request http version', () => {
        let valueEditor = valueEditors[2]
        valueEditor.props.onDone('HTTP/9.9')
        expect(store.getActions()).toEqual([updateEdit({ request: { http_version: 'HTTP/9.9' }})])
    })

    it('should handle change on flow request header', () => {
        let headers = TestUtils.findRenderedComponentWithType(provider, Headers)
        headers.props.onChange('foo')
        expect(store.getActions()).toEqual([updateEdit({ request: { headers: 'foo' }})])
    })

    it('should handle change on flow request contentView', () => {
        let contentView = TestUtils.findRenderedComponentWithType(provider, ContentView)
        contentView.props.onContentChange('foo')
        expect(store.getActions()).toEqual([updateEdit({ request: { content: 'foo' }})])
    })

    it('should handle uploadContent on flow request ContentViewOptions', () => {
        let contentViewOptions = TestUtils.findRenderedComponentWithType(provider, ContentViewOptions)
        contentViewOptions.props.uploadContent('foo')
        expect(fetch).toBeCalled()
        fetch.mockClear()
    })
})

describe('Response Component', () => {
    afterEach(() => {store.clearActions()})

    it('should render correctly', () => {
        let provider = renderer.create(
            <Provider store={store}>
                <Response/>
            </Provider>
        ),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let provider = TestUtils.renderIntoDocument(
        <Provider store={store}>
            <Response/>
        </Provider>),
        valueEditors = TestUtils.scryRenderedComponentsWithType(provider, ValueEditor)

    it('should handle done on flow response http version', () => {
        let valueEditor = valueEditors[0]
        valueEditor.props.onDone('HTTP/9.9')
        expect(store.getActions()).toEqual([updateEdit({ response: { http_version: 'HTTP/9.9' }})])
    })

    it('should handle done on flow response status code', () => {
        let valueEditor = valueEditors[1]
        valueEditor.props.onDone('404')
        expect(store.getActions()).toEqual([updateEdit({ response: { code: parseInt('404') }})])
    })

    it('should handle done on flow response reason', () => {
        let valueEdiotr = valueEditors[2]
        valueEdiotr.props.onDone('foo')
        expect(store.getActions()).toEqual([updateEdit( { response: { msg: 'foo' }})])
    })

    it('should handle change on flow response headers', () => {
        let headers = TestUtils.findRenderedComponentWithType(provider, Headers)
        headers.props.onChange('foo')
        expect(store.getActions()).toEqual([updateEdit( { response: { headers: 'foo' }})])
    })

    it('should handle change on flow response ContentView', () => {
        let contentView = TestUtils.findRenderedComponentWithType(provider, ContentView)
        contentView.props.onContentChange('foo')
        expect(store.getActions()).toEqual([updateEdit( { response: { content: 'foo' }})])
    })

    it('should handle updateContent on flow response ContentViewOptions', () => {
        let contentViewOptions = TestUtils.findRenderedComponentWithType(provider, ContentViewOptions)
        contentViewOptions.props.uploadContent('foo')
        expect(fetch).toBeCalled()
        fetch.mockClear()
    })
})

describe('Error Component', () => {
    it('should render correctly', () => {
        let errorView = renderer.create(<ErrorView flow={tflow}/>),
            tree = errorView.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
