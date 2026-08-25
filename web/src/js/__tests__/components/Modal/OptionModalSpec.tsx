import * as React from "react";
import { PureOptionDefault } from "../../../components/Modal/OptionModal";
import { render } from "../../test-utils";

describe("PureOptionDefault Component", () => {
    it("should return null when the value is default", () => {
        const { asFragment } = render(
            <PureOptionDefault value="foo" defaultVal="foo" />,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should handle boolean type", () => {
        const { asFragment } = render(
            <PureOptionDefault value={true} defaultVal={false} />,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should handle array", () => {
        let a = [""],
            b = [],
            c = ["c"],
            { asFragment } = render(
                <PureOptionDefault value={a} defaultVal={b} />,
            );
        expect(asFragment()).toMatchSnapshot();

        asFragment = render(
            <PureOptionDefault value={a} defaultVal={c} />,
        ).asFragment;
        expect(asFragment()).toMatchSnapshot();
    });

    it("should handle string", () => {
        const { asFragment } = render(
            <PureOptionDefault value="foo" defaultVal="" />,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should handle null value", () => {
        const { asFragment } = render(
            <PureOptionDefault value="foo" defaultVal={null} />,
        );
        expect(asFragment()).toMatchSnapshot();
    });
});
