import React from 'react'
import renderer from 'react-test-renderer'
import ConnectedComponent, { ViewSelector } from '../../../components/ContentView/ViewSelector'
import { Provider } from 'react-redux'
import { TStore } from '../../ducks/tutils'


describe('ViewSelector Component', () => {
    let contentViews = ['Auto', 'Raw', 'Text'],
        activeView = 'Auto',
        setContentViewFn = jest.fn(),
        viewSelector = renderer.create(
            <ViewSelector contentViews={contentViews} activeView={activeView} setContentView={setContentViewFn}/>
        ),
        tree = viewSelector.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle click', () => {
        let mockEvent = { preventDefault: jest.fn() },
            tab = tree.children[1].children[0].children[1]
        tab.props.onClick(mockEvent)
        expect(mockEvent.preventDefault).toBeCalled()
    })

    it('should connect to state', () => {
        let store = TStore(),
            provider = renderer.create(
                <Provider store={store}>
                    <ConnectedComponent/>
                </Provider>
            ),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
