jest.mock("../../../contrib/CodeMirror")
import * as React from 'react';
import CodeEditor from '../../../components/ContentView/CodeEditor'
import {render} from '@testing-library/react'


test("CodeEditor", async () => {

    const changeFn = jest.fn(),
        {asFragment} = render(
            <CodeEditor content="foo" onChange={changeFn}/>
        );
    expect(asFragment()).toMatchSnapshot()
});
