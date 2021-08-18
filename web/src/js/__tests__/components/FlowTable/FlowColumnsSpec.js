import * as React from "react"
import renderer from 'react-test-renderer'
import {
    icon,
    method,
    path,
    quickactions,
    size,
    status,
    time,
    timestamp,
    tls
} from '../../../components/FlowTable/FlowColumns'
import {TFlow, TStore} from '../../ducks/tutils'
import {Provider} from 'react-redux'

describe('Flowcolumns Components', () => {

    let tflow = TFlow()
    it('should render TLSColumn', () => {
        let tlsColumn = renderer.create(<tls flow={tflow}/>),
            tree = tlsColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render IconColumn', () => {
        let tflow = TFlow(),
            iconColumn = renderer.create(<icon flow={tflow}/>),
            tree = iconColumn.toJSON()
        // plain
        expect(tree).toMatchSnapshot()
        // not modified
        tflow.response.status_code = 304
        iconColumn = renderer.create(<icon flow={tflow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // redirect
        tflow.response.status_code = 302
        iconColumn = renderer.create(<icon flow={tflow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // image
        let imageFlow = TFlow()
        imageFlow.response.headers = [['Content-Type', 'image/jpeg']]
        iconColumn = renderer.create(<icon flow={imageFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // javascript
        let jsFlow = TFlow()
        jsFlow.response.headers = [['Content-Type', 'application/x-javascript']]
        iconColumn = renderer.create(<icon flow={jsFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // css
        let cssFlow = TFlow()
        cssFlow.response.headers = [['Content-Type', 'text/css']]
        iconColumn = renderer.create(<icon flow={cssFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // html
        let htmlFlow = TFlow()
        htmlFlow.response.headers = [['Content-Type', 'text/html']]
        iconColumn = renderer.create(<icon flow={htmlFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // default
        let fooFlow = TFlow()
        fooFlow.response.headers = [['Content-Type', 'foo']]
        iconColumn = renderer.create(<icon flow={fooFlow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
        // no response
        tflow.response = null
        iconColumn = renderer.create(<icon flow={tflow}/>)
        tree = iconColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render pathColumn', () => {
        let tflow = TFlow(),
            pathColumn = renderer.create(<path flow={tflow}/>),
            tree = pathColumn.toJSON()
        expect(tree).toMatchSnapshot()

        tflow.error.msg = 'Connection killed.'
        tflow.intercepted = true
        pathColumn = renderer.create(<path flow={tflow}/>)
        tree = pathColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render MethodColumn', () => {
        let methodColumn = renderer.create(<method flow={tflow}/>),
            tree = methodColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render StatusColumn', () => {
        let statusColumn = renderer.create(<status flow={tflow}/>),
            tree = statusColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render SizeColumn', () => {
        let sizeColumn = renderer.create(<size flow={tflow}/>),
            tree = sizeColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render TimeColumn', () => {
        let tflow = TFlow(),
            timeColumn = renderer.create(<time flow={tflow}/>),
            tree = timeColumn.toJSON()
        expect(tree).toMatchSnapshot()

        tflow.response = null
        timeColumn = renderer.create(<time flow={tflow}/>)
        tree = timeColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render TimeStampColumn', () => {
        let timeStampColumn = renderer.create(<timestamp flow={tflow}/>),
            tree = timeStampColumn.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render QuickActionsColumn', () => {
        let store = TStore(),
            provider = renderer.create(
                <Provider store={store}>
                    <quickactions flow={tflow}/>
                </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
