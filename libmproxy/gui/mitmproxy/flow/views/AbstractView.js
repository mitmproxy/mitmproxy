/**
 * Flow View Interface. All views should implement this.
 */
define(["dojo/_base/declare", "../../util/_ReactiveTemplatedWidget", "../FlowBindings","../MessageUtils","../RequestUtils","../ResponseUtils", "dojo/text!./templates/BasicContentView.html"],
         function(declare, _ReactiveTemplatedWidget, flowBindings, MessageUtils, RequestUtils, ResponseUtils, basicContentViewTemplate) {
           
  var AbstractView = declare([_ReactiveTemplatedWidget], {
    bindings: flowBindings,
    context: {
      MessageUtils: MessageUtils,
      RequestUtils: RequestUtils,
      ResponseUtils: ResponseUtils
    },
    buildRendering: function(){
      if((!RequestUtils.hasContent(this.model.request)) && (!this.model.response || !ResponseUtils.hasContent(this.model.response))){
        this.templateString = basicContentViewTemplate;
      }
      this.inherited(arguments);
    },
    templateString: undefined // Template file to fill
  });
  
  AbstractView.className = undefined;// a list of classes following the pattern flow-flowType
  AbstractView.matches = function (flow) {
    //function that returns whether true if the view should be used to display the flow, false otherwise.
  };
  
  return AbstractView;
});