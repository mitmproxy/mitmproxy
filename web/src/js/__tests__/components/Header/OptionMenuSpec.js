import React from 'react'
import renderer from 'react-test-renderer'
import { Provider } from 'react-redux'
import OptionMenu from '../../../components/Header/OptionMenu'
import { TStore } from '../../ducks/tutils'

describe('OptionMenu Component', () => {
    it('should render correctly', () => {
        let store = TStore(),
            provider = renderer.create(
                <Provider store={store}>
                    <OptionMenu/>
                </Provider>
            ),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
