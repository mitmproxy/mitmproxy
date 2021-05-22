import React from 'react'
import renderer from 'react-test-renderer'
import Nav, { NavAction } from '../../../components/FlowView/Nav'

describe('Nav Component', () => {
    let tabs = ['foo', 'bar'],
        onSelectTab = jest.fn(),
        nav = renderer.create(<Nav active='foo' tabs={tabs} onSelectTab={onSelectTab}/>),
        tree = nav.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle click', () => {
        let mockEvent = { preventDefault: jest.fn() }
        tree.children[0].props.onClick(mockEvent)
        expect(mockEvent.preventDefault).toBeCalled()
        expect(onSelectTab).toBeCalledWith('foo')
    })
})

describe('NavAction Component', () => {
    let clickFn = jest.fn(),
        navAction = renderer.create(<NavAction icon="foo" title="bar" onClick={clickFn}/>),
        tree = navAction.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle click', () => {
        let mockEvent = { preventDefault: jest.fn() }
        tree.props.onClick(mockEvent)
        expect(mockEvent.preventDefault).toBeCalled()
        expect(clickFn).toBeCalledWith(mockEvent)
    })
})
