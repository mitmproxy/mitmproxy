import * as React from "react"
import StartMenu from '../../../components/Header/StartMenu'
import {render} from "../../test-utils"

test("MainMenu", () => {
    const {asFragment} = render(<StartMenu/>);
    expect(asFragment()).toMatchSnapshot();
})
