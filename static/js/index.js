$(document).ready(function () {
    const svg = d3.select("#graph");
    const width = parseInt(svg.style("width"));
    const height = parseInt(svg.style("height"));
  
    let simulation = d3.forceSimulation()
      .force("link", d3.forceLink().id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));
  
    let zoom = d3.zoom()
      .on("zoom", (event) => {
        svg.select("g.graph-container").attr("transform", event.transform);
      });
    svg.call(zoom);
  
    const graphContainer = svg.append("g")
      .attr("class", "graph-container");
  
    // Função para carregar dados do grafo
    function loadGraph(level) {
      const query = $('#query').val();
    
      if (!query) {
        alert('Por favor, insira um nome ou CPF.');
        return;
      }
    
      $.post('/search', { query: query, level: level }, function (data) {
        if (data.graph_data) {
          const { nodes, links } = data.graph_data;
    
          // Contagem de nós e arestas
          const totalNodes = nodes.length;
          const totalEdges = links.length;
    
          // Contagem por tipo de nó
          const nodeTypes = {};
          nodes.forEach(node => {
            nodeTypes[node.type] = (nodeTypes[node.type] || 0) + 1;
          });
    
          // Formatando a exibição dos tipos de nós
          const typeSummary = Object.entries(nodeTypes)
            .map(([type, count]) => `${type}: ${count}`)
            .join(", ");
    
          // Atualizando a caixa de informações
          $('#total-nodes').text(`Nós: ${totalNodes}`);
          $('#total-edges').text(`Arestas: ${totalEdges}`);
          $('#type-nodes').text(`Tipos: ${typeSummary}`);
    
          // Limpa o grafo anterior
          graphContainer.selectAll("*").remove();
          simulation.stop();
    
          // Reinicia a simulação
          simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));
    
          const link = graphContainer.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("class", "link")
            .style("stroke-width", 1.5);
    
          const node = graphContainer.append("g")
            .attr("class", "nodes")
            .selectAll("g")
            .data(nodes)
            .join("g")
            .attr("class", "node");
    
          node.append("circle")
            .attr("r", 5)
            .attr("fill", d => d.type === "Pessoa" ? "#ff7f0e" : "#1f77b4");
    
          node.append("text")
            .text(d => d.label)
            .attr("x", 8)
            .attr("y", 3);
    
          simulation
            .nodes(nodes)
            .on("tick", ticked);
    
          simulation.force("link").links(links);
    
          function ticked() {
            link
              .attr("x1", d => d.source.x)
              .attr("y1", d => d.source.y)
              .attr("x2", d => d.target.x)
              .attr("y2", d => d.target.y);
    
            node.attr("transform", d => `translate(${d.x},${d.y})`);
          }
        } else {
          alert('Nenhum resultado encontrado.');
        }
      }).fail(function (xhr) {
        const error = xhr.responseJSON?.error || 'Erro desconhecido.';
        alert(error);
      });
    }
    
  
    // Ao submeter o formulário, exibe o modal para seleção do nível
    $('#searchForm').submit(function (e) {
      e.preventDefault();
      $('#searchLevelModal').modal('show');
    });
  
    // Eventos para os botões do modal de seleção de nível
    $('#modalLevel1, #modalLevel2').click(function () {
      const level = $(this).data('level');
      $('#searchLevelModal').modal('hide');
      loadGraph(level);
    });
  
    // Geração do Relatório: redireciona para /report passando o parâmetro de consulta
    $('#generateReport').click(function () {
      const query = $('#query').val();
      if (!query) {
        alert('Por favor, insira um nome ou CPF antes de gerar o relatório.');
        return;
      }
      window.location.href = `/report?query=${encodeURIComponent(query)}`;
    });
  
    // Evento para sugestões de nomes conforme o usuário digita
    $('#query').on('input', function(){
      const query = $(this).val();
      if(query.length < 2) {  // Opcional: só busca sugestões com pelo menos 2 caracteres
        $('#suggestions').empty();
        return;
      }
      $.ajax({
        url: '/suggest',
        data: { q: query },
        success: function(data) {
          const suggestions = data.suggestions;
          const $datalist = $('#suggestions');
          $datalist.empty();
          suggestions.forEach(function(item) {
            $datalist.append('<option value="'+item+'"></option>');
          });
        }
      });
    });
  });
  