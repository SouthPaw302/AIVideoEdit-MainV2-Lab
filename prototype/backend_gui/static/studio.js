(() => {
  const stageOrder=['media','direction','storyboard','shots','assemble','finish'];
  const stageMap={
    INITIALIZED:'media',SOURCE_INGESTED:'media',REFERENCES_ANALYZED:'direction',APPROACH_ESTABLISHED:'storyboard',
    STORYBOARD_LOCKED:'shots',SHOT_PACKAGES_BUILT:'shots',SHOT_PROOFS_ACCEPTED:'assemble',FX_LOCKED:'assemble',
    ASSEMBLED:'finish',FINAL_QC_PASSED:'finish',ARCHIVED:'finish'
  };
  let activeSurface='media';
  let shotTemplate=null;
  let lastProject='';
  let lastStage='';

  const byId=id=>document.getElementById(id);
  const safe=v=>typeof esc==='function'?esc(v):String(v??'');
  const stageIndex=name=>stageOrder.indexOf(name);

  function selectSurface(name,user=false){
    if(!stageOrder.includes(name))name='media';
    activeSurface=name;
    document.querySelectorAll('.stage-surface').forEach(el=>el.classList.toggle('active',el.id===`surface-${name}`));
    document.querySelectorAll('[data-studio-stage]').forEach(el=>el.classList.toggle('active',el.dataset.studioStage===name));
    if(user)document.querySelector(`#surface-${name}`)?.scrollIntoView({block:'nearest'});
  }

  function syncRail(){
    const stage=productionState?.stage||'INITIALIZED';
    const current=stageMap[stage]||'media';
    const currentIndex=stageIndex(current);
    document.querySelectorAll('[data-studio-stage]').forEach(el=>{
      const i=stageIndex(el.dataset.studioStage);
      el.classList.toggle('done',i<currentIndex);
    });
    byId('stageChip').textContent=friendlyStage(stage||'INITIALIZED');
    byId('contextStage').textContent=friendlyStage(stage||'INITIALIZED');
    byId('engineDot').classList.toggle('online',!!coreState?.bootstrapped);
    if(lastStage!==stage){selectSurface(current);lastStage=stage;}
    const strip=byId('productionStrip');
    const show=stageIndex(current)>=2;
    strip.hidden=!show;
    if(show){
      byId('stripLabel').textContent=friendlyStage(stage);
      const total=productionState?.stage==='ARCHIVED'?6:Math.max(1,currentIndex+1);
      byId('stripTimeline').innerHTML=stageOrder.map((s,i)=>`<span class="strip-segment ${i<total?'active':''}" title="${safe(s)}"></span>`).join('');
    }
  }

  function syncTopAction(){
    const b=byId('topNextAction');
    b.disabled=false;
    if(!coreState?.bootstrapped){b.textContent='Load engine';b.onclick=()=>bootstrapCore();return;}
    if(!productionState?.initialized){b.textContent='Connect project';b.onclick=()=>startProjectEngine();return;}
    const stage=productionState.stage;
    if(stage==='INITIALIZED'){b.textContent='Sync media';b.onclick=()=>syncProductionAssets();return;}
    if(stage==='SOURCE_INGESTED'){b.textContent='Analyze song';b.onclick=()=>analyzeProduction();return;}
    if(stage==='REFERENCES_ANALYZED'){b.textContent='Set direction';b.onclick=()=>selectSurface('direction',true);return;}
    if(stage==='APPROACH_ESTABLISHED'){b.textContent='Build storyboard';b.onclick=()=>byId('storyboardOpen').click();return;}
    if(stage==='STORYBOARD_LOCKED'){b.textContent='Prepare shots';b.onclick=()=>selectSurface('shots',true);return;}
    if(stage==='SHOT_PACKAGES_BUILT'){b.textContent='Review proofs';b.onclick=()=>selectSurface('shots',true);return;}
    if(stage==='SHOT_PROOFS_ACCEPTED'){b.textContent='Lock effects';b.onclick=()=>selectSurface('assemble',true);return;}
    if(stage==='FX_LOCKED'){b.textContent='Assemble';b.onclick=()=>byId('runAssembly').click();return;}
    if(stage==='ASSEMBLED'){b.textContent='Final review';b.onclick=()=>selectSurface('finish',true);return;}
    if(stage==='FINAL_QC_PASSED'){b.textContent='Archive';b.onclick=()=>byId('archiveProject').click();return;}
    b.textContent='Archived';b.disabled=true;b.onclick=null;
  }

  function renderDirection(){
    const state=byId('directionState'),body=byId('directionSummary');
    if(!productionState?.initialized){state.textContent='Not connected';state.className='state-pill';body.className='surface-body empty-surface';body.textContent='Connect the production engine to begin.';return;}
    const routes=approachState?.route_options||[];
    const selected=approachState?.route_selection?.selected_option_numbers||[];
    const count=(approachState?.selected_capabilities||[]).length;
    state.textContent=productionState.stage==='APPROACH_ESTABLISHED'||stageIndex(stageMap[productionState.stage])>1?'Locked':count?'In progress':'Not set';
    state.className='state-pill '+(state.textContent==='Locked'?'pass':'');
    if(!count&&!routes.length){body.className='surface-body empty-surface';body.textContent='Set the creative approach to define the film’s media language.';return;}
    body.className='surface-body';
    if(routes.length){
      body.innerHTML=`<div class="direction-cards">${routes.map(r=>`<article class="direction-card ${selected.includes(Number(r.number))?'selected':''}"><span class="kicker">ROUTE ${safe(r.number)}</span><h4>${safe(r.name)}</h4><p>${safe(r.story_approach)}</p><div class="chip-row"><span class="mini-chip">${safe(r.production_mode||'mode unset')}</span>${selected.includes(Number(r.number))?'<span class="mini-chip">SELECTED</span>':''}</div></article>`).join('')}</div>`;
    }else{
      body.innerHTML=`<article class="status-card"><span class="kicker">APPROACH</span><h3>${count} production capabilities selected</h3><p>${safe(approachState?.approach_summary||'Visual reference is supplying the direction.')}</p></article>`;
    }
  }

  async function renderStoryboard(){
    const stage=productionState?.stage;
    const state=byId('storyboardState'),body=byId('storyboardVisual');
    if(!productionState?.initialized||!['APPROACH_ESTABLISHED','STORYBOARD_LOCKED','SHOT_PACKAGES_BUILT','SHOT_PROOFS_ACCEPTED','FX_LOCKED','ASSEMBLED','FINAL_QC_PASSED','ARCHIVED'].includes(stage)){
      state.textContent='Waiting';state.className='state-pill';body.className='storyboard-visual empty-surface';body.textContent='Establish the creative direction to unlock the storyboard.';return;
    }
    try{
      const s=await toolCall('storyboard.status',{project_id:projectId()});
      state.textContent=s.storyboard_locked?'Locked':s.storyboard_exists?'Draft':'Not built';state.className='state-pill '+(s.storyboard_locked?'pass':'');
      if(!s.entry_count){body.className='storyboard-visual empty-surface';body.textContent='Open the storyboard editor to map the song into shots.';return;}
      let entries=[];
      try{const t=await toolCall('shots.template',{project_id:projectId()});entries=t.shots||[];}catch(_){ }
      body.className='storyboard-visual';
      body.innerHTML=entries.length?`<div class="timeline-grid">${entries.map(x=>`<div class="timeline-shot"><strong>${safe(x.shot_id)}</strong><small>${safe(x.story_action||x.visual_media||'shot')}</small><small>${safe(x.start_frame)}–${safe(x.end_frame)}</small></div>`).join('')}</div>`:`<article class="status-card"><h3>${s.entry_count} shots · ${s.total_frames||0} frames</h3><p>${formatDuration(s.duration_seconds)} at ${s.target_fps||30} fps. ${s.storyboard_locked?'Storyboard is locked for production.':'Draft is still editable.'}</p></article>`;
    }catch(e){state.textContent='Needs attention';state.className='state-pill fail';body.className='storyboard-visual empty-surface';body.textContent=e.message;}
  }

  async function renderShots(){
    const state=byId('shotsState'),grid=byId('shotsGrid');
    const enabled=['STORYBOARD_LOCKED','SHOT_PACKAGES_BUILT','SHOT_PROOFS_ACCEPTED','FX_LOCKED','ASSEMBLED','FINAL_QC_PASSED','ARCHIVED'].includes(productionState?.stage);
    byId('saveShotPackages').disabled=!enabled||productionState?.stage!=='STORYBOARD_LOCKED';
    if(!enabled){state.textContent='Waiting';state.className='state-pill';grid.className='shots-grid empty-surface';grid.textContent='Lock the storyboard to unlock shot preparation.';return;}
    try{
      shotTemplate=await toolCall('shots.template',{project_id:projectId()});
      const shots=shotTemplate.shots||[],assets=shotTemplate.assets||[];
      state.textContent=shots.length?`${shots.length} shots`:'No shots';state.className='state-pill '+(shots.length?'pass':'');
      grid.className='shots-grid';
      grid.innerHTML=shots.map(s=>`<article class="shot-card" data-shot-card="${safe(s.shot_id)}"><span class="kicker">${safe(s.shot_id)}</span><h4>${safe(s.story_action||'Shot')}</h4><p>${safe(s.visual_media||'')}</p><div class="chip-row"><span class="mini-chip">frames ${safe(s.start_frame)}–${safe(s.end_frame)}</span>${s.current_assignment_count?`<span class="mini-chip">${s.current_assignment_count} assigned</span>`:''}</div><div class="asset-picks">${assets.length?assets.map(a=>`<label class="asset-pick"><input type="checkbox" data-shot-asset="${safe(s.shot_id)}" value="${safe(a.id)}" ${(s.current_asset_ids||[]).includes(a.id)?'checked':''}><span>${safe(a.filename)}<small>${safe(a.origin||'source')} · ${safe(a.creative_status||'ready')}</small></span></label>`).join(''):'<span class="micro">No ready, hashed media is available yet.</span>'}</div></article>`).join('');
    }catch(e){state.textContent='Needs attention';state.className='state-pill fail';grid.className='shots-grid empty-surface';grid.textContent=e.message;}
  }

  async function buildShotPackages(){
    if(!shotTemplate)return renderShots();
    const assignments=(shotTemplate.shots||[]).map(s=>({shot_id:s.shot_id,asset_ids:[...document.querySelectorAll(`[data-shot-asset="${CSS.escape(String(s.shot_id))}"]:checked`)].map(x=>x.value),status:'ingested',role:'scripted_visual_media'}));
    if(assignments.some(x=>!x.asset_ids.length)){byId('productionStatus').textContent='Every shot needs at least one real media asset.';return;}
    byId('saveShotPackages').disabled=true;
    try{await toolCall('shots.build_packages',{project_id:projectId(),assignments});byId('productionStatus').textContent='Shot packages built from real hashed media. Continue production to verify the gate.';await refreshAll();}
    catch(e){byId('productionStatus').textContent=e.message;}
    finally{byId('saveShotPackages').disabled=false;await renderShots();}
  }

  async function renderAssemble(){
    const body=byId('assembleBody'),state=byId('assembleState');
    if(!productionState?.initialized){state.textContent='Waiting';return;}
    try{
      const [proofs,fx,assembly]=await Promise.allSettled([
        toolCall('proofs.status',{project_id:projectId()}),toolCall('fx.status',{project_id:projectId()}),toolCall('assembly.status',{project_id:projectId()})
      ]);
      const p=proofs.value||{},f=fx.value||{},a=assembly.value||{};
      state.textContent=a.assembly_complete?'Assembled':f.fx_lock_verified?'Ready to assemble':p.shot_proofs_accepted?'Effects needed':'Proofs needed';
      state.className='state-pill '+(a.assembly_complete?'pass':'');
      body.className='surface-body';
      body.innerHTML=`<div class="state-list"><div class="state-line"><span>Shot proofs</span><strong class="${p.shot_proofs_accepted?'ok-text':'warn-text'}">${p.accepted_count||0}/${p.proof_count||0} accepted</strong></div><div class="state-line"><span>Effects lock</span><strong class="${f.fx_lock_verified?'ok-text':'warn-text'}">${f.fx_lock_verified?'Verified':'Not locked'}</strong></div><div class="state-line"><span>Workprint</span><strong class="${a.assembly_complete?'ok-text':'warn-text'}">${a.assembly_complete?'Ready':'Not assembled'}</strong></div></div>`;
      byId('runAssembly').disabled=productionState.stage!=='FX_LOCKED'||a.assembly_complete;
      byId('verifyFx').disabled=!f.lock_present;
    }catch(e){body.className='surface-body empty-surface';body.textContent=e.message;}
  }

  async function runAssembly(){
    byId('runAssembly').disabled=true;
    try{const r=await toolCall('assembly.run',{project_id:projectId(),width:1280,height:720});byId('productionStatus').textContent=`Assembly queued${r.job?.id?` · ${r.job.id}`:''}.`;await loadJobs();}
    catch(e){byId('productionStatus').textContent=e.message;}finally{setTimeout(renderAssemble,800);}
  }

  async function renderFinish(){
    const body=byId('finishBody'),state=byId('finishState');
    if(!productionState?.initialized)return;
    try{
      const [qc,archive]=await Promise.allSettled([toolCall('final_qc.status',{project_id:projectId()}),toolCall('archive.status',{project_id:projectId()})]);
      const q=qc.value||{},a=archive.value||{};
      state.textContent=a.archive_complete?'Archived':q.final_pass?'Accepted':q.technical_pass?'Creative review':'Waiting for QC';state.className='state-pill '+((a.archive_complete||q.final_pass)?'pass':'');
      body.className='surface-body';body.innerHTML=`<div class="state-list"><div class="state-line"><span>Technical QC</span><strong class="${q.technical_pass?'ok-text':'warn-text'}">${q.technical_pass?'PASS':'Pending'}</strong></div><div class="state-line"><span>Creative review</span><strong class="${q.creative_status==='accepted'?'ok-text':'warn-text'}">${safe(q.creative_status||'pending')}</strong></div><div class="state-line"><span>Archive</span><strong class="${a.archive_complete?'ok-text':'warn-text'}">${a.archive_complete?'Verified':'Not archived'}</strong></div></div>`;
      byId('runFinalQc').disabled=productionState.stage!=='ASSEMBLED';byId('archiveProject').disabled=productionState.stage!=='FINAL_QC_PASSED';
    }catch(e){body.className='surface-body empty-surface';body.textContent=e.message;}
  }

  async function runFinalQc(){byId('runFinalQc').disabled=true;try{await toolCall('final_qc.run_technical',{project_id:projectId()});byId('productionStatus').textContent='Technical final QC finished. Creative acceptance is still required before final pass.';await renderFinish();}catch(e){byId('productionStatus').textContent=e.message;}finally{byId('runFinalQc').disabled=false;}}
  async function archiveProject(){byId('archiveProject').disabled=true;try{await toolCall('archive.build',{project_id:projectId(),note:'Archived from Studio after accepted final QC.'});byId('productionStatus').textContent='Archive manifest created and content-addressed.';await refreshAll();}catch(e){byId('productionStatus').textContent=e.message;}finally{await renderFinish();}}
  async function verifyFx(){try{const r=await toolCall('fx.verify',{project_id:projectId()});byId('productionStatus').textContent=r.ok?'Effects lock verified.':'FX verification needs attention.';await renderAssemble();}catch(e){byId('productionStatus').textContent=e.message;}}

  function syncContext(){syncRail();syncTopAction();renderDirection();}
  async function refreshCreative(){
    const pid=byId('project')?.value||'';
    if(!pid)return;
    if(pid!==lastProject){lastProject=pid;shotTemplate=null;lastStage='';}
    syncContext();
    const surf=activeSurface;
    if(surf==='storyboard')await renderStoryboard();
    if(surf==='shots')await renderShots();
    if(surf==='assemble')await renderAssemble();
    if(surf==='finish')await renderFinish();
  }

  document.querySelectorAll('[data-studio-stage]').forEach(b=>b.addEventListener('click',()=>{selectSurface(b.dataset.studioStage,true);refreshCreative();}));
  byId('directionApproach').addEventListener('click',()=>byId('setApproach').click());
  byId('directionRoutes').addEventListener('click',()=>byId('setRoutes').click());
  byId('directionChoose').addEventListener('click',()=>byId('selectRoute').click());
  byId('storyboardOpen').addEventListener('click',()=>byId('storyboardEditor').click());
  byId('saveShotPackages').addEventListener('click',buildShotPackages);
  byId('refreshShots').addEventListener('click',renderShots);
  byId('runAssembly').addEventListener('click',runAssembly);
  byId('verifyFx').addEventListener('click',verifyFx);
  byId('runFinalQc').addEventListener('click',runFinalQc);
  byId('archiveProject').addEventListener('click',archiveProject);

  setInterval(refreshCreative,1800);
  setTimeout(refreshCreative,300);
})();
