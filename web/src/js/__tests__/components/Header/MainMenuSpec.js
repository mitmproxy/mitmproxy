import React from 'react'
import MainMenu from '../../../components/Header/MainMenu'
import {render} from "../../test-utils"

test("MainMenu", () => {
    const {asFragment} = render(<MainMenu/>);
    expect(asFragment()).toMatchSnapshot();
})
