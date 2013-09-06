/*
 * This report script summarizes all POSTed form data in a JSON array.
 * Great for a quick check to see whether there are any interesting POST requests in your data.
 */
require(["dojo/promise/all"], function(all) {
  
  traffic.query().then(function(resultSet){
  
    //filter all requests for POST requests with form data
    var requests = resultSet.filter(function(flow){
      return flow.request.method === "POST" && RequestUtils.hasFormData(flow.request);
    });
    
    console.log("Matched requests: "+requests.length+" of "+resultSet.length);
    if(requests.length === 0)
      return alert("No POST requests found!");
    
    var data = {};			//Collects all POST data.
    
    //Handles incoming formdata and adds it to the data obj.
    function handleFormData(flow, formData) {
      
      var prettyData = {};
      for(var i=0; i<formData.length; i++){
        
        var name = _.escape(formData[i].name);
        var value = _.escape(formData[i].value);
        
        //if two or more form elements share the same name, collect all values in an array
        if (name in prettyData){
          if(Array.isArray(prettyData[name]))
            prettyData[name].push(value); //array present
          else
            prettyData[name] = [prettyData[name],value]; //single obj present
        } else {
          prettyData[name] = value; //not present
        }
        
      }
      
      var key = "<span class=openDetail data-flow-id="+parseInt(flow.id)+">"+_.escape(RequestUtils.getFullPath(flow.request))+"</span>";
      data[key] = prettyData;
    }
    
    //getFormData() and getContent() are  async,
    //they both return a dojo promise.
    //This array collects all promises to trigger the result
    //output as soon as they are ready.
    //Promises are covered in dojos Deferred tutorial.
    var promises = []; 	
    
    //For reach request, request its form data and push the returned promise into promises.
    requests.forEach(function(flow){
      var promise = RequestUtils.getFormData(flow.request).then(handleFormData.bind(undefined, flow));
      promises.push(promise);
    });
    
    //dojo/promise/all() gets fulfilled when all passed promises are fulfilled.
    all(promises).then(function(){
      var pre = domConstruct.create("pre",{},out,"only");
      //flowJSON formats flows
      pre.innerHTML = JSON.stringify(data,undefined,"\t");
      //Register event listener for flows and open detail view when clicked.
      on(pre, ".openDetail:click",function(){
        detailView.showDetails(traffic.get(parseInt(this.dataset.flowId)));
      });
    });
    
  });
});