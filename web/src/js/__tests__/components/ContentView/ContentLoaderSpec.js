import React from 'react'
import renderer from 'react-test-renderer'
import withContentLoader from '../../../components/ContentView/ContentLoader'
import { TFlow } from '../../ducks/tutils'
import TestUtils from 'react-dom/test-utils'
import mockXMLHttpRequest from 'mock-xmlhttprequest'

global.XMLHttpRequest = mockXMLHttpRequest
class tComponent extends React.Component {
    constructor(props, context){
        super(props, context)
    }
    render() {
        return (<p>foo</p>)
    }
}

let tflow = new TFlow(),
    ContentLoader = withContentLoader(tComponent)

describe('ContentLoader Component', () => {
    it('should render correctly', () => {
        let contentLoader = renderer.create(<ContentLoader flow={tflow} message={tflow.response}/>),
            tree = contentLoader.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let contentLoader = TestUtils.renderIntoDocument(<ContentLoader flow={tflow} message={tflow.response}/>)

    it('should handle updateContent', () => {
        tflow.response.content = 'foo'
        contentLoader.updateContent({flow: tflow, message: tflow.response})
        expect(contentLoader.state.request).toEqual(undefined)
        expect(contentLoader.state.content).toEqual('foo')
        // when content length is 0 or null
        tflow.response.contentLength = 0
        tflow.response.content = undefined
        contentLoader.updateContent({flow: tflow, message: tflow.response})
        expect(contentLoader.state.request).toEqual(undefined)
        expect(contentLoader.state.content).toEqual('')
    })

    it('should handle componentWillReceiveProps', () => {
        contentLoader.updateContent = jest.fn()
        contentLoader.componentWillReceiveProps({flow: tflow, message: tflow.request})
        expect(contentLoader.updateContent).toBeCalled()
    })

    it('should handle requestComplete', () => {
        expect(contentLoader.requestComplete(tflow.request, {})).toEqual(undefined)
        // request == this.state.request
        contentLoader.state.request = tflow.request
        contentLoader.requestComplete(tflow.request, {})
        expect(contentLoader.state.content).toEqual(tflow.request.responseText)
        expect(contentLoader.state.request).toEqual(undefined)
    })

    it('should handle requestFailed', () => {
        console.error = jest.fn()
        expect(contentLoader.requestFailed(tflow.request, {})).toEqual(undefined)
        //request == this.state.request
        contentLoader.state.request = tflow.request
        contentLoader.requestFailed(tflow.request, 'foo error')
        expect(contentLoader.state.content).toEqual('Error getting content.')
        expect(contentLoader.state.request).toEqual(undefined)
        expect(console.error).toBeCalledWith('foo error')
    })

    it('should handle componentWillUnmount', () => {
        contentLoader.state.request = { abort : jest.fn() }
        contentLoader.componentWillUnmount()
        expect(contentLoader.state.request.abort).toBeCalled()
    })
})
