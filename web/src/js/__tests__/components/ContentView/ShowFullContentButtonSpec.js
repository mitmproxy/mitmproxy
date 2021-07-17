import React from 'react'
import renderer from 'react-test-renderer'
import { Provider } from 'react-redux'
import ShowFullContentButton  from '../../../components/ContentView/ShowFullContentButton'
import { TStore } from '../../ducks/tutils'


describe('ShowFullContentButton Component', () => {
    let store = TStore()

    let setShowFullContentFn = jest.fn(),
        showFullContentButton = renderer.create(
            <Provider store={store}>
                <ShowFullContentButton />
            </Provider>
        ),
        tree = showFullContentButton.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })
})
