import * as React from "react";
import { ModeToggle } from "./ModeToggle";
import Dropdown, { MenuItem } from "../common/Dropdown";
import ValueEditor from "../editors/ValueEditor";
import { useAppDispatch } from "../../ducks";
import {
    removeServer,
    ReverseState,
    setActive,
    setDestination,
    setListenHost,
    setListenPort,
    setProtocol,
} from "../../ducks/modes/reverse";
import { ReverseProxyProtocols } from "../../backends/consts";

interface ReverseToggleRowProps {
    server: ReverseState;
}

export default function ReverseToggleRow({ server }: ReverseToggleRowProps) {
    const dispatch = useAppDispatch();

    const protocols = Object.values(ReverseProxyProtocols);

    const inner = (
        <span>
            &nbsp;<b>{server.protocol} </b>
            <span className="caret" />
        </span>
    );

    const deleteServer = async () => {
        if (server.active) {
            await dispatch(setActive({ server, value: false })).unwrap();
        }
        await dispatch(removeServer(server));
    };

    return (
        <div>
            <ModeToggle
                value={server.active}
                onChange={() => {
                    dispatch(setActive({ server, value: !server.active }));
                }}
            >
                Forward
                <Dropdown
                    text={inner}
                    className="btn btn-default btn-xs mode-reverse-dropdown"
                    options={{ placement: "bottom" }}
                >
                    {protocols.map((prot) => (
                        <MenuItem
                            key={prot}
                            onClick={() =>
                                dispatch(setProtocol({ server, value: prot }))
                            }
                        >
                            {prot}
                        </MenuItem>
                    ))}
                </Dropdown>{" "}
                traffic from{" "}
                <ValueEditor
                    className="mode-reverse-input"
                    content={server.listen_host || ""}
                    onEditDone={(value) =>
                        dispatch(setListenHost({ server, value }))
                    }
                    placeholder="*"
                />
                <ValueEditor
                    className="mode-reverse-input"
                    content={String(server.listen_port || "")}
                    onEditDone={(value) =>
                        dispatch(
                            setListenPort({
                                server,
                                value: value as unknown as number,
                            }),
                        )
                    }
                    placeholder="8080"
                />{" "}
                to{" "}
                <ValueEditor
                    className="mode-reverse-input"
                    content={server.destination?.toString() || ""}
                    onEditDone={(value) =>
                        dispatch(setDestination({ server, value }))
                    }
                    placeholder="example.com"
                />
                <i
                    className="fa fa-fw fa-trash fa-lg"
                    aria-hidden="true"
                    onClick={deleteServer}
                ></i>
            </ModeToggle>
            {server.error && (
                <div className="mode-error text-danger">{server.error}</div>
            )}
        </div>
    );
}
