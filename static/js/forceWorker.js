// forceWorker.js
importScripts("https://d3js.org/d3.v7.min.js");

let simulation;

onmessage = function(e) {
  if (e.data.type === "start") {
    const nodes = e.data.nodes;
    const links = e.data.links;
    const width = e.data.width;
    const height = e.data.height;

    simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .on("tick", () => {
        postMessage({ type: "tick", nodes: nodes, links: links });
      });
  } else if (e.data.type === "stop") {
    if (simulation) simulation.stop();
  }
};
