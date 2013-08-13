/*
 * This report script shows a scatter plot with requests over time
 */
require([
  "mitmproxy/util/formatSize",
  "dojox/charting/Chart",
  "dojox/charting/themes/Claro",
  "dojox/charting/plot2d/Scatter",
  "dojox/charting/action2d/Tooltip",
  "dojox/charting/action2d/Magnify",
  "dojox/charting/plot2d/Markers",
  "dojox/charting/axis2d/Default",
], function(formatSize, Chart, theme, Scatter, Tooltip, Magnify, Highlight) {
  
  var hosts = {}; // hostname -> y plot value
  var hostcount = 0; //number of known hosts
  var data = [];  
  // Iterate over all flows and sum up content lengths
  traffic.query().forEach(function(flow){
    var host = flow.request.host;
    
    if(!(host in hosts))
      hosts[host] = hostcount++;
    data.push(
      {
        x:flow.request.timestamp_start,
        y:hosts[host],
        text: flow.request.path,
        flow: flow
      });
  });
  
  
  // Create the chart within it's "holding" node
  a = document.createElement("div");
  a.style.width = "100%";
  out.appendChild(a); 
  var chart = new Chart(a,{
    title: "Requests over time"
  });
  
  // Set the theme
  chart.setTheme(theme);
  
  // Add the only/default plot
  chart.addPlot("default", {
    type: Scatter,
    markers: true,
  });
  
  var labels = [];
  labels.push({text:"",value:-1});
  for(i in hosts){
    labels.push({text:i,value:hosts[i]})
  }
  labels.push({text:"",value:hostcount});
  
  a.style.height = (200+labels.length*10)+"px";
  
  //Add axes
  chart.addAxis("x", {
    fixUpper: "minor",
    fixLower: "minor",
    labelFunc: function(a){
      return (new Date(a*1000)).toLocaleTimeString();
    }
  });
  chart.addAxis("y", { 
    labels: labels, 
    vertical: true, 
    min: -0.5, max: hostcount-0.5,
    dropLabels: false,
    minorTickStep: 1,
    majorTickStep: 1
  });
  
  // Add the series of data
  chart.addSeries("default",data);
  
  chart.connectToPlot( "default", function(evt){
    if(!(evt.type === "onclick" && evt.element === "marker"))
      return;
    detailView.showDetails(data[evt.index].flow);
    chart.resize();
  })
  
  //Add tooltip
  var tip = new Tooltip(chart,"default");
  
  var magnify = new Magnify(chart, "default");
  
  // Render the chart!
  chart.render();
  chart.resize();
  
});