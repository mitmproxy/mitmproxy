//All dependencies are cached by the AMD loader by default.
//Dirty Hack to uncache
for(k in require.modules) 
  k.indexOf("ReportScripts") === 0 && delete require.modules[k];

require(["require","./dep"], function(require,dep) {
  out.textContent = dep+"!";
});