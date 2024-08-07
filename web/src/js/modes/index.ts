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
