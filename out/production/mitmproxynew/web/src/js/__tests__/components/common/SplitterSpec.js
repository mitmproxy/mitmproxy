import React from 'react'
import ReactDOM from 'react-dom'
import renderer from 'react-test-renderer'
import Splitter from '../../../components/common/Splitter'
import TestUtils from 'react-dom/test-utils';

describe('Splitter Component', () => {

    it('should render correctly', () => {
        let splitter = renderer.create(<Splitter></Splitter>),
            tree = splitter.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let splitter = TestUtils.renderIntoDocument(<Splitter></Splitter>),
        dom = ReactDOM.findDOMNode(splitter),
        previousElementSibling = {
            offsetHeight: 0,
            offsetWidth: 0,
            style: {flex: ''}
        },
        nextElementSibling = {
            style: {flex: ''}
        }

    it('should handle mouseDown ', () => {
        window.addEventListener = jest.fn()
        splitter.onMouseDown({ pageX: 1, pageY: 2})
        expect(splitter.state.startX).toEqual(1)
        expect(splitter.state.startY).toEqual(2)
        expect(window.addEventListener).toBeCalledWith('mousemove', splitter.onMouseMove)
        expect(window.addEventListener).toBeCalledWith('mouseup', splitter.onMouseUp)
        expect(window.addEventListener).toBeCalledWith('dragend', splitter.onDragEnd)
    })

    it('should handle dragEnd', () => {
        window.removeEventListener = jest.fn()
        splitter.onDragEnd()
        expect(dom.style.transform).toEqual('')
        expect(window.removeEventListener).toBeCalledWith('dragend', splitter.onDragEnd)
        expect(window.removeEventListener).toBeCalledWith('mouseup', splitter.onMouseUp)
        expect(window.removeEventListener).toBeCalledWith('mousemove', splitter.onMouseMove)
    })

    it('should handle mouseUp', () => {

        Object.defineProperty(dom, 'previousElementSibling', { value: previousElementSibling })
        Object.defineProperty(dom, 'nextElementSibling', { value: nextElementSibling })
        splitter.onMouseUp({ pageX: 3, pageY: 4 })
        expect(splitter.state.applied).toBeTruthy()
        expect(nextElementSibling.style.flex).toEqual('1 1 auto')
        expect(previousElementSibling.style.flex).toEqual('0 0 2px')
    })

    it('should handle mouseMove', () => {
        splitter.onMouseMove({pageX: 10, pageY: 10})
        expect(dom.style.transform).toEqual("translate(9px, 0px)")

        let splitterY = TestUtils.renderIntoDocument(<Splitter axis="y"></Splitter>)
        splitterY.onMouseMove({pageX: 10, pageY: 10})
        expect(ReactDOM.findDOMNode(splitterY).style.transform).toEqual("translate(0px, 10px)")
    })

    it('should handle resize', () => {
        window.setTimeout = jest.fn((event, time) => event())
        splitter.onResize()
        expect(window.setTimeout).toHaveBeenCalled()
    })

    it('should handle componentWillUnmount', () => {
        splitter.componentWillUnmount()
        expect(previousElementSibling.style.flex).toEqual('')
        expect(nextElementSibling.style.flex).toEqual('')
        expect(splitter.state.applied).toBeTruthy()
    })

    it('should handle reset', () => {
        splitter.reset(false)
        expect(splitter.state.applied).toBeFalsy()

        expect(splitter.reset(true)).toEqual(undefined)
    })

})
