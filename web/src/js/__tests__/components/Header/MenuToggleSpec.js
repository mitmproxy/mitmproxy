import * as React from "react"
import renderer from 'react-test-renderer'
import {EventlogToggle, MenuToggle, OptionsToggle} from '../../../components/Header/MenuToggle'
import {Provider} from 'react-redux'
import {TStore} from '../../ducks/tutils'
import * as optionsEditorActions from "../../../ducks/ui/optionsEditor"
import {fireEvent, render, screen} from "../../test-utils"

describe('MenuToggle Component', () => {
    it('should render correctly', () => {
        let changeFn = jest.fn(),
            menuToggle = renderer.create(
                <MenuToggle onChange={changeFn} value={true}>
                    <p>foo children</p>
                </MenuToggle>),
            tree = menuToggle.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

test("OptionsToggle", async () => {
    const store = TStore(),
        {asFragment} = render(
            <OptionsToggle name='anticache'>toggle anticache</OptionsToggle>,
                {store}
        );
    globalThis.fetch = jest.fn()

    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("toggle anticache"));
    expect(store.getActions()).toEqual([optionsEditorActions.startUpdate("anticache", true)])
});

test("EventlogToggle", async () => {
    const {asFragment, store} = render(
        <EventlogToggle/>
    );
    expect(asFragment()).toMatchSnapshot();

    expect(store.getState().eventLog.visible).toBeTruthy();
    fireEvent.click(screen.getByText("Display Event Log"));

    expect(store.getState().eventLog.visible).toBeFalsy();
})
