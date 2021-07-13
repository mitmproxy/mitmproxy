import React from 'react'
import CommandBar from '../../../components/CommandBar'
import { render } from "../../test-utils"
import fetchMock from 'fetch-mock';
import { act, waitFor } from '@testing-library/react'

test('CommandBar Component', async () => {
    fetchMock.get('./commands.json', {status: 200, body: {"commands": "foo"}})

    const {asFragment, store} = render(
        <CommandBar/>
    );
    await waitFor(() => {
        expect(asFragment()).toMatchSnapshot();
    });
})