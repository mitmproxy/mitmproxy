/*
 * This backend uses the REST API only to host static instances,
 * without any Websocket connection.
 */
import { fetchApi } from "../utils"

export default class StaticBackend {
   constructor(store) {
       this.store = store
       this.onOpen()
   }

   onOpen() {
        this.fetchData("flows")
        this.fetchData("settings")
        // this.fetchData("events") # TODO: Add events log to static viewer.
   }

   fetchData(resource) {
       fetchApi(`./${resource}`)
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
