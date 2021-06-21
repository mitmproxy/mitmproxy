import React from 'react'
import Modal from '../../../components/Modal/Modal'
import {render} from "../../test-utils"
import {setActiveModal} from "../../../ducks/ui/modal";

test("Modal Component", async () => {
    const {asFragment, store} = render(<Modal/>);
    expect(asFragment()).toMatchSnapshot();

    store.dispatch(setActiveModal("OptionModal"));
    expect(asFragment()).toMatchSnapshot();

})

/*
describe('Modal Component', () => {
    let store = TStore()

    it('should render correctly', () => {
        // hide modal by default
        let provider = renderer.create(
            <Provider store={store}>
               <Modal/>
            </Provider>
        ),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()

        // option modal show up
        store.getState().ui.modal.activeModal = 'OptionModal'
        provider = renderer.create(
            <Provider store={store}>
                <Modal/>
            </Provider>
        )
        tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
*/
