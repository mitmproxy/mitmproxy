import React, { Component } from "react";
import ValueEditor from "./ValueEditor";
import { isEqual } from "lodash";
import classnames from "classnames";

type Item = [key: string, value: string];

type RowProps = {
    item: Item;
    onEditStart: () => void;
    onEditDone: (newItem: Item) => void;
    onClickEmptyArea: () => void;
    onTabNext: () => void;
};

class Row extends Component<RowProps> {
    container = React.createRef<HTMLDivElement>();
    nameInput = React.createRef<ValueEditor>();
    valueInput = React.createRef<ValueEditor>();

    render = () => {
        const [key, value] = this.props.item;

        return (
            <div
                ref={this.container}
                className="kv-row"
                onClick={this.onClick}
                onKeyDownCapture={this.onKeyDown}
            >
                <ValueEditor
                    ref={this.nameInput}
                    className="kv-key"
                    content={key}
                    onEditStart={this.props.onEditStart}
                    onEditDone={(newKey) =>
                        this.props.onEditDone([newKey, value])
                    }
                    selectAllOnClick={true}
                />
                :&nbsp;
                <ValueEditor
                    ref={this.valueInput}
                    className="kv-value"
                    content={value}
                    onEditStart={this.props.onEditStart}
                    onEditDone={(newVal) =>
                        this.props.onEditDone([key, newVal])
                    }
                    placeholder="empty"
                    selectAllOnClick={true}
                />
            </div>
        );
    };

    onClick = (e: React.MouseEvent) => {
        if (e.target === this.container.current) this.props.onClickEmptyArea();
    };

    onKeyDown = (e: React.KeyboardEvent) => {
        if (
            e.target === this.valueInput.current?.input.current &&
            e.key === "Tab"
        ) {
            this.props.onTabNext();
        }
    };
}

type KeyValueListProps = {
    onChange: (newList: Item[]) => void;
    data?: Item[];
    className?: string;
};

type KeyValueListState = {
    currentList: Item[];
    initialList?: Item[];
};

export default class KeyValueListEditor extends Component<
    KeyValueListProps,
    KeyValueListState
> {
    private rowRefs: { [id: number]: Row | null } = {};
    private currentlyEditing?: number;
    private justFinishedEditing?: number;

    state: KeyValueListState = {
        currentList: this.props.data || [],
        initialList: this.props.data,
    };

    static getDerivedStateFromProps(
        props: KeyValueListProps,
        state: KeyValueListState,
    ): KeyValueListState | null {
        if (props.data !== state.initialList)
            return { currentList: props.data || [], initialList: props.data };
        else return null;
    }

    render = () => {
        this.rowRefs = {};

        const rows = this.state.currentList.map((h, row) => {
            return (
                <Row
                    key={row}
                    item={h}
                    onEditStart={() => (this.currentlyEditing = row)}
                    onEditDone={(newItem) => this.onEditDone(row, newItem)}
                    onClickEmptyArea={() => this.onClickEmptyArea(row)}
                    onTabNext={() => this.onTabNext(row)}
                    ref={(e) => {
                        this.rowRefs[row] = e;
                    }}
                />
            );
        });

        return (
            <div
                className={classnames("kv-editor", this.props.className)}
                onMouseDown={this.onMouseDown}
            >
                {rows}
                <div
                    onClick={(e) => {
                        e.preventDefault();
                        this.onClickEmptyArea(
                            this.state.currentList.length - 1,
                        );
                    }}
                    className="kv-add-row fa fa-plus-square-o"
                    role="button"
                    aria-label="Add"
                />
            </div>
        );
    };

    onEditDone = (row: number, newItem: Item) => {
        const newList = [...this.state.currentList];
        if (newItem[0]) {
            newList[row] = newItem;
        } else {
            newList.splice(row, 1);
        }
        this.currentlyEditing = undefined;
        if (!isEqual(this.state.currentList, newList))
            this.props.onChange(newList);
        this.setState({ currentList: newList });
    };

    onClickEmptyArea = (row: number) => {
        if (this.justFinishedEditing) return;
        const newList = [...this.state.currentList];
        newList.splice(row + 1, 0, ["", ""]);
        this.setState({ currentList: newList }, () =>
            this.rowRefs[row + 1]?.nameInput.current?.startEditing(),
        );
    };

    onTabNext = (row: number) => {
        if (row == this.state.currentList.length - 1) {
            this.onClickEmptyArea(row);
        }
    };

    onMouseDown = (_e: React.MouseEvent) => {
        this.justFinishedEditing = this.currentlyEditing;
    };
}
