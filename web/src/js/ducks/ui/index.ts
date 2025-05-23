import { combineReducers } from "redux";
import flow from "./flow";
import modal from "./modal";
import optionsEditor from "./optionsEditor";
import tabs from "./tabs";
import filter from "./filter";

// TODO: Just move ducks/ui/* into ducks/?
export default combineReducers({
    flow,
    modal,
    optionsEditor,
    tabs,
    filter,
});
