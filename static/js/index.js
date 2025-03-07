$(document).ready(function () {
  // Configura o canvas e o contexto
  const canvas = d3.select("#graph").node();
  const context = canvas.getContext("2d");
  const width = canvas.width = canvas.clientWidth;
  const height = canvas.height = canvas.clientHeight;

  // Variáveis globais para os dados e zoom
  let nodes = [], links = [];
  let currentTransform = d3.zoomIdentity;
  let worker;  // Web Worker para a simulação

  // Configura o zoom no canvas
  d3.select(canvas)
    .call(d3.zoom()
      .scaleExtent([0.1, 10])
      .on("zoom", (event) => {
        currentTransform = event.transform;
        draw();
      })
    );

  // Função para desenhar o grafo no canvas
  function draw() {
    context.save();
    context.clearRect(0, 0, width, height);
    // Aplica o transform do zoom
    context.translate(currentTransform.x, currentTransform.y);
    context.scale(currentTransform.k, currentTransform.k);

    // Desenha as arestas (links)
    context.strokeStyle = "#999";
    context.lineWidth = 1.5;
    links.forEach(link => {
      // Se os nós fonte e destino tiverem sido atualizados pela simulação
      context.beginPath();
      context.moveTo(link.source.x, link.source.y);
      context.lineTo(link.target.x, link.target.y);
      context.stroke();
    });

    // LOD: Se o zoom estiver baixo, desenha somente os nós do tipo "Ato"
    nodes.forEach(node => {
      if (currentTransform.k < 0.7 && node.type !== "Ato") return;

      context.beginPath();
      context.arc(node.x, node.y, 5, 0, 2 * Math.PI);
      context.fillStyle = node.type === "Pessoa" ? "#ff7f0e" : "#1f77b4";
      context.fill();
      context.strokeStyle = "#fff";
      context.lineWidth = 1.5;
      context.stroke();

      // Desenha o rótulo somente se o zoom estiver suficiente
      if (currentTransform.k >= 1) {
        context.font = "10px sans-serif";
        context.fillStyle = "#000";
        context.fillText(node.label, node.x + 8, node.y + 3);
      }
    });
    context.restore();
  }

  // Função para carregar dados do grafo (sem alterações na lógica de busca)
  function loadGraph(level) {
    const query = $('#query').val();
  
    if (!query) {
      alert('Por favor, insira um nome ou CPF.');
      return;
    }
  
    $.post('/search', { query: query, level: level }, function (data) {
      if (data.graph_data) {
        ({ nodes, links } = data.graph_data);
  
        // Atualiza a contagem na interface
        $('#total-nodes').text(`Nós: ${nodes.length}`);
        $('#total-edges').text(`Arestas: ${links.length}`);
  
        // Formata a contagem por tipo
        const nodeTypes = {};
        nodes.forEach(node => {
          nodeTypes[node.type] = (nodeTypes[node.type] || 0) + 1;
        });
        const typeSummary = Object.entries(nodeTypes)
          .map(([type, count]) => `${type}: ${count}`)
          .join(", ");
        $('#type-nodes').text(`Tipos: ${typeSummary}`);
  
        // Se já houver um worker ativo, encerra-o
        if (worker) worker.terminate();
  
        // Inicializa o Web Worker para a simulação de força
        worker = new Worker('/static/js/forceWorker.js');
        worker.postMessage({
          type: 'start',
          nodes: nodes,
          links: links,
          width: width,
          height: height
        });
  
        // Recebe os ticks da simulação do Worker e redesenha o canvas
        worker.onmessage = function (e) {
          if (e.data.type === 'tick') {
            nodes = e.data.nodes;
            links = e.data.links;
            draw();
          }
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
    if(query.length < 2) {
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
