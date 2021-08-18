import * as React from "react"
import renderer from 'react-test-renderer'
import ViewSelector from '../../../components/ContentView/ViewSelector'
import { Provider } from 'react-redux'
import { TStore } from '../../ducks/tutils'


describe('ViewSelector Component', () => {
    let store = TStore(),
        viewSelector = renderer.create(
            <Provider store={store}>
                <ViewSelector/>
            </Provider>
        ),
        tree = viewSelector.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })
})
