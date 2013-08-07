define(["dojo/_base/declare", "dojo/_base/lang", "./BasicContentView", "../simpleMatcher", "../FlowBindings"], 
         function(declare, lang, BasicContentView, simpleMatcher, FlowBindings) {
  
  var jsBindings = lang.mixin({}, FlowBindings);
  jsBindings.displayContent = FlowBindings._displayContent(function(content){
    try {
      var json = JSON.parse(content);
      return JSON.stringify(json,null,"  ");
    } catch(e){
      return content;
    }
  },FlowBindings._prettifyNodeTransform);
  
  var JavaScriptView = declare([BasicContentView],{
    bindings: jsBindings
  });
  
  JavaScriptView.className = "flow-javascript " + BasicContentView.className;
  JavaScriptView.matches = simpleMatcher(/(javascript|json)/i, /(\.js|\.json)$/i);

  return JavaScriptView;
});