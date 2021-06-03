import React from 'react'
import renderer from 'react-test-renderer'
import {columns} from '../../../components/FlowTable/FlowColumns'
import { TFlow } from '../../ducks/tutils'
import { Provider } from 'react-redux'
import { TStore } from '../../ducks/tutils'

describe('Flowcolumns Components', () => {

    let tflow = TFlow()
    it('should render TLSColumn', () => {
        let tlsColumn = renderer.create(<columns.TLSColumn flow={tflow}/>),
            tree = tlsColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render IconColumn', () => {
        let iconColumn = renderer.create(<columns.IconColumn flow={tflow}/>),
            tree = iconColumn.toJSON()
        // plain
        expect(tree).toMatchSnapshot()
        // not modified
        tflow.response.status_code = 304
        iconColumn = renderer.create(<columns.IconColumn flow={tflow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // redirect
        tflow.response.status_code = 302
        iconColumn = renderer.create(<columns.IconColumn flow={tflow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // image
        let imageFlow = TFlow()
        imageFlow.response.headers = [['Content-Type', 'image/jpeg']]
        iconColumn = renderer.create(<columns.IconColumn flow={imageFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // javascript
        let jsFlow = TFlow()
        jsFlow.response.headers = [['Content-Type', 'application/x-javascript']]
        iconColumn = renderer.create(<columns.IconColumn flow={jsFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // css
        let cssFlow = TFlow()
        cssFlow.response.headers = [['Content-Type', 'text/css']]
        iconColumn = renderer.create(<columns.IconColumn flow={cssFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // html
        let htmlFlow = TFlow()
        htmlFlow.response.headers = [['Content-Type', 'text/html']]
        iconColumn = renderer.create(<columns.IconColumn flow={htmlFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // default
        let fooFlow = TFlow()
        fooFlow.response.headers = [['Content-Type', 'foo']]
        iconColumn = renderer.create(<columns.IconColumn flow={fooFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // no response
        tflow.response = null
        iconColumn = renderer.create(<columns.IconColumn flow={tflow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render pathColumn', () => {
        let pathColumn = renderer.create(<columns.PathColumn flow={tflow}/>),
            tree = pathColumn.toJSON()
        expect(tree).toMatchSnapshot()

        tflow.error.msg = 'Connection killed.'
        tflow.intercepted = true
        pathColumn = renderer.create(<columns.PathColumn flow={tflow}/>)
        tree = pathColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render MethodColumn', () => {
        let methodColumn =renderer.create(<columns.MethodColumn flow={tflow}/>),
            tree = methodColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render StatusColumn', () => {
        let statusColumn = renderer.create(<columns.StatusColumn flow={tflow}/>),
            tree = statusColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render SizeColumn', () => {
        tflow = TFlow()
        let sizeColumn = renderer.create(<columns.SizeColumn flow={tflow}/>),
            tree = sizeColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render TimeColumn', () => {
        let timeColumn = renderer.create(<columns.TimeColumn flow={tflow}/>),
            tree = timeColumn.toJSON()
        expect(tree).toMatchSnapshot()

        tflow.response = null
        timeColumn = renderer.create(<columns.TimeColumn flow={tflow}/>),
        tree = timeColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render TimeStampColumn', () => {
        let timeStampColumn = renderer.create(<columns.TimeStampColumn flow={tflow}/>),
            tree = timeStampColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render ForwardColumn', () => {
        let store = TStore(),
            provider = renderer.create(
            <Provider store={store}>
                <columns.ForwardColumn flow={tflow}/>
            </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

