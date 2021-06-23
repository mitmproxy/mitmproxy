import React from "react"
import ReactDOM from "react-dom"
import AutoScroll from '../../../components/helpers/AutoScroll'
import { calcVScroll } from '../../../components/helpers/VirtualScroll'
import TestUtils from 'react-dom/test-utils'

describe('Autoscroll', () => {
    let mockFn = jest.fn()
    class tComponent extends React.Component {
        constructor(props, context){
            super(props, context)
            this.state = { vScroll: calcVScroll() }
        }

       UNSAFE_componentWillUpdate() {
           mockFn("foo")
       }

       componentDidUpdate() {
           mockFn("bar")
       }

       render() {
           return (<p>foo</p>)
       }
    }

    it('should update component', () => {
        let Foo = AutoScroll(tComponent),
            autoScroll = TestUtils.renderIntoDocument(<Foo></Foo>),
            viewport = ReactDOM.findDOMNode(autoScroll)
        viewport.scrollTop = 10
        Object.defineProperty(viewport, "scrollHeight", { value: 10, writable: true })
        autoScroll.UNSAFE_componentWillUpdate()
        expect(mockFn).toBeCalledWith("foo")

        Object.defineProperty(viewport, "scrollHeight", { value: 0, writable: true })
        autoScroll.componentDidUpdate()
        expect(mockFn).toBeCalledWith("bar")
    })
})
