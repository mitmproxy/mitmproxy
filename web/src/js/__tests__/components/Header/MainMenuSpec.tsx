import * as React from "react";
import FlowListMenu from "../../../components/Header/FlowListMenu";
import { render } from "../../test-utils";

test("MainMenu", () => {
    const { asFragment } = render(<FlowListMenu />);
    expect(asFragment()).toMatchSnapshot();
});
