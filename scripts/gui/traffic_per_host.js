/*
 * This report scripts displays shows a traffic per hostname pie chart.
 */
require([
  "mitmproxy/util/formatSize",
  "dojox/charting/Chart",
  "dojox/charting/themes/Claro",
  "dojox/charting/plot2d/Pie",
  "dojox/charting/action2d/Tooltip",
  "dojox/charting/action2d/MoveSlice",
  "dojox/charting/plot2d/Markers",
  "dojox/charting/axis2d/Default",
], function(formatSize, Chart, theme, Pie, Tooltip, MoveSlice) {
  
  //hosts must occupy at least 2 degrees of the pie
  //if they don't want to get summed up in "other"
  var minimum_percentage = 3 / 360; 
  
  // hostname -> propObj
  var trafficPerHost = {};
  var total = 0;
  
  // Iterate over all flows and sum up content lengths
  traffic.query().forEach(function(flow){
    var host = flow.request.host;
    
    //host = /google|gstatic/.test(host) ? "google" : "facebook";
    
    if(!(host in trafficPerHost))
      trafficPerHost[host] = {y:0,text:"",count:0};
    var size = flow.request.contentLength + flow.response.contentLength;
    trafficPerHost[host].y += size;
    trafficPerHost[host].count += 1;
    total += size;
  });
  
  // Sum up all hosts with less traffic than minimum_percentage
  // into other
  var other = {"y":0,"count": 0}; //virtual "Other" host.
  var minsize = total * minimum_percentage;
  for(host in trafficPerHost) {
    var hostdata = trafficPerHost[host];
    if(hostdata.y < minsize) {
      other.y += hostdata.y;
      other.count += 1;
      delete trafficPerHost[host];
    }
  }
  if(other.count > 0) {
    other.y = Math.max(total * minimum_percentage, other.y);
    //give other a minimum size
    trafficPerHost.Other = other;
  }
  
  //create a Dojo Charting Array from the aggregated data.
  var data = [];
  for (host in trafficPerHost){
    trafficPerHost[host]["tooltip"] = trafficPerHost[host]["count"] + " requests";
    trafficPerHost[host]["text"] = host + " ("+formatSize(trafficPerHost[host]["y"])+")";
    data.push(trafficPerHost[host]);
  }
  
  // Create the chart within it's "holding" node
  a = document.createElement("div");
  a.style.width = "100%";
  a.style.height = "100%";
  out.appendChild(a); 
  var chart = new Chart(a,{
    title: "Traffic per host"
  });
  
 
  
  // Set the theme
  chart.setTheme(theme);
  
  // Add the only/default plot
  chart.addPlot("default", {
    type: Pie,
    markers: true,
    radius:200
  });
  
  // Add axes
  chart.addAxis("x");
  chart.addAxis("y", { vertical: true, fixLower: "major", fixUpper: "major"/*, max: 5000*/ });
  
  // Add the series of data
  chart.addSeries("Traffic",data);
  
  //Add tooltip
  var tip = new Tooltip(chart,"default");
  
  // Create the slice mover
  var mag = new MoveSlice(chart,"default");
  
  // Render the chart!
  chart.render();
  chart.resize();
  
});