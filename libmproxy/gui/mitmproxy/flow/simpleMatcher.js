define(["./RequestUtils","./ResponseUtils"],function(RequestUtils,ResponseUtils){
  
  //Simple matching function generator for View.matches(flow) that performs a match based on the supplied content type and filename.
  
  return function(contentType, filename){
    return function(flow) {
      var contentType_ = flow.response ? ResponseUtils.getContentType(flow.response) : false;
      if (contentType && contentType_ && !!contentType_.match(contentType))
        return true;
      var filename_ = RequestUtils.getFilename(flow.request);
      if (filename && filename_ && !!filename_.match(filename))
        return true;
      return false;
    };
  };
});