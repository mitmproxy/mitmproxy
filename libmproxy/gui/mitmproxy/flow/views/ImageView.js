/**
 * Flow subclass responsible for proper display of image files. Basically
 * loading file content as an image and subscribing to .load() events to display filesize etc.
 */
define([ "dojo/_base/declare","./AbstractView", "../simpleMatcher",
         "dojo/text!./templates/ImageView.html"],
         function(declare, AbstractView, simpleMatcher, template) {
   
  var ImageView = declare([AbstractView], {
    onImageLoad: function(e){
      this.imageWidth.textContent = e.target.naturalWidth;
      this.imageHeight.textContent = e.target.naturalHeight;
    },
    templateString: template
  });
  
  ImageView.className = "flow-image";
  ImageView.matches = simpleMatcher(/image/i, /\.(gif|png|jpg|jpeg)$/i);

  return ImageView;
});