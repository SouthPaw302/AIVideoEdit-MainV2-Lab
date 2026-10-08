const $ = id => document.getElementById(id);
let currentAssetId = null;
let assetsCache = [];
let systemState = null;
let coreState = null;
let productionState = null;
let approachState = null;

async function api(url, options) {
  const res = await fetch(url, options);
  let body = null;
  try { body = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error(body?.error || `${res.status} ${res.statusText}`);
  return body;
}
async function toolCall(name, arguments_ = {}) {
  const d = await api('/api/tools/call', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, arguments: arguments_})
  });
  return d.result;
}
const esc = v => String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const projectId = () => $('project').value || 'prototype';

function formatBytes(n){ n=Number(n); if(!Number.isFinite(n))return '—'; const u=['B','KB','MB','GB','TB']; let i=0; while(n>=1024&&i<u.length-1){n/=1024;i++;} return `${n.toFixed(i?1:0)} ${u[i]}`; }
function formatDuration(n){ n=Number(n); if(!Number.isFinite(n))return '—'; const m=Math.floor(n/60),s=Math.round(n%60); return `${m}:${String(s).padStart(2,'0')}`; }
function formatTime(ts){ return ts?new Date(ts*1000).toLocaleTimeString():'—'; }
function friendlyJob(type){ return ({analyze_media:'Reading media',make_proxy:'Making preview copy',extract_review_frames:'Creating review snapshots',qc_media:'Checking media',ffmpeg_check:'Testing video engine',sync_project:'Backing up project',analyze_production:'Analyzing references & music'})[type] || type.replaceAll('_',' '); }
function friendlyStatus(status){ return ({complete:'Done',failed:'Needs attention',running:'Working',queued:'Waiting',interrupted:'Stopped'})[status] || status; }
function friendlyStage(stage){ return ({INITIALIZED:'Project started',SOURCE_INGESTED:'Source media added',REFERENCES_ANALYZED:'Media analyzed',APPROACH_ESTABLISHED:'Creative approach set',STORYBOARD_LOCKED:'Storyboard locked',SHOT_PACKAGES_BUILT:'Shots prepared',SHOT_PROOFS_ACCEPTED:'Shot proofs accepted',FX_LOCKED:'Effects locked',ASSEMBLED:'Video assembled',FINAL_QC_PASSED:'Final check passed',ARCHIVED:'Archived'})[stage] || String(stage||'').replaceAll('_',' ').toLowerCase(); }

async function loadHealth(){ try{await api('/api/health');$('health').textContent='Ready';$('health').classList.add('online');}catch(_){$('health').textContent='Offline';$('health').classList.remove('online');} }
async function loadCapabilities(){ const d=await api('/api/capabilities'); const caps=d.capabilities.map(c=>c.name==='Python'&&!c.available?{...c,available:true,detail:'Running this app'}:c); $('capabilities').innerHTML=caps.map(c=>`<div class="cap"><span class="dot ${c.available?'ok':'bad'}"></span><div><strong>${esc(c.name)}</strong><small>${esc(c.available?'Ready':c.detail)}</small></div></div>`).join(''); }

async function loadCoreStatus(){
  try{
    coreState=await api('/api/core');
    if(coreState.bootstrapped){ $('coreStatus').textContent='Current-main production engine loaded and attested.'; $('coreDetails').textContent=`main ${String(coreState.main_commit||'').slice(0,12)} · ${coreState.capability_count||0} media capabilities · ${coreState.fx_count||0} reusable FX · guard ${coreState.guard_result||'unknown'}`; $('loadCore').textContent='Refresh current core'; }
    else{ $('coreStatus').textContent='Canonical production engine is not loaded yet.'; $('coreDetails').textContent='Load it to use the production contracts, capability matrix and reusable FX from current main.'; $('loadCore').textContent='Load current core'; }
  }catch(_){ coreState=null; $('coreStatus').textContent='Start the full stack to use the canonical production engine.'; $('coreDetails').textContent=''; }
  updateProductionButtons();
}
async function bootstrapCore(){
  $('loadCore').disabled=true; $('coreStatus').textContent='Loading and verifying current main…'; $('coreDetails').textContent='This can take a moment the first time.';
  try{ const d=await api('/api/core/bootstrap',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}); coreState=d; $('uploadMessage').textContent=d.bootstrapped?'Production engine loaded.':'Production engine could not be loaded.'; }
  catch(e){ $('coreStatus').textContent='Production engine needs attention.'; $('coreDetails').textContent=e.message; }
  finally{ $('loadCore').disabled=false; await Promise.allSettled([loadCoreStatus(),loadSystem(),loadProductionStatus()]); }
}

function updateProductionButtons(){
  const initialized=!!productionState?.initialized;
  const analysisStage=['SOURCE_INGESTED','REFERENCES_ANALYZED'].includes(productionState?.stage);
  const approachStage=['REFERENCES_ANALYZED','APPROACH_ESTABLISHED'].includes(productionState?.stage);
  $('startProjectEngine').hidden=initialized;
  $('verifyProjectEngine').hidden=!initialized;
  $('syncProductionAssets').hidden=!initialized;
  $('analyzeProduction').hidden=!initialized||!analysisStage;
  $('songContext').hidden=!initialized||!analysisStage;
  $('setApproach').hidden=!initialized||!approachStage;
  $('setRoutes').hidden=!initialized||!approachStage||!approachState?.route_gate_required;
  $('selectRoute').hidden=!initialized||!approachStage||!(approachState?.route_options||[]).length;
  $('advanceProduction').hidden=!initialized||!productionState?.next_stage;
  $('startProjectEngine').disabled=!coreState?.bootstrapped;
  if(productionState?.next_stage) $('advanceProduction').textContent=`Continue: ${friendlyStage(productionState.next_stage)}`;
}
async function loadApproachStatus(){
  if(!productionState?.initialized || !['REFERENCES_ANALYZED','APPROACH_ESTABLISHED'].includes(productionState.stage)){ approachState=null; $('approachStatus').hidden=true; updateProductionButtons(); return; }
  try{
    approachState=await toolCall('approach.status',{project_id:projectId()});
    const selected=(approachState.selected_capabilities||[]).length;
    const route=approachState.route_gate_required?(approachState.route_locked?'visual route locked':`${(approachState.route_options||[]).length} visual routes recorded`):'visual reference supplies direction';
    $('approachStatus').hidden=false;
    $('approachStatus').textContent=`Creative approach: ${selected} capabilities selected · ${route}.`;
  }catch(e){ approachState=null; $('approachStatus').hidden=false; $('approachStatus').textContent=e.message; }
  updateProductionButtons();
}
async function loadProductionStatus(){
  if(!$('project').value)return;
  try{
    productionState=await toolCall('production.status',{project_id:projectId()});
    if(!productionState.initialized) $('productionStatus').textContent=coreState?.bootstrapped?'This project is not connected to the production engine yet.':'Load the canonical core first, then start the project engine.';
    else{
      const media=productionState.workstation_asset_sync_complete?` · ${productionState.workstation_ready_asset_count}/${productionState.workstation_asset_count} media synced`:' · media not synced';
      const verify=productionState.guard_pass?'verified':'needs verification';
      $('productionStatus').textContent=`${friendlyStage(productionState.stage||'INITIALIZED')} · ${verify}${media}${productionState.next_stage?` · next: ${friendlyStage(productionState.next_stage)}`:''}.`;
    }
  }catch(e){ productionState=null; $('productionStatus').textContent=e.message; }
  await loadApproachStatus();
  updateProductionButtons();
}

async function startProjectEngine(){ $('startProjectEngine').disabled=true; $('productionStatus').textContent='Creating an isolated production workspace and verifying it…'; try{ if(!coreState?.bootstrapped)await bootstrapCore(); if(!coreState?.bootstrapped)throw new Error('Canonical core is not loaded.'); productionState=await toolCall('production.initialize',{project_id:projectId()}); }catch(e){$('productionStatus').textContent=e.message;}finally{$('startProjectEngine').disabled=false;await loadProductionStatus();} }
async function syncProductionAssets(){ $('syncProductionAssets').disabled=true; $('productionStatus').textContent='Syncing workstation media into the canonical project manifests…'; try{ productionState=await toolCall('production.sync_assets',{project_id:projectId()}); $('productionStatus').textContent=`Synced ${productionState.asset_count||0} media items to the production engine.`; }catch(e){$('productionStatus').textContent=e.message;}finally{$('syncProductionAssets').disabled=false;await loadProductionStatus();} }
async function analyzeProduction(){ $('analyzeProduction').disabled=true; $('productionStatus').textContent='Queueing full reference coverage and music signal analysis…'; try{ const result=await toolCall('production.analyze',{project_id:projectId()}); $('productionStatus').textContent=`Analysis queued as ${result.job?.id||'background job'}. Long references may take a while.`; await loadJobs(); }catch(e){$('productionStatus').textContent=e.message;}finally{$('analyzeProduction').disabled=false;} }

async function saveSongContext(){
  const genre=$('songGenre').value.trim(),lyricsStatus=$('lyricsStatus').value,lyricsText=$('lyricsText').value.trim();
  if(!genre){$('productionStatus').textContent='Enter the genre before saving song context.';return false;}
  if(lyricsStatus==='present'&&!lyricsText){$('productionStatus').textContent='Paste the verified lyrics when lyrics are present.';return false;}
  $('saveSongContext').disabled=true;
  try{await toolCall('production.set_music_context',{project_id:projectId(),genre,lyrics_status:lyricsStatus,lyrics_text:lyricsText,directing_use:'default'});$('productionStatus').textContent='Song context recorded as explicit production authority.';return true;}
  catch(e){$('productionStatus').textContent=e.message;return false;}
  finally{$('saveSongContext').disabled=false;await loadProductionStatus();}
}

async function openApproachDialog(){
  try{
    const [caps,status]=await Promise.all([toolCall('capabilities.list'),toolCall('approach.status',{project_id:projectId()})]);
    const selected=new Set(status.selected_capabilities||[]);
    $('approachCapabilities').innerHTML=(caps.capabilities||[]).map(c=>`<label><input type="checkbox" data-capability="${esc(c.id)}" ${selected.has(c.id)?'checked':''}> <strong>${esc(c.id)}</strong><small>${esc(c.kind||'')} · ${esc(c.requires||'')}</small></label>`).join('');
    $('approachSummary').value=status.approach_summary||'';
    $('approachDialog').showModal();
  }catch(e){$('productionStatus').textContent=e.message;}
}
async function saveApproach(){
  const capabilities=[...document.querySelectorAll('[data-capability]:checked')].map(x=>x.dataset.capability);
  const approachSummary=$('approachSummary').value.trim();
  if(!capabilities.length||!approachSummary){$('productionStatus').textContent='Choose at least one capability and describe the creative approach.';return false;}
  $('saveApproach').disabled=true;
  try{ approachState=await toolCall('approach.set_capabilities',{project_id:projectId(),capabilities,approach_summary:approachSummary}); $('productionStatus').textContent=approachState.route_gate_required?'Approach saved. Three visual routes are required because no visual reference was supplied.':'Creative approach saved from the supplied visual reference.'; return true; }
  catch(e){$('productionStatus').textContent=e.message;return false;}
  finally{$('saveApproach').disabled=false;await loadApproachStatus();}
}

function routeForm(number,existing={}){
  const beats=existing.storyboard||[];
  return `<fieldset data-route="${number}"><legend>Route ${number}</legend><label>Name<input data-route-name value="${esc(existing.name||'')}"></label><label>Story approach<textarea data-route-story rows="3">${esc(existing.story_approach||'')}</textarea></label><label>Rendering/media treatment<textarea data-route-render rows="3">${esc(existing.rendering_route||'')}</textarea></label>${[1,2,3].map((n,i)=>`<label>Beat ${n}<input data-route-beat="${n}" value="${esc(beats[i]?.description||'')}"></label>`).join('')}</fieldset>`;
}
async function openRoutesDialog(){
  try{ const status=await toolCall('approach.status',{project_id:projectId()}); const existing=status.route_options||[]; $('routeForms').innerHTML=[1,2,3].map((n,i)=>routeForm(n,existing[i]||{})).join(''); $('routesDialog').showModal(); }
  catch(e){$('productionStatus').textContent=e.message;}
}
async function saveRoutes(){
  const routes=[...document.querySelectorAll('[data-route]')].map(fs=>({number:Number(fs.dataset.route),name:fs.querySelector('[data-route-name]').value.trim(),story_approach:fs.querySelector('[data-route-story]').value.trim(),rendering_route:fs.querySelector('[data-route-render]').value.trim(),storyboard:[...fs.querySelectorAll('[data-route-beat]')].map(b=>({number:Number(b.dataset.routeBeat),description:b.value.trim()}))}));
  if(routes.some(r=>!r.name||!r.story_approach||!r.rendering_route||r.storyboard.some(b=>!b.description))){$('productionStatus').textContent='Complete all three routes and all three beats for each route.';return false;}
  $('saveRoutes').disabled=true;
  try{ approachState=await toolCall('approach.set_routes',{project_id:projectId(),routes}); $('productionStatus').textContent='Three visual directions recorded. Choose one or create a hybrid before continuing.'; return true; }
  catch(e){$('productionStatus').textContent=e.message;return false;}
  finally{$('saveRoutes').disabled=false;await loadApproachStatus();}
}
async function openRouteSelection(){
  try{ const status=await toolCall('approach.status',{project_id:projectId()}); approachState=status; $('routeChoices').innerHTML=(status.route_options||[]).map(r=>`<label><input type="checkbox" data-route-choice="${Number(r.number)}"> <strong>${esc(r.number)}. ${esc(r.name)}</strong><small>${esc(r.story_approach)} · ${esc(r.rendering_route)}</small></label>`).join(''); $('routeInstruction').value=status.route_selection?.recorded_user_instruction||''; $('routeSelectionDialog').showModal(); }
  catch(e){$('productionStatus').textContent=e.message;}
}
async function saveRouteSelection(){
  const numbers=[...document.querySelectorAll('[data-route-choice]:checked')].map(x=>Number(x.dataset.routeChoice));
  const instruction=$('routeInstruction').value.trim();
  if(!numbers.length||!instruction){$('productionStatus').textContent='Choose at least one route and record the user instruction.';return false;}
  $('saveRouteSelection').disabled=true;
  try{ approachState=await toolCall('approach.select_route',{project_id:projectId(),selected_option_numbers:numbers,recorded_user_instruction:instruction,status:numbers.length>1?'hybrid':'selected'}); $('productionStatus').textContent='Visual direction locked as explicit current-user production authority.'; return true; }
  catch(e){$('productionStatus').textContent=e.message;return false;}
  finally{$('saveRouteSelection').disabled=false;await loadApproachStatus();}
}

async function advanceProduction(){
  if(!productionState?.next_stage)return;
  const target=productionState.next_stage; $('advanceProduction').disabled=true; $('productionStatus').textContent=`Checking whether the project can continue to ${friendlyStage(target)}…`;
  try{ const result=await toolCall('production.advance',{project_id:projectId(),target_stage:target}); productionState=result; $('productionStatus').textContent=result.advanced?`Continued to ${friendlyStage(result.stage)}. Canonical guard PASS.`:`Could not continue. ${result.guard_stderr||result.error||'Required production evidence is still missing.'}`; }
  catch(e){$('productionStatus').textContent=e.message;}
  finally{$('advanceProduction').disabled=false;await loadProductionStatus();}
}
async function verifyProjectEngine(){ $('verifyProjectEngine').disabled=true; $('productionStatus').textContent='Running the canonical production guard…'; try{ productionState=await toolCall('production.guard',{project_id:projectId()}); $('productionStatus').textContent=productionState.guard_pass?`Verified · ${friendlyStage(productionState.stage||'INITIALIZED')} · guard PASS.`:`Verification failed. ${productionState.stderr||'Project state needs attention.'}`; }catch(e){$('productionStatus').textContent=e.message;}finally{$('verifyProjectEngine').disabled=false;await loadProductionStatus();} }

async function loadSystem(){
  try{
    systemState=await api('/api/system');
    const s=systemState,coreLabel=s.core?.bootstrapped?'core loaded':'core not loaded',h=s.harness||{};
    $('systemStats').textContent=`${s.workers} workers · ${s.queue_depth} waiting · ${formatBytes(s.disk?.free)} free · storage: ${s.storage?.mode||'local'} · ${coreLabel} · ${s.tool_count||0} agent tools`;
    $('syncProject').hidden=!s.storage?.configured;
    if($('harnessStatus')){
      const launch=h.dsh_installed?'dsh installed':h.npx_available?'npx available':'launcher not detected';
      $('harnessStatus').textContent=h.bridge_ready?`MCP bridge ready · ${launch}`:'Harness bridge unavailable';
      $('harnessDetails').textContent=`${h.bridge||'mcp-stdio'} · canonical guards stay authoritative · main writes disabled`;
    }
  }catch(_){
    systemState=null;
    $('systemStats').textContent='Run stack.py or the platform launcher to enable queued workers and storage telemetry.';
    $('syncProject').hidden=true;
    if($('harnessStatus'))$('harnessStatus').textContent='Start the full stack to inspect the harness bridge.';
    if($('harnessDetails'))$('harnessDetails').textContent='';
  }
}
async function loadProjects(selectId){ const d=await api('/api/projects'); $('project').innerHTML=d.projects.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join(''); if(selectId&&d.projects.some(p=>p.id===selectId))$('project').value=selectId; }
function updateNextAction(){ const title=$('nextActionTitle'),text=$('nextActionText'),button=$('nextActionButton');button.hidden=true;button.onclick=null;if(!assetsCache.length){title.textContent='Add your first media file';text.textContent='Choose a video, song, or image above, then click “Add to project”.';return;}const a=assetsCache.find(x=>x.id===currentAssetId)||assetsCache[0];if(!currentAssetId){title.textContent='Choose a file from Your media';text.textContent='Pick the video or audio you want to work on next, or prepare the whole project at once.';return;}if(a.status==='analyzing'||a.status==='uploaded'){title.textContent='Reading your media…';text.textContent='The app is checking the file and preparing its basic information.';return;}if(a.status==='failed'){title.textContent='This file needs attention';text.textContent=a.error||'The app could not prepare this media.';return;}if(!a.proxy_url&&a.metadata?.video_codec){title.textContent='Make a smooth preview copy';text.textContent='This creates a smaller version that is easier to play while you work.';button.textContent='Make preview copy';button.hidden=false;button.onclick=()=>operation('make_proxy');return;}if(!(a.review_frames||[]).length&&a.metadata?.video_codec){title.textContent='Create review snapshots';text.textContent='Generate six frames across the video so you can quickly inspect the whole piece.';button.textContent='Create snapshots';button.hidden=false;button.onclick=()=>operation('extract_review_frames');return;}if(a.qc?.status!=='pass'){title.textContent='Check the media';text.textContent='Verify that the file can be decoded cleanly before you continue editing.';button.textContent='Check media';button.hidden=false;button.onclick=()=>operation('qc_media');return;}title.textContent='This media is ready';text.textContent='Preview copy, review snapshots, and media check are complete.'; }
async function loadAssets(){ const d=await api(`/api/assets?project=${encodeURIComponent(projectId())}`);assetsCache=d.assets;if(!d.assets.length){$('assets').innerHTML='<div class="empty-list"><strong>No media yet</strong><small>Add a file above to get started.</small></div>';currentAssetId=null;showInspector(null);updateNextAction();return;}$('assets').innerHTML=d.assets.map(a=>{const m=a.metadata||{},selected=a.id===currentAssetId?' selected':'',thumb=a.thumbnail_url?`<img src="${esc(a.thumbnail_url)}" alt="">`:`<div class="mini-placeholder">${esc(a.status==='ready'?'media':a.status)}</div>`,qc=a.qc?.status||'unchecked',label=qc==='pass'?'checked':qc==='fail'?'issue':'';return `<button class="asset-row${selected}" data-asset="${esc(a.id)}">${thumb}<span><strong>${esc(a.filename)}</strong><small>${esc([m.width&&m.height?`${m.width}×${m.height}`:'',formatDuration(m.duration_seconds),formatBytes(a.size_bytes)].filter(Boolean).join(' · '))}</small></span><em class="mini-qc ${esc(qc)}">${esc(label)}</em></button>`;}).join('');document.querySelectorAll('[data-asset]').forEach(el=>el.addEventListener('click',()=>selectAsset(el.dataset.asset)));if(currentAssetId){const a=d.assets.find(x=>x.id===currentAssetId);showInspector(a||null);}updateNextAction(); }
function selectAsset(id){currentAssetId=id;const a=assetsCache.find(x=>x.id===id);showInspector(a);loadAssets();}
function showInspector(a){$('emptyInspector').hidden=!!a;$('assetInspector').hidden=!a;if(!a)return;const m=a.metadata||{};$('assetTitle').textContent=a.filename;$('assetSubtitle').textContent=`${formatBytes(a.size_bytes)} · ${a.status==='ready'?'Ready to work with':a.status}`;const qc=a.qc?.status||'unchecked';$('qcBadge').textContent=qc==='pass'?'CHECKED':qc==='fail'?'CHECK FAILED':'NOT CHECKED';$('qcBadge').className=`pill ${qc}`;const url=a.proxy_url||a.source_url;if(url&&m.video_codec)$('preview').innerHTML=`<video controls preload="metadata" poster="${esc(a.thumbnail_url||'')}"><source src="${esc(url)}"></video>`;else if(url&&m.audio_codec)$('preview').innerHTML=`<audio controls src="${esc(url)}"></audio>`;else if(a.thumbnail_url)$('preview').innerHTML=`<img src="${esc(a.thumbnail_url)}" alt="Preview">`;else $('preview').innerHTML='<div class="preview-placeholder">Preparing preview…</div>';const rows=[['Length',formatDuration(m.duration_seconds)],['Video',m.video_codec||'—'],['Size',m.width&&m.height?`${m.width} × ${m.height}`:'—'],['Frame rate',m.fps||'—'],['Audio',m.audio_codec||'—'],['File size',formatBytes(a.size_bytes)],['Preview copy',a.proxy_url?'Ready':'Not made yet'],['Media check',qc==='pass'?'Passed':qc==='fail'?'Failed':'Not checked']];$('metadata').innerHTML=rows.map(([k,v])=>`<div><small>${esc(k)}</small><strong>${esc(v)}</strong></div>`).join('');$('reviewFrames').innerHTML=(a.review_frames||[]).map(u=>`<img src="${esc(u)}" alt="Review snapshot">`).join('');}
async function loadJobs(){const d=await api(`/api/jobs?project=${encodeURIComponent(projectId())}`);if(!d.jobs.length){$('jobs').innerHTML='<p class="muted">No background work yet.</p>';return;}$('jobs').innerHTML=d.jobs.slice(0,20).map(j=>`<div class="job"><div><strong>${esc(friendlyJob(j.type))}</strong><small>${formatTime(j.created_at)}</small></div><span class="job-state ${esc(j.status)}">${esc(friendlyStatus(j.status))}</span><div class="progress"><i style="width:${Number(j.progress||0)}%"></i></div><small class="job-result">${esc(j.result||'Working…')}</small></div>`).join('');}
async function uploadMedia(){const file=$('mediaFile').files[0];if(!file){$('uploadMessage').textContent='Choose a file first.';return;}$('upload').disabled=true;$('uploadMessage').textContent=`Adding ${file.name}…`;try{const d=await api(`/api/assets?filename=${encodeURIComponent(file.name)}&project=${encodeURIComponent(projectId())}`,{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream'},body:file});currentAssetId=d.asset.id;$('uploadMessage').textContent='Added. Preparing media…';await refreshAll();}catch(e){$('uploadMessage').textContent=e.message;}finally{$('upload').disabled=false;}}
async function operation(type){if(!currentAssetId)return;try{await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type,project:projectId(),asset_id:currentAssetId})});await loadJobs();updateNextAction();}catch(e){$('uploadMessage').textContent=e.message;}}
async function prepareProject(){$('prepareProject').disabled=true;$('uploadMessage').textContent='Preparing everything that still needs work…';try{const d=await api(`/api/projects/${encodeURIComponent(projectId())}/prepare`,{method:'POST'});$('uploadMessage').textContent=d.count?`${d.count} background tasks added.`:'Everything is already prepared.';await loadJobs();}catch(e){$('uploadMessage').textContent=e.message;}finally{$('prepareProject').disabled=false;}}
async function syncProject(){$('syncProject').disabled=true;$('uploadMessage').textContent='Starting project backup…';try{await api(`/api/projects/${encodeURIComponent(projectId())}/sync`,{method:'POST'});$('uploadMessage').textContent='Backup queued.';await loadJobs();}catch(e){$('uploadMessage').textContent=e.message;}finally{$('syncProject').disabled=false;}}
async function deleteAsset(){if(!currentAssetId||!confirm('Remove this media and its local preview files from this project?'))return;await api(`/api/assets/${encodeURIComponent(currentAssetId)}`,{method:'DELETE'});currentAssetId=null;await refreshAll();}
async function createProject(){const name=$('newProjectName').value.trim();if(!name)return;const d=await api('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});await loadProjects(d.project.id);$('newProjectName').value='';productionState=null;approachState=null;await refreshAll();}
async function refreshAll(){await Promise.allSettled([loadAssets(),loadJobs(),loadSystem(),loadCoreStatus(),loadProductionStatus()]);}

$('upload').addEventListener('click',uploadMedia);
$('project').addEventListener('change',()=>{currentAssetId=null;productionState=null;approachState=null;refreshAll();});
$('refreshAssets').addEventListener('click',loadAssets);
$('refreshJobs').addEventListener('click',loadJobs);
$('runJob').addEventListener('click',()=>api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'ffmpeg_check',project:projectId()})}).then(loadJobs));
$('prepareProject').addEventListener('click',prepareProject);
$('syncProject').addEventListener('click',syncProject);
$('loadCore').addEventListener('click',bootstrapCore);
$('startProjectEngine').addEventListener('click',startProjectEngine);
$('syncProductionAssets').addEventListener('click',syncProductionAssets);
$('analyzeProduction').addEventListener('click',analyzeProduction);
$('songContext').addEventListener('click',()=>$('songContextDialog').showModal());
$('lyricsStatus').addEventListener('change',()=>{$('lyricsTextLabel').hidden=$('lyricsStatus').value!=='present';});
$('saveSongContext').addEventListener('click',e=>{e.preventDefault();saveSongContext().then(ok=>{if(ok)$('songContextDialog').close();});});
$('setApproach').addEventListener('click',openApproachDialog);
$('saveApproach').addEventListener('click',e=>{e.preventDefault();saveApproach().then(ok=>{if(ok)$('approachDialog').close();});});
$('setRoutes').addEventListener('click',openRoutesDialog);
$('saveRoutes').addEventListener('click',e=>{e.preventDefault();saveRoutes().then(ok=>{if(ok)$('routesDialog').close();});});
$('selectRoute').addEventListener('click',openRouteSelection);
$('saveRouteSelection').addEventListener('click',e=>{e.preventDefault();saveRouteSelection().then(ok=>{if(ok)$('routeSelectionDialog').close();});});
$('advanceProduction').addEventListener('click',advanceProduction);
$('verifyProjectEngine').addEventListener('click',verifyProjectEngine);
$('deleteAsset').addEventListener('click',deleteAsset);
document.querySelectorAll('[data-op]').forEach(b=>b.addEventListener('click',()=>operation(b.dataset.op)));
$('newProject').addEventListener('click',()=>$('projectDialog').showModal());
$('createProject').addEventListener('click',e=>{e.preventDefault();createProject().then(()=>$('projectDialog').close());});

(async()=>{await Promise.allSettled([loadHealth(),loadCapabilities(),loadProjects(),loadSystem(),loadCoreStatus()]);await refreshAll();})();
setInterval(()=>refreshAll(),2500);
