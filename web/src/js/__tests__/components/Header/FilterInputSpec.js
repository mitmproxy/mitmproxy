import React from 'react'
import renderer from 'react-test-renderer'
import FilterInput from '../../../components/Header/FilterInput'
import FilterDocs from '../../../components/Header/FilterDocs'
import TestUtil from 'react-dom/test-utils'
import ReactDOM from 'react-dom'
import { Key } from '../../../utils'

describe('FilterInput Component', () => {
    it('should render correctly', () => {
        let filterInput = renderer.create(<FilterInput type='foo' color='red' placeholder='bar'/>),
            tree = filterInput.toJSON()
        expect(tree).toMatchSnapshot()
    })

    let filterInput = TestUtil.renderIntoDocument(
        <FilterInput type='foo' color='red' placeholder='bar' value='' onChange={jest.fn()}/>)
    it('should handle componentWillReceiveProps', () => {
       filterInput.componentWillReceiveProps({value: 'foo'})
        expect(filterInput.state.value).toEqual('foo')
    })

    it('should handle isValid', () => {
        // valid
        expect(filterInput.isValid("~u foo")).toBeTruthy()
        expect(filterInput.isValid("~foo bar")).toBeFalsy()
    })

    it('should handle getDesc', () => {
        filterInput.state.value = ''
        expect(filterInput.getDesc().type).toEqual(FilterDocs)

        filterInput.state.value = '~u foo'
        expect(filterInput.getDesc()).toEqual('url matches /foo/i')

        filterInput.state.value = '~foo bar'
        expect(filterInput.getDesc()).toEqual('SyntaxError: Expected filter expression but \"~\" found.')
    })

    it('should handle change', () => {
        let mockEvent = { target: { value: '~a bar'} }
        filterInput.onChange(mockEvent)
        expect(filterInput.state.value).toEqual('~a bar')
        expect(filterInput.props.onChange).toBeCalledWith('~a bar')
    })

    it('should handle focus', () => {
        filterInput.onFocus()
        expect(filterInput.state.focus).toBeTruthy()
    })

    it('should handle blur', () => {
        filterInput.onBlur()
        expect(filterInput.state.focus).toBeFalsy()
    })

    it('should handle mouseEnter', () => {
        filterInput.onMouseEnter()
        expect(filterInput.state.mousefocus).toBeTruthy()
    })

    it('should handle mouseLeave', () => {
        filterInput.onMouseLeave()
        expect(filterInput.state.mousefocus).toBeFalsy()
    })

    let input = ReactDOM.findDOMNode(filterInput.refs.input)

    it('should handle keyDown', () => {
        input.blur = jest.fn()
        let mockEvent = {
            keyCode: Key.ESC,
            stopPropagation: jest.fn()
        }
        filterInput.onKeyDown(mockEvent)
        expect(input.blur).toBeCalled()
        expect(filterInput.state.mousefocus).toBeFalsy()
        expect(mockEvent.stopPropagation).toBeCalled()
    })

    it('should handle selectFilter', () => {
        input.focus = jest.fn()
        filterInput.selectFilter('bar')
        expect(filterInput.state.value).toEqual('bar')
        expect(input.focus).toBeCalled()
    })

    it('should handle select', () => {
        input.select = jest.fn()
        filterInput.select()
        expect(input.select).toBeCalled()
    })
})
