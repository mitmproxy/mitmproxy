import React from 'react'
import renderer from 'react-test-renderer'
import * as Columns from '../../../components/FlowTable/FlowColumns'
import { TFlow } from '../../ducks/tutils'

describe('FlowColumns Components', () => {

    let tFlow = new TFlow()
    it('should render TLSColumn', () => {
        let tlsColumn = renderer.create(<Columns.TLSColumn flow={tFlow}/>),
            tree = tlsColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render IconColumn', () => {
        let iconColumn = renderer.create(<Columns.IconColumn flow={tFlow}/>),
            tree = iconColumn.toJSON()
        // plain
        expect(tree).toMatchSnapshot()
        // not modified
        tFlow.response.status_code = 304
        iconColumn = renderer.create(<Columns.IconColumn flow={tFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // redirect
        tFlow.response.status_code = 302
        iconColumn = renderer.create(<Columns.IconColumn flow={tFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // image
        let imageFlow = new TFlow()
        imageFlow.response.headers = [['Content-Type', 'image/jpeg']]
        iconColumn = renderer.create(<Columns.IconColumn flow={imageFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // javascript
        let jsFlow = new TFlow()
        jsFlow.response.headers = [['Content-Type', 'application/x-javascript']]
        iconColumn = renderer.create(<Columns.IconColumn flow={jsFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // css
        let cssFlow = new TFlow()
        cssFlow.response.headers = [['Content-Type', 'text/css']]
        iconColumn = renderer.create(<Columns.IconColumn flow={cssFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // default
        let fooFlow = new TFlow()
        fooFlow.response.headers = [['Content-Type', 'foo']]
        iconColumn = renderer.create(<Columns.IconColumn flow={fooFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // no response
        tFlow.response = null
        iconColumn = renderer.create(<Columns.IconColumn flow={tFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render pathColumn', () => {
        // error
        let pathColumn = renderer.create(<Columns.PathColumn flow={tFlow}/>),
            tree = pathColumn.toJSON()
        expect(tree).toMatchSnapshot()

        tFlow.error.msg = 'Connection killed'
        tFlow.intercepted = true
        pathColumn = renderer.create(<Columns.PathColumn flow={tFlow}/>)
        tree = pathColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render MethodColumn', () => {
        let methodColumn =renderer.create(<Columns.MethodColumn flow={tFlow}/>),
            tree = methodColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render StatusColumn', () => {
        let statusColumn = renderer.create(<Columns.StatusColumn flow={tFlow}/>),
            tree = statusColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render SizeColumn', () => {
        tFlow = new TFlow()
        let sizeColumn = renderer.create(<Columns.SizeColumn flow={tFlow}/>),
            tree = sizeColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render TimeColumn', () => {
        let timeColumn = renderer.create(<Columns.TimeColumn flow={tFlow}/>),
            tree = timeColumn.toJSON()
        expect(tree).toMatchSnapshot()

        tFlow.response = null
        timeColumn = renderer.create(<Columns.TimeColumn flow={tFlow}/>),
        tree = timeColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
