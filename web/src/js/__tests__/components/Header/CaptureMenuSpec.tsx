import * as React from "react";
import CaptureMenu from "../../../components/Header/CaptureMenu";
import { render } from "../../test-utils";

describe("CaptureMenu Component", () => {
    it("should render correctly", () => {
        const { asFragment } = render(<CaptureMenu />);
        expect(asFragment()).toMatchSnapshot();
    });
});
