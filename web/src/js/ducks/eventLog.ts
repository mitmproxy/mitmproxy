import * as store from "./utils/store";
import { createAction, createSlice, PayloadAction } from "@reduxjs/toolkit";

export const EVENTS_ADD = createAction<EventLogItem>("EVENTS_ADD");
export const EVENTS_RECEIVE = createAction<EventLogItem[]>("EVENTS_RECEIVE");

export enum LogLevel {
    debug = "debug",
    info = "info",
    web = "web",
    warn = "warn",
    error = "error",
}

export interface EventLogItem extends store.Item {
    message: string;
    level: LogLevel;
}

interface EventLogState extends store.State<EventLogItem> {
    visible: boolean;
    filters: { [level in LogLevel]: boolean };
}

const defaultState: EventLogState = {
    visible: false,
    filters: { debug: false, info: true, web: true, warn: true, error: true },
    ...store.defaultState,
};

const eventLogSlice = createSlice({
    name: "eventLog",
    initialState: defaultState,
    reducers: {
        toggleVisibility: (state) => {
            state.visible = !state.visible;
        },
        toggleFilter: (state, action: PayloadAction<LogLevel>) => {
            const newFilters = {
                ...state.filters,
                [action.payload]: !state.filters[action.payload],
            };
            const storeState = store.reduce(
                state,
                store.setFilter<EventLogItem>((log) => newFilters[log.level]),
            );
            return {
                ...state,
                ...storeState,
                filters: newFilters,
            };
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(EVENTS_ADD, (state, action) => ({
                ...state,
                ...store.reduce(
                    state,
                    store.add(
                        action.payload,
                        (log: EventLogItem) => state.filters[log.level],
                    ),
                ),
            }))
            .addCase(EVENTS_RECEIVE, (state, action) => ({
                ...state,
                ...store.reduce(
                    state,
                    store.receive(
                        action.payload,
                        (log: EventLogItem) => state.filters[log.level],
                    ),
                ),
            }));
    },
});

export const { toggleVisibility, toggleFilter } = eventLogSlice.actions;
export default eventLogSlice.reducer;

export function add(message: string, level: LogLevel = LogLevel.web) {
    return EVENTS_ADD({
        id: Math.random().toString(),
        message,
        level,
    });
}
