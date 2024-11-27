import React, { Component } from "react";
import { onKeyDown } from "../ducks/ui/keyboard";
import MainView from "./MainView";
import Header from "./Header";
import CommandBar from "./CommandBar";
import EventLog from "./EventLog";
import Footer from "./Footer";
import Modal from "./Modal/Modal";
import { RootState } from "../ducks";
import { connect } from "react-redux";

type ProxyAppMainProps = {
    showEventLog: boolean;
    showCommandBar: boolean;
    onKeyDown: (e: KeyboardEvent) => void;
};

type ProxyAppMainState = {
    error?: Error;
    errorInfo?: React.ErrorInfo;
};

export interface Menu {
    (): JSX.Element;
    title: string;
}

class ProxyAppMain extends Component<ProxyAppMainProps, ProxyAppMainState> {
    state: ProxyAppMainState = {};

    render = () => {
        const { showEventLog, showCommandBar } = this.props;

        if (this.state.error) {
            console.log("ERR", this.state);
            return (
                <div className="container">
                    <h1>mitmproxy has crashed.</h1>
                    <pre>
                        {this.state.error.stack}
                        <br />
                        <br />
                        Component Stack:
                        {this.state.errorInfo?.componentStack}
                    </pre>

                    <p>
                        Please lodge a bug report at{" "}
                        <a href="https://github.com/mitmproxy/mitmproxy/issues">
                            https://github.com/mitmproxy/mitmproxy/issues
                        </a>
                        .
                    </p>
                </div>
            );
        }

        return (
            <div id="container" tabIndex={0}>
                <Header />
                <MainView />
                {showCommandBar && <CommandBar key="commandbar" />}
                {showEventLog && <EventLog key="eventlog" />}
                <Footer />
                <Modal />
            </div>
        );
    };

    componentDidMount() {
        window.addEventListener("keydown", this.props.onKeyDown);
    }

    componentWillUnmount() {
        window.removeEventListener("keydown", this.props.onKeyDown);
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        this.setState({ error, errorInfo });
    }
}

export default connect(
    (state: RootState) => ({
        showEventLog: state.eventLog.visible,
        showCommandBar: state.commandBar.visible,
    }),
    {
        onKeyDown,
    },
)(ProxyAppMain);
