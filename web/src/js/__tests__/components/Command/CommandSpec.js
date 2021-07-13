import React from 'react'
import CommandBar from '../../../components/CommandBar'
import { render } from "../../test-utils"

test('CommandBar Component', async () => {
    const {asFragment, store} = render(
        <CommandBar/>
    );
    expect(asFragment()).toMatchSnapshot();
})