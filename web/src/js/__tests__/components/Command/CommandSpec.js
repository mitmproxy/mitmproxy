import * as React from "react"
import CommandBar from '../../../components/CommandBar'
import {render} from "../../test-utils"
import fetchMock, {enableFetchMocks} from "jest-fetch-mock";
import {waitFor} from '@testing-library/react'

enableFetchMocks()


test('CommandBar Component', async () => {
    fetchMock.mockResponseOnce(JSON.stringify({"commands": "foo"}));

    const {asFragment, store} = render(
        <CommandBar/>
    );
    await waitFor(() => {
        expect(asFragment()).toMatchSnapshot();
    });
})
