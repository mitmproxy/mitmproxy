import React, { Component } from "react";
import { withTranslation, type WithTranslation } from "react-i18next";
import { fetchApi } from "../../utils";

type FilterDocsProps = {
    selectHandler: (cmd: string) => void;
} & WithTranslation;

type FilterDocsStates = {
    doc: { commands: string[][] };
};

class FilterDocs extends Component<FilterDocsProps, FilterDocsStates> {
    // @todo move to redux

    static xhr: Promise<any> | null;
    static doc: { commands: string[][] };

    constructor(props, context) {
        super(props, context);
        this.state = { doc: FilterDocs.doc };
    }

    componentDidMount() {
        if (!FilterDocs.xhr) {
            FilterDocs.xhr = fetchApi("/filter-help").then((response) =>
                response.json(),
            );
            FilterDocs.xhr.catch(() => {
                FilterDocs.xhr = null;
            });
        }
        if (!this.state.doc) {
            FilterDocs.xhr.then((doc) => {
                FilterDocs.doc = doc;
                this.setState({ doc });
            });
        }
    }

    render() {
        const { t } = this.props;
        const { doc } = this.state;
        return !doc ? (
            <i className="fa fa-spinner fa-spin" />
        ) : (
            <table className="table table-condensed">
                <tbody>
                    {doc.commands.map((cmd) => (
                        <tr
                            key={cmd[1]}
                            onClick={() =>
                                this.props.selectHandler(
                                    cmd[0].split(" ")[0] + " ",
                                )
                            }
                        >
                            <td>{cmd[0].replace(" ", " ")}</td>
                            <td>{cmd[1]}</td>
                        </tr>
                    ))}
                    <tr key="docs-link">
                        <td colSpan={2}>
                            <a
                                href="https://mitmproxy.org/docs/latest/concepts-filters/"
                                target="_blank"
                                rel="noreferrer"
                            >
                                <i className="fa fa-external-link" />
                                &nbsp; {t("header.filterDocs.docsLink")}
                            </a>
                        </td>
                    </tr>
                </tbody>
            </table>
        );
    }
}

export default withTranslation()(FilterDocs);
