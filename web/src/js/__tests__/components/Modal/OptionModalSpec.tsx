import * as React from "react";
import OptionModal, {
    PureOptionDefault,
} from "../../../components/Modal/OptionModal";
import { render, screen } from "../../test-utils";
import { TStore, testState } from "../../ducks/tutils";

describe("OptionModal Component", () => {
    it("leaves the flow table columns to the column picker", () => {
        const store = TStore({
            ...testState,
            options_meta: {
                ...testState.options_meta,
                web_columns: {
                    type: "sequence of str",
                    default: ["path", "method"],
                    value: ["path", "method"],
                    help: "Columns to show in the flow list",
                    choices: undefined,
                },
            },
        });
        render(<OptionModal />, { store });

        expect(screen.getByText("anticache")).toBeInTheDocument();
        expect(screen.queryByText("web_columns")).not.toBeInTheDocument();
    });
});

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
