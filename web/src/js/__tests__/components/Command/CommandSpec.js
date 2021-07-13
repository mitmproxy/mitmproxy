import React from 'react'
import CommandBar from '../../../components/CommandBar'
import { render } from "../../test-utils"
import fetchMock from 'fetch-mock';

test('CommandBar Component', async () => {
    fetchMock.get('./commands.json', {status: 200, body: {"commands": "foo"}})

    const {asFragment, store} = render(
        <CommandBar/>
    );
    expect(asFragment()).toMatchSnapshot();
})