$(document).ready(function(){
  // Evento para exibir o modal com os detalhes do ato
  $('.act-link').on('click', function(e){
    e.preventDefault();
    var actTipo = $(this).data('acttipo');
    var actAno = $(this).data('actano');
    var actTexto = $(this).data('acttexto');
    var actIdentificador = $(this).data('actidentificador');
    var actArquivo = $(this).data('actarquivo');

    $('#actModalLabel').text(actIdentificador);
    $('#modalActTipo').text(actTipo);
    $('#modalActAno').text(actAno);
    $('#modalActTexto').text(actTexto);

    // Constrói o link para o PDF com parâmetro de busca (opcional)
    var searchParam = "#search=" + encodeURIComponent(actTexto);
    $('#modalActArquivo').attr('href', actArquivo + searchParam);

    var actModal = new bootstrap.Modal(document.getElementById('actModal'));
    actModal.show();
  });

  // Variável para armazenar o nome da pessoa selecionada para rede
  var selectedPerson = "";

  // Ao clicar no botão "Rede"
  $('.rede-btn').on('click', function(e){
    e.stopPropagation(); // Evita o disparo do collapse
    selectedPerson = $(this).data('person');
    var networkLevelModal = new bootstrap.Modal(document.getElementById('networkLevelModal'));
    networkLevelModal.show();
  });

  // Ao escolher o nível de rede no modal
  $('.network-level-btn').on('click', function(){
    var level = $(this).data('level');
    // Fecha o modal de seleção do nível
    var networkLevelModalEl = document.getElementById('networkLevelModal');
    var networkLevelModal = bootstrap.Modal.getInstance(networkLevelModalEl);
    networkLevelModal.hide();

    // Atualiza o título do modal de rede
    $('#networkPersonName').text(selectedPerson);

    // Carrega a rede para a pessoa selecionada e o nível escolhido
    loadNetworkForPerson(selectedPerson, level);
  });

  // Função para carregar e renderizar a rede de uma pessoa específica usando D3
  function loadNetworkForPerson(person, level) {
    // Se o nome contém "(", extraímos apenas a parte anterior ao parênteses.
    var queryPerson = person;
    if (queryPerson.indexOf("(") !== -1) {
      queryPerson = queryPerson.split(" (")[0];
    }
    
    // Seleciona o SVG do modal e limpa o conteúdo anterior
    var svg = d3.select("#networkGraph");
    svg.selectAll("*").remove();

    // Obtém dimensões do SVG
    var width = parseInt(svg.style("width"));
    var height = parseInt(svg.style("height"));

    // Cria um grupo para o grafo e aplica zoom
    var graphContainer = svg.append("g")
                            .attr("class", "graph-container");

    var zoom = d3.zoom()
                 .on("zoom", function(event) {
                   graphContainer.attr("transform", event.transform);
                 });
    svg.call(zoom);

    // Requisição AJAX para obter os dados do grafo usando o endpoint /search
    $.post('/search', { query: queryPerson, level: level }, function(data) {
      if (data.graph_data) {
        var nodes = data.graph_data.nodes;
        var links = data.graph_data.links;

        // Cria a simulação do grafo
        var simulation = d3.forceSimulation(nodes)
          .force("link", d3.forceLink(links).id(function(d) { return d.id; }).distance(100))
          .force("charge", d3.forceManyBody().strength(-300))
          .force("center", d3.forceCenter(width / 2, height / 2));

        // Cria os links
        var link = graphContainer.append("g")
                        .attr("class", "links")
                        .selectAll("line")
                        .data(links)
                        .join("line")
                        .attr("class", "link")
                        .style("stroke", "#999")
                        .style("stroke-width", 1.5);

        // Cria os nós
        var node = graphContainer.append("g")
                        .attr("class", "nodes")
                        .selectAll("g")
                        .data(nodes)
                        .join("g")
                        .attr("class", "node");

        node.append("circle")
          .attr("r", 5)
          .attr("fill", function(d) { return d.type === "Pessoa" ? "#ff7f0e" : "#1f77b4"; });

        node.append("text")
          .text(function(d) { return d.label; })
          .attr("x", 8)
          .attr("y", 3);

        simulation
          .nodes(nodes)
          .on("tick", ticked);

        simulation.force("link").links(links);

        function ticked() {
          link.attr("x1", function(d) { return d.source.x; })
              .attr("y1", function(d) { return d.source.y; })
              .attr("x2", function(d) { return d.target.x; })
              .attr("y2", function(d) { return d.target.y; });

          node.attr("transform", function(d) {
            return "translate(" + d.x + "," + d.y + ")";
          });
        }

        // Exibe o modal da rede
        var networkModal = new bootstrap.Modal(document.getElementById('networkModal'));
        networkModal.show();
      } else {
        alert("Nenhum resultado encontrado para a rede.");
      }
    }).fail(function(xhr) {
      var error = xhr.responseJSON?.error || 'Erro desconhecido.';
      alert(error);
    });
  }
});
