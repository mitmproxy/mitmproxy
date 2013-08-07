require(["d3"],function(d3){

  //Node Opacity: Last Activity
  //Node radius:  Content Size
  //Node Color:   Random
  //Line Color:   Request Count
  
  // There is no proper destructor. :(
  // Reload the page if you experience performance issues.
  
  var flows = traffic.query();
  
  var hostMapping = {},
      hosts = [],
      linkMapping = {},
      links = [],
      minTime,
      maxTime,
      maxSize,
      maxRequestCount,
      start = function(){};
  
  /* ### Prepare data ### */
  function addHost(addr,message){
    
    //Add new element if neccessary
    if(!(addr in hostMapping)){
      hostMapping[addr] = {
        index: hosts.length
      };
      hosts.push({
        name: addr,
        size: 0,
        sourceCount: 0,
        targetCount: 0
      });
    }
    
    //set element props
    var host = hostMapping[addr];
    var data = hosts[host.index];
    data.size += message.contentLength;
    data.timestamp = Math.max(data.timestamp || 0, message.timestamp_end);
    
    //set general min max props
    maxSize = Math.max(maxSize || 0, data.size);
    minTime = Math.min(minTime || Number.POSITIVE_INFINITY,message.timestamp_end);
    maxTime = Math.max(maxTime || Number.NEGATIVE_INFINITY,message.timestamp_end);
    
    //data.flows.push(flow);
    return host.index;
  }
  function getLinkName(flow){
    var source = flow.request.client_conn.address[0];
    var target = flow.request.host;
    return source + "-" + target;
  }
  function addFlow(flow){
    var source = flow.request.client_conn.address[0];
    var target = flow.request.host;
    var linkName = getLinkName(flow);
    
    var sourceIndex = addHost(source,flow.request);
    hosts[sourceIndex].sourceCount++;
    var targetIndex = addHost(target,flow.response);
    hosts[targetIndex].targetCount++;
    
    if(!(linkName in linkMapping)){
      linkMapping[linkName] = links.length;
      links.push({
        requestCount : 0,
        source: sourceIndex,
        target: targetIndex
      });
    }
    var link = links[linkMapping[linkName]];
    link.requestCount++;
    maxRequestCount = Math.max(maxRequestCount || 10, link.requestCount);
  }
  
  /* ### Graph Styling ### */
  var radiusScale = d3.scale.log().range([3, 10]);
  var opacityScale = d3.scale.pow().exponent(2).range([0.1,1]);
  var colorScale = d3.scale.category20();
  var linkColorScale = d3.interpolateRgb("#666", "#C73C3C");
  
  function updateNodeSelectionStyle(nodes){
    radiusScale.domain([1, maxSize]);
    opacityScale.domain([minTime,maxTime]);
    nodes.attr("r", function(d){ return radiusScale(d.size+1);})
         .style("opacity",function(d) { return opacityScale(d.timestamp); });
  }
  function updateLinkSelectionStyle(links){
   links.attr("stroke", function(d) { return linkColorScale(d.requestCount/maxRequestCount); });
    links.each(function(d){
      if(d.highlight){
        d.highlight = false;
        d3.select(this).transition().attr("stroke","yellow")
         							 .transition().attr("stroke", function(d) { return linkColorScale(d.requestCount/maxRequestCount); });
      }
    });
  }
  
  /* ### Draw graph ### */
  flows.forEach(addFlow).then(function(){
        
    //viewport size
    var width = Math.max( $(out).width() * 0.85, 480 );  //width
    var height = Math.max( $(out).height() * 0.85, 300 ); //height
 
    var svg = d3
      .select(out)
      .append("svg")
      .attr("height", height)
      .attr("width", width);
    
    var node = svg.selectAll("circle"),
    		link = svg.selectAll("line");
    
    var force = d3.layout.force()
      .charge(-100)
      .linkDistance(100)
      .on("tick", tick)
      .nodes(hosts)
      .links(links)
      .size([width, height]);
    
    
    start = function(){
    
      link = link.data(force.links())
      link.enter().append("line")
      							.style("stroke-width","1px")
      							.each(function(d){d.node = d3.select(this);})
      							.call(updateLinkSelectionStyle);
      
      node = node.data(force.nodes());
      node.enter().append("circle")
      							.style("fill", function(d) { return colorScale(d.name); })
      							.call(force.drag)
      						.append("title")
										.text(function(d) { return d.name; });
      
      force.start();
    };
    start();
    
    //To keep performance up, update not more than 20 nodes and links per second
    var i=0, j=0;
    function updateStyles(){
      var c = 0;
      while(c < 10){
        c++;
        i = (i+1) % link[0].length;
        j = (j+1) % node[0].length;
        updateLinkSelectionStyle(d3.select(link[0][i]));
        updateNodeSelectionStyle(d3.select(node[0][j]));
      }
      window.setTimeout(updateStyles,200,i,j);
    }
    window.setInterval(updateStyles, 500);

    function tick() {
      node.attr("cx", function(d) { return d.x; })
      		.attr("cy", function(d) { return d.y; })
      
      link.attr("x1", function(d) { return d.source.x; })
      		.attr("y1", function(d) { return d.source.y; })
      		.attr("x2", function(d) { return d.target.x; })
      		.attr("y2", function(d) { return d.target.y; });
    }
    
  });
  
  /* ### live observe ### */
  flows.observe(function(flow){
    var oldl = links.length;
    addFlow(flow);
    if(oldl !== links.length)
    	start();
    
    //highlight link
    var linkName = getLinkName(flow);
    var link = links[linkMapping[linkName]];
    link.highlight = true;
    updateLinkSelectionStyle(link.node);
    
  });
});