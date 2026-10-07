'use strict';
const $ = id => document.getElementById(id);
const fragment = new URLSearchParams(location.hash.slice(1));
const token = fragment.get('token') || sessionStorage.getItem('auto-dd-token') || '';
if (token) sessionStorage.setItem('auto-dd-token', token);
history.replaceState(null, '', location.pathname);
let data = {version:1, source:'manual', tables:[]};
let view = 'catalog';
let editing = null;
let working = false;

function element(tag, text, cls) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function notice(text) { $('notice').textContent = text; }
async function api(path, body, raw=false) {
  const response = await fetch('/api/'+path, {
    method:body === undefined ? 'GET':'POST',
    headers:{'X-Auto-DD-Token':token, 'Content-Type':'application/json'},
    ...(body === undefined ? {} : {body:JSON.stringify(body)})
  });
  if (!response.ok) {
    const error = await response.json().catch(()=>({error:'요청을 처리하지 못했습니다.'}));
    throw new Error(error.error || '요청을 처리하지 못했습니다.');
  }
  return raw ? response.blob() : response.json();
}
async function run(action) {
  if (working) return;
  working = true;
  document.querySelectorAll('button').forEach(button=>button.disabled=true);
  try { await action(); }
  catch(error) { notice(error.message); }
  finally { working=false; document.querySelectorAll('button').forEach(button=>button.disabled=false); }
}
async function commit(candidate, message) {
  data = await api('validate', candidate);
  render();
  if (message) notice(message);
}
function stats() {
  const columns = data.tables.flatMap(t=>t.columns);
  $('table-count').textContent=data.tables.length;
  $('column-count').textContent=columns.length;
  $('relation-count').textContent=data.tables.reduce((n,t)=>n+(t.foreign_keys||[]).length,0);
  const total = columns.length+data.tables.length;
  const written = columns.filter(c=>c.description).length+data.tables.filter(t=>t.description).length;
  $('coverage').textContent=(total ? Math.round(written/total*100):0)+'%';
  const labels = {manual:'직접 작성', sample:'샘플 데이터', postgresql:'PostgreSQL', bigquery:'BigQuery'};
  $('source-label').textContent=labels[data.source] || '가져온 카탈로그';
}
function render() {
  stats();
  $('empty').hidden=data.tables.length>0;
  $('tables').replaceChildren();
  const query=$('search').value.toLowerCase();
  const selected=data.tables.filter(t=>JSON.stringify(t).toLowerCase().includes(query));
  for (const table of selected) {
    const card=element('article',undefined,'table-card');
    const head=element('div',undefined,'table-head');
    const title=element('div');
    const name=element('h2',table.name);
    name.append(element('span',table.columns.length+' columns','count'));
    title.append(name,element('div',table.schema,'schema'));
    const actions=element('div',undefined,'table-actions');
    const edit=element('button','편집'); edit.onclick=()=>openTable(table);
    const remove=element('button','삭제','danger');
    remove.onclick=()=>{
      if (!confirm(`${table.id} 테이블과 연결된 관계를 삭제할까요?`)) return;
      run(async()=>{
        const candidate=structuredClone(data);
        candidate.tables=candidate.tables.filter(t=>t.id!==table.id);
        candidate.tables.forEach(t=>t.foreign_keys=t.foreign_keys.filter(f=>f.target_table!==table.id));
        await commit(candidate,'테이블을 삭제했습니다.');
      });
    };
    actions.append(edit,remove); head.append(title,actions); card.append(head);
    if (table.description) card.append(element('p',table.description));
    const grid=element('table'); const thead=element('thead');const hrow=element('tr');
    ['컬럼','데이터 타입','NULL','키','기본값','설명'].forEach(x=>hrow.append(element('th',x)));
    thead.append(hrow);grid.append(thead);const tbody=element('tbody');
    for (const col of table.columns) {
      const row=element('tr');const key=element('td');
      if (col.primary_key) key.append(element('span','PK','pill'));
      if (table.foreign_keys.some(f=>f.columns.includes(col.name))) key.append(element('span',' FK','pill'));
      row.append(element('td',col.name),element('td',col.type,'mono'),element('td',col.nullable?'YES':'NO'),key,element('td',col.default||'—','mono'),element('td',col.description||'—'));
      tbody.append(row);
    }
    grid.append(tbody);card.append(grid);$('tables').append(card);
  }
  if (data.tables.length && !selected.length) $('tables').append(element('p','검색 결과가 없습니다.'));
  drawDiagram();
}
function switchView(next) {
  view=next;
  $('catalog-view').hidden=next!=='catalog';$('erd-view').hidden=next!=='erd';
  $('heading').textContent=next==='catalog'?'데이터 구조를 한눈에.':'데이터의 연결을 그려보세요.';
  $('lead').textContent=next==='catalog'?'데이터베이스를 연결하고, 명세와 관계도를 최신 상태로 관리하세요.':'테이블을 배치하고 관계를 연결해, 설계부터 명세까지 한곳에서.';
  $('view-name').textContent=next==='catalog'?'데이터 카탈로그':'ERD 스튜디오';
  document.querySelectorAll('[data-view]').forEach(b=>{
    b.classList.toggle('active',b.classList.contains('nav')&&b.dataset.view===next);
    b.classList.toggle('selected',!b.classList.contains('nav')&&b.dataset.view===next);
  });
  drawDiagram();
}
function positions() {
  const result={};let y=40;
  for(let start=0;start<data.tables.length;start+=3) {
    const row=data.tables.slice(start,start+3);
    row.forEach((t,i)=>result[t.id]=t.position || {x:40+i*360,y});
    y+=Math.max(...row.map(t=>72+t.columns.length*26))+80;
  }
  return result;
}
function edges(pos) {
  const svg=$('edges');svg.replaceChildren();
  const make=(tag,attrs)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));return el;};
  const defs=make('defs',{});const marker=make('marker',{id:'arrow',markerWidth:10,markerHeight:10,refX:9,refY:3,orient:'auto'});marker.append(make('path',{d:'M0,0 L0,6 L9,3 z',fill:'#587bdf'}));defs.append(marker);svg.append(defs);
  for(const table of data.tables) for(const fk of table.foreign_keys) {
    const p=pos[table.id],q=pos[fk.target_table]; if(!q) continue;
    const path=table.id===fk.target_table?`M${p.x+300},${p.y+20} C${p.x+350},${p.y-40} ${p.x+350},${p.y+70} ${p.x+300},${p.y+55}`:`M${p.x+300},${p.y+20} L${q.x},${q.y+20}`;
    const line=make('path',{d:path,stroke:'#587bdf','stroke-width':2,fill:'none','marker-end':'url(#arrow)'});
    const title=make('title',{});title.textContent=fk.name+': '+fk.columns.join(', ')+' → '+fk.target_columns.join(', ');line.append(title);svg.append(line);
  }
  const width=Math.max(1100,...Object.values(pos).map(p=>p.x+380));
  const height=Math.max(500,...data.tables.map(t=>pos[t.id].y+100+t.columns.length*26));
  svg.setAttribute('width',width);svg.setAttribute('height',height);
  $('diagram').style.width=width+'px';$('diagram').style.height=height+'px';
}
function drawDiagram() {
  const pos=positions();$('nodes').replaceChildren();$('relations').replaceChildren();
  for(const table of data.tables) {
    const node=element('div',undefined,'erd-node');const p=pos[table.id];
    node.style.left=p.x+'px';node.style.top=p.y+'px';
    const head=element('div',undefined,'node-head');head.tabIndex=0;head.setAttribute('role','button');head.setAttribute('aria-label',table.name+' 위치 이동: 방향키, 편집: Enter');
    head.append(element('strong',table.name),element('small',table.schema));
    head.ondblclick=()=>openTable(table);
    head.onkeydown=e=>{
      if(e.key==='Enter'){openTable(table);return;}
      const step={ArrowLeft:[-20,0],ArrowRight:[20,0],ArrowUp:[0,-20],ArrowDown:[0,20]}[e.key];
      if(!step)return;e.preventDefault();p.x=Math.max(0,p.x+step[0]);p.y=Math.max(0,p.y+step[1]);table.position={...p};node.style.left=p.x+'px';node.style.top=p.y+'px';edges(pos);
    };
    head.onpointerdown=e=>{
      if(e.button!==0 || working)return;
      const sx=e.clientX,sy=e.clientY,ox=p.x,oy=p.y;
      head.setPointerCapture(e.pointerId);
      head.onpointermove=move=>{
        p.x=Math.min(100000,Math.max(0,ox+move.clientX-sx));p.y=Math.min(100000,Math.max(0,oy+move.clientY-sy));
        table.position={...p};node.style.left=p.x+'px';node.style.top=p.y+'px';edges(pos);
      };
      const stop=()=>{head.onpointermove=null;head.onpointerup=null;head.onpointercancel=null;};
      head.onpointerup=stop;head.onpointercancel=stop;
    };
    node.append(head);
    for(const col of table.columns) {
      const line=element('div',undefined,'node-col');
      line.append(element('span',(col.primary_key?'◆ ':'')+col.name),element('em',col.type));node.append(line);
    }
    $('nodes').append(node);
    for(const fk of table.foreign_keys) {
      const row=element('div',undefined,'relation-row');
      row.append(element('span',`${table.name} (${fk.columns.join(', ')}) → ${fk.target_table} (${fk.target_columns.join(', ')}) · ${fk.name}${pos[fk.target_table]?'':' · 대상 테이블 미포함'}`));
      const remove=element('button','삭제');remove.onclick=()=>run(async()=>{
        const candidate=structuredClone(data);const t=candidate.tables.find(t=>t.id===table.id);
        t.foreign_keys.splice(table.foreign_keys.indexOf(fk),1);await commit(candidate,'관계를 삭제했습니다.');
      });row.append(remove);$('relations').append(row);
    }
  }
  if(!data.tables.length)$('relations').append(element('p','+ 테이블 버튼으로 첫 번째 테이블을 추가하세요.'));
  edges(pos);
}
function addColumn(col={name:'',type:'text',nullable:true,primary_key:false,description:'',default:null}) {
  const row=element('div',undefined,'column-edit');
  const fields=element('div',undefined,'row');
  const name=element('input');name.value=col.name;name.placeholder='컬럼 이름';name.required=true;name.dataset.field='name';name.setAttribute('aria-label','컬럼 이름');
  const type=element('input');type.value=col.type;type.placeholder='데이터 타입';type.required=true;type.dataset.field='type';type.setAttribute('aria-label','데이터 타입');
  const remove=element('button','×');remove.type='button';remove.setAttribute('aria-label','컬럼 삭제');remove.onclick=()=>row.remove();fields.append(name,type,remove);row.append(fields);
  for(const [key,label] of [['nullable','NULL 허용'],['primary_key','기본키 (PK)']]){
    const l=element('label');const checkbox=element('input');checkbox.type='checkbox';checkbox.dataset.field=key;checkbox.checked=col[key];l.append(checkbox,document.createTextNode(label));row.append(l);
  }
  const def=element('input');def.className='default-field';def.dataset.field='default';def.value=col.default??'';def.placeholder='기본값 (선택)';def.setAttribute('aria-label','컬럼 기본값');row.append(def);
  const description=element('textarea');description.value=col.description||'';description.placeholder='컬럼 설명';description.dataset.field='description';description.setAttribute('aria-label','컬럼 설명');row.append(description);$('column-editor').append(row);
}
function openTable(table=null) {
  editing=table?.id||null;$('table-title').textContent=table?'테이블 편집':'테이블 만들기';
  $('edit-schema').value=table?.schema||'public';$('edit-name').value=table?.name||'';$('edit-description').value=table?.description||'';
  $('column-editor').replaceChildren();(table?.columns||[{name:'id',type:'bigint',nullable:false,primary_key:true,description:''}]).forEach(addColumn);
  $('table-dialog').showModal();
}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>b.closest('dialog').close());
$('search').oninput=render;
$('connect').onclick=()=>$('connect-dialog').showModal();
$('db-source').onchange=()=>{$('pg-fields').hidden=$('db-source').value!=='postgresql';$('bq-fields').hidden=$('db-source').value!=='bigquery';};
$('connection-form').onsubmit=e=>{e.preventDefault();run(async()=>{
  notice('메타데이터를 가져오는 중입니다…');
  const body={source:$('db-source').value,dsn:$('dsn').value,schemas:$('schemas').value.split(',').map(s=>s.trim()).filter(Boolean),project:$('project').value.trim(),dataset:$('dataset').value.trim()};
  try {data=await api('extract',body);$('connect-dialog').close();render();notice('메타데이터를 가져왔습니다. 편집 내용은 DB에 반영되지 않습니다.');}
  finally {$('dsn').value='';body.dsn='';}
});};
const sample=()=>run(async()=>{data=await api('sample');render();notice('샘플 카탈로그입니다. 실제 DB에 연결하지 않았습니다.');});
$('sample').onclick=sample;$('empty-sample').onclick=sample;
$('import').onclick=()=>$('file').click();
$('file').onchange=()=>run(async()=>{
  const file=$('file').files[0];if(!file)return;
  try {if(file.size>16*1024*1024)throw new Error('최대 16MB 파일을 지원합니다.');await commit(JSON.parse(await file.text()),'JSON 카탈로그를 가져왔습니다.');}
  finally {$('file').value='';}
});
$('export').onclick=()=>run(async()=>{
  if(!data.tables.length)throw new Error('먼저 테이블을 추가하세요.');
  const kind=$('format').value;const blob=await api('export/'+kind,data,true);const url=URL.createObjectURL(blob);
  const a=element('a');a.href=url;a.download='auto-dd.'+kind;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice('파일을 내보냈습니다. JSON으로 저장하면 ERD 배치와 편집 내용을 다시 열 수 있습니다.');
});
$('new-table').onclick=()=>openTable();$('new-column').onclick=()=>addColumn();
$('table-form').onsubmit=e=>{e.preventDefault();run(async()=>{
  const candidate=structuredClone(data);const id=$('edit-schema').value.trim()+'.'+$('edit-name').value.trim();
  const columns=Array.from($('column-editor').children).map(row=>{
    const c={};row.querySelectorAll('[data-field]').forEach(input=>c[input.dataset.field]=input.type==='checkbox'?input.checked:input.value);
    c.default=c.default||null;return c;
  });
  const original=candidate.tables.find(t=>t.id===editing);
  const preservedId=original&&original.schema===$('edit-schema').value.trim()&&original.name===$('edit-name').value.trim()?original.id:id;
  if(candidate.tables.some(t=>t.id===preservedId&&t.id!==editing))throw new Error('같은 테이블 이름이 이미 있습니다.');
  const table={...(original||{}),id:preservedId,schema:$('edit-schema').value.trim(),name:$('edit-name').value.trim(),description:$('edit-description').value,columns,foreign_keys:original?.foreign_keys||[]};
  if(original){candidate.tables[candidate.tables.indexOf(original)]=table;candidate.tables.forEach(t=>t.foreign_keys.forEach(f=>{if(f.target_table===editing)f.target_table=preservedId;}));}
  else candidate.tables.push(table);
  await commit(candidate,'테이블을 저장했습니다. 파일로 내보내면 편집 내용을 보관할 수 있습니다.');$('table-dialog').close();
});};
$('auto-layout').onclick=()=>{data.tables.forEach(t=>delete t.position);drawDiagram();notice('테이블을 자동 배치했습니다.');};
$('add-relation').onclick=()=>{
  if(!data.tables.length){notice('먼저 테이블을 추가하세요.');return;}
  for(const id of ['fk-source','fk-target']){
    $(id).replaceChildren();data.tables.forEach(t=>{const o=element('option',t.id);o.value=t.id;$(id).append(o);});
  }
  $('relation-dialog').showModal();
};
$('relation-form').onsubmit=e=>{e.preventDefault();run(async()=>{
  const candidate=structuredClone(data);const table=candidate.tables.find(t=>t.id===$('fk-source').value);
  if(table.foreign_keys.some(f=>f.name===$('fk-name').value.trim()))throw new Error('같은 외래키 이름이 이미 있습니다.');
  table.foreign_keys.push({name:$('fk-name').value.trim(),columns:$('fk-columns').value.split(',').map(s=>s.trim()),target_table:$('fk-target').value,target_columns:$('fk-target-columns').value.split(',').map(s=>s.trim())});
  await commit(candidate,'관계를 저장했습니다.');$('relation-dialog').close();
});};
$('ai-open').onclick=()=>$('ai-dialog').showModal();
$('ai-form').onsubmit=e=>{e.preventDefault();run(async()=>{
  if(!data.tables.length)throw new Error('먼저 카탈로그를 열어주세요.');
  notice('로컬 모델에서 설명을 생성 중입니다. 테이블 수와 모델에 따라 시간이 걸립니다…');
  data=await api('ai',{catalog:data,model:$('ai-model').value});render();$('ai-dialog').close();notice('AI 제안을 채웠습니다. 정확성을 검토하고 JSON으로 저장하세요.');
});};
window.addEventListener('beforeunload',e=>{if(data.tables.length){e.preventDefault();e.returnValue='';}});
render();
if(!token)notice('인증된 앱 실행 주소가 필요합니다. Auto-DD 실행 시 출력된 주소를 사용하세요.');
