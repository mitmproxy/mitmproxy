/*
 * This report script checks for common security shortcomings on webapges
 */

//you can get the flow id by hovering over the leftmost 10px of the traffic table.
var flow_id = 2;
var flow = traffic.get(flow_id).then(function(flow){

  domConstruct.create("h2",{innerHTML:"Audit for "+_.escape(RequestUtils.getFullPath(flow.request))},out);
  domConstruct.create(
    "p",
    {
      innerHTML:
      "Please note that this audit checks for best practices, not for security holes. "+
      "A website can be fully secure with all headers absent. "+
      "However, usually it's a good idea to limit the possible impact of security breaches in your page by specifying these headers."}, out);
  var result = {
    "Good": [],
    "Neutral": [],
    "Bad": []
  };
  var style = {
    "Good":"color: green",
    "Neutral":"",
    "Bad":"color: red"
  }
  
  function goodHeader(name, value) {
    result.Good.push("The page is served with a limiting <code>"+name+"</code> header: <code>"+_.escape(value)+"</code>"); 
  }
  function badHeader(name, suffix) {
    result.Bad.push("The page is not served with a <code>"+name+"</code> header" + (suffix || "."));
  }
  
  // X-Frame-Options Header
  var xFrameOptions = ResponseUtils.getHeader(flow.response,/X-Frame-Options/i);
  if(!xFrameOptions || !xFrameOptions.match(/Deny|SameOrigin|Allow-From/i)) {
    badHeader("X-Frame-Options"," and could be vulnerable to clickjacking.");
  } else {
    goodHeader("X-Frame-Options",xFrameOptions);
  }
  
  // Strict-Transport-Security Header
  var isSSL = (flow.request.scheme === "https");
  if(isSSL){
    
    var stt = ResponseUtils.getHeader(flow.response,/Strict-Transport-Security/i);
    if(!stt) {
      badHeader("Strict-Transport-Security"," and is vulnerable to man-in-the-middle attacks therefore.");
    } else if(!stt.match(/includeSubDomains/i)) {
      result.Neutral.push("The page is served with a limiting <code>Strict-Transport-Security</code> header. However, the header does not cover subdomains: <code>"+_.escape(stt)+"</code>"); 
    } else {
      goodHeader("Strict-Transport-Security",stt);
    }
    
  } else {
    result.Neutral.push("The page is not secured by SSL.");
  }
  
  // X-Content-Security-Policy
  var xCSP = ResponseUtils.getHeader(flow.response,/X-Content-Security-Policy/i);
  if(xCSP) {
    goodHeader("X-Content-Security-Policy",xCSP);
  } else {
    badHeader("X-Content-Security-Policy",".");
  }
  
  // X-Content-Type-Options
  var xCTO = ResponseUtils.getHeader(flow.response,/X-Content-Type-Options/i);
  var CT = ResponseUtils.getHeader(flow.response,/Content-Type/i);
  if(!CT)
    badHeader("Content-Type",".");
  if(CT && xCTO && !!xCTO.match(/nosniff/i)) {
    goodHeader("X-Content-Type-Options",xCTO);
  } else {
    badHeader("X-Content-Type-Options",". This could allow MIME-type confusion.");
  }
  
  // X-XSS-Protection
  var xXSSP = ResponseUtils.getHeader(flow.response,/X-XSS-Protection/i);
  if(xXSSP) {
    goodHeader("X-XSS-Protection",xXSSP);
  } else {
    badHeader("X-XSS-Protection",".");
  }
  
  //Output
  for(i in result){
    domConstruct.create("h3",{innerHTML:i, style: style[i]},out);
    var ul = domConstruct.create("ul",{},out);
    result[i].forEach(function(bp){
      domConstruct.create("li",{"innerHTML":bp},ul); 
    });
  }
  
  detailView.showDetails(flow);
},function(){
  alert("Flow not found!");
});