/* Apenas agregados públicos; nenhuma consulta ao Genderize.io ocorre no navegador. */
'use strict';
const $ = id => document.getElementById(id);
const number = value => value == null ? '—' : new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value);
const percent = value => value == null ? '—' : `${number(value)}%`;
const palette = {female: '#7751a8', male: '#337bad', total: '#18584d'};
let rows = [];
function options(element, values, current) {
  element.replaceChildren(...values.map(value => new Option(value, value)));
  if (values.includes(current)) element.value = current;
}
function baseRows() {
  return rows.filter(r => r.curso === $('course').value && r.tipo_registro === $('kind').value && r.agrupamento === $('grain').value);
}
function updatePeriods() {
  const periods = [...new Set(baseRows().map(r => r.periodo))].sort();
  options($('from'), periods, periods[0]);
  options($('to'), periods, periods.at(-1));
  render();
}
function emptyChart(message) {
  if (window.Plotly) Plotly.purge('chart');
  $('chart').replaceChildren(document.createTextNode(message));
}
function render() {
  const invalid = $('from').value > $('to').value;
  const selected = invalid ? [] : baseRows().filter(r => r.periodo >= $('from').value && r.periodo <= $('to').value).sort((a,b) => a.periodo.localeCompare(b.periodo));
  const sum = key => selected.reduce((n, r) => n + r[key], 0);
  const n = sum('total'), resolved = sum('resolvidos'), female = sum('expected_female');
  $('total').textContent = number(n);
  $('female').textContent = percent(resolved ? 100 * female / resolved : null);
  $('coverage').textContent = percent(n ? 100 * resolved / n : null);
  $('unknown').textContent = number(sum('nao_identificados'));
  $('resolved').textContent = `${number(resolved)} de ${number(n)} registros`;
  $('status').textContent = invalid ? 'O início do período deve ser anterior ou igual ao fim.' : !n ? 'Não há registros neste recorte.' : !resolved ? 'Sem inferência disponível neste recorte. Os totais documentais estão disponíveis; a composição por gênero ainda não pode ser estimada.' : `${number(resolved)} registros com inferência em ${number(n)} registros. Percentuais de gênero calculados sobre os resolvidos.`;
  $('rows').replaceChildren(...selected.map(r => {
    const tr = document.createElement('tr');
    [r.periodo, number(r.total), number(r.resolvidos), number(r.nao_identificados), r.resolvidos ? number(r.expected_female) : '—', r.resolvidos ? number(r.expected_male) : '—', percent(r.female_percent_resolved), percent(100*r.cobertura)].forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
    return tr;
  }));
  const type = $('chart-type').value;
  const titles = {counts:'Registros ao longo do tempo', bars:'Composição estimada por período', line:'Participação feminina ao longo do tempo', pie:'Composição estimada no recorte', coverage:'Cobertura da inferência por período'};
  $('chart-title').textContent = titles[type];
  const notes = {counts:'Contagens de registros nos documentos disponíveis. Períodos ausentes não representam zero.', bars:'Quantidades esperadas entre registros resolvidos. Valores fracionários são resultados do modelo.', line:'Percentual entre resolvidos. As barras verticais indicam os quantis de 2,5% e 97,5% do modelo; períodos sem inferência permanecem sem valor.', pie:'Proporções calculadas pela soma das quantidades esperadas no recorte. Registros sem inferência ficam fora da pizza.', coverage:'Percentual de registros com inferência disponível em relação ao total de cada período.'};
  $('chart-note').textContent = notes[type];
  if (!n) return emptyChart('Nenhum dado para o período selecionado.');
  if (!resolved && ['bars','line','pie'].includes(type)) return emptyChart('Composição indisponível: não há inferência de gênero neste recorte.');
  if (!window.Plotly) return emptyChart('A biblioteca de gráficos não carregou. A tabela e os downloads continuam disponíveis.');
  // Remover mensagens de estado antes de recriar o gráfico.
  if (!$('chart').classList.contains('js-plotly-plot')) $('chart').replaceChildren();
  const x = selected.map(r => r.periodo);
  let traces = [], ytitle = 'Registros';
  if (type === 'counts') traces = [{x, y:selected.map(r=>r.total), type:'bar', marker:{color:palette.total}, name:'Registros'}];
  if (type === 'bars') traces = ['female','male'].map((g,i) => ({x, y:selected.map(r=>r.resolvidos ? r[`expected_${g}`] : null), type:'bar', name:i ? 'Masculina (estimada)' : 'Feminina (estimada)', marker:{color:palette[g]}}));
  if (type === 'line') {
    ytitle = 'Participação feminina (%)';
    traces = [{x, y:selected.map(r=>r.female_percent_resolved), type:'scatter', mode:'lines+markers', connectgaps:false, name:'Feminina (estimada)', line:{color:palette.female}}];
    // Intervalos absolutos: não presumir que a expectativa está entre os quantis.
    selected.forEach(r => {if(r.resolvidos) traces.push({x:[r.periodo,r.periodo], y:[100*r.interval95_lower_resolved/r.resolvidos,100*r.interval95_upper_resolved/r.resolvidos], type:'scatter', mode:'lines+markers', line:{color:palette.female,width:2}, marker:{symbol:'line-ew',size:10}, name:'Intervalo probabilístico de 95%', showlegend:false, hovertemplate:'%{y:.2f}%<extra>Intervalo de 95%</extra>'});});
  }
  if (type === 'pie') traces = [{values:[female,resolved-female],labels:['Feminina (estimada)','Masculina (estimada)'],type:'pie',hole:.48,sort:false,marker:{colors:[palette.female,palette.male]},textinfo:'label+percent',textposition:'inside',hovertemplate:'%{label}<br>Quantidade esperada: %{value:.2f}<br>%{percent}<extra></extra>'}];
  if (type === 'coverage') {ytitle='Cobertura (%)';traces=[{x,y:selected.map(r=>100*r.cobertura),type:'bar',marker:{color:palette.total},name:'Cobertura'}];}
  const layout = {autosize:true,margin:{t:24,r:16,b:70,l:60},font:{family:'system-ui, sans-serif',color:'#202c35'},paper_bgcolor:'#fff',plot_bgcolor:'#fff',barmode:'group',legend:{orientation:'h',y:-.22},xaxis:{type:'category',title:{text:$('grain').value === 'ano' ? 'Ano' : 'Semestre'},gridcolor:'#edf0eb'},yaxis:{title:{text:ytitle},rangemode:'tozero',gridcolor:'#edf0eb'},separators:',.'};
  if (type === 'line' || type === 'coverage') layout.yaxis.range=[0,100];
  Plotly.react('chart', traces, layout, {responsive:true,displaylogo:false,toImageButtonOptions:{format:'png',filename:'elas-ti'},modeBarButtonsToRemove:['lasso2d','select2d']}).catch(()=>emptyChart('Não foi possível desenhar o gráfico. Os valores estão na tabela.'));
}
async function init() {
  try {
    const response = await fetch('data/resumo.json');
    if (!response.ok) throw new Error('data');
    const data = await response.json();
    if (data.schema_version !== 1 || !Array.isArray(data.rows)) throw new Error('schema');
    rows = data.rows;
    const courses = [...new Set(rows.map(r=>r.curso))].sort((a,b)=>a.localeCompare(b,'pt-BR'));
    options($('course'),courses,'Todos os cursos');
    $('updated').textContent = `Análise de ${new Date(data.analysis_at).toLocaleString('pt-BR')} · Fonte: documentos institucionais processados localmente`;
    ['course','kind','grain'].forEach(id=>$(id).addEventListener('change',updatePeriods));
    ['from','to','chart-type'].forEach(id=>$(id).addEventListener('change',render));
    updatePeriods();
  } catch {
    $('updated').textContent = 'Dados indisponíveis';
    $('status').textContent = 'Não foi possível carregar os dados. Para uma prévia local, a página deve ser aberta por um servidor HTTP.';
    emptyChart('Aguardando uma exportação válida.');
  }
}
init();
