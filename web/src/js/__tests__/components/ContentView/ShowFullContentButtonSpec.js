import React from 'react'
import renderer from 'react-test-renderer'
import { Provider } from 'react-redux'
import ConnectedComponent, { ShowFullContentButton } from '../../../components/ContentView/ShowFullContentButton'
import { TStore } from '../../ducks/tutils'


describe('ShowFullContentButton Component', () => {
    let setShowFullContentFn = jest.fn(),
        showFullContentButton = renderer.create(
            <ShowFullContentButton
                setShowFullContent={setShowFullContentFn}
                showFullContent={false}
                visibleLines={10}
                contentLines={20}
            />
        ),
        tree = showFullContentButton.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle click', () => {
        tree.children[0].props.onClick()
        expect(setShowFullContentFn).toBeCalled()
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
