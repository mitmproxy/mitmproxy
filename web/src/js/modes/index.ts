import { partition, rpartition } from "../utils";

export interface ModeState {
    active: boolean;
    error?: string;
    listen_port?: number;
    listen_host?: string;
    // The UI ID is used to uniquely identify the server when doing async updates with createModeUpdateThunk
    ui_id?: number;
}

export const includeListenAddress = (
    modeNameAndData: string,
    state: Pick<ModeState, "listen_host" | "listen_port">,
): string => {
    if (state.listen_host && state.listen_port) {
        return `${modeNameAndData}@${state.listen_host}:${state.listen_port}`;
    } else if (state.listen_port) {
        return `${modeNameAndData}@${state.listen_port}`;
    } else {
        return modeNameAndData;
    }
};

export interface RawSpecParts {
    full_spec: string;
    name: string;
    data?: string;
    listen_host?: string;
    listen_port?: number;
}

export const parseSpec = (full_spec: string): RawSpecParts => {
    let [head, listenAt] = rpartition(full_spec, "@");

    if (!head) {
        head = listenAt;
        listenAt = "";
    }

    const [name, data] = partition(head, ":");
    let listen_host: string | undefined, listen_port: number | undefined;

    if (listenAt) {
        let port: string;
        if (listenAt.includes(":")) {
            [listen_host, port] = rpartition(listenAt, ":");
        } else {
            listen_host = "";
            port = listenAt;
        }
        if (port) {
            listen_port = parseInt(port, 10);
            if (isNaN(listen_port) || listen_port < 0 || listen_port > 65535) {
                throw new Error(`invalid port: ${port}`);
            }
        }
    }
    return {
        full_spec,
        name,
        data,
        listen_host,
        listen_port,
    };
};
