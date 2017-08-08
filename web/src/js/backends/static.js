/*
 * This backend uses the REST API only to host static instances,
 * without any Websocket connection.
 */
import { fetchApi } from "../utils"

const CMD_RESET = 'reset'

export default class StaticBackend {
   constructor(store) {
       this.activeFetches = {}
       this.store = store
       this.onOpen()
   }

   onOpen() {
        this.fetchData("settings")
        this.fetchData("flows")
        this.fetchData("events")
        this.fetchData("options")
   }

   fetchData(resource) {
       fetchApi(`/${resource}`)
           .then(res => res.json())
           .then(json => {
               this.receive(resource, json)
           })
   }

   receive(resource, data) {
       let type = `${resource}_RECEIVE`.toUpperCase()
       this.store.dispatch({ type, cmd: "receive", resource, data })
   }

}
