(() => {
  const id=x=>document.getElementById(x);
  const safe=v=>typeof esc==='function'?esc(v):String(v??'');
  let operatingState=null;

  const capabilityGroup = cap => {
    const x=String(cap?.id||'').toLowerCase();
    if(/generated|painting/.test(x))return 'Generated imagery';
    if(/depth|25d|perspective|motion|parallax/.test(x))return 'Depth & motion';
    if(/atmos|plate|reflection|composite/.test(x))return 'Atmosphere';
    if(/reactive|audio|visualizer/.test(x))return 'Music-reactive';
    if(/nerf|3d|gaussian|splat/.test(x))return '3D / spatial';
    return 'Source footage';
  };

  async function refreshOperating(){
    if(!productionState?.initialized){operatingState=null;id('directorModeLabel').textContent='Legacy / not configured';id('directorModeMeta').textContent='Connect the production engine before enabling Director Brain v3.';id('configureDirector').disabled=true;return;}
    id('configureDirector').disabled=false;
    try{
      operatingState=await toolCall('operating.status',{project_id:projectId()});
      const version=Number(operatingState.director_brain_version||0);
      if(version>=2){
        id('directorModeLabel').textContent=`${String(operatingState.production_mode||'').replaceAll('_',' ')} · ${String(operatingState.direction_authority||'').replaceAll('_',' ')}`;
        id('directorModeMeta').textContent=operatingState.current_user_direction||operatingState.mission||'Director Brain v3 configured.';
      }else{
        id('directorModeLabel').textContent='Legacy / not configured';
        id('directorModeMeta').textContent='Enable v2 to explicitly lock direction authority and production mode.';
      }
    }catch(e){id('directorModeMeta').textContent=e.message;}
  }

  async function openDirector(){
    await refreshOperating();
    if(operatingState?.director_brain_version>=2){
      id('directionAuthority').value=operatingState.direction_authority||'music_led';
      id('productionMode').value=operatingState.production_mode||'cinematic';
      id('directorMission').value=operatingState.mission||'';
      id('directorCurrentDirection').value=operatingState.current_user_direction||'';
      id('directorNextAction').value=operatingState.exact_next_action||'';
    }
    id('directorDialog').showModal();
  }

  async function saveDirector(){
    const args={project_id:projectId(),direction_authority:id('directionAuthority').value,production_mode:id('productionMode').value,mission:id('directorMission').value.trim(),current_user_direction:id('directorCurrentDirection').value.trim(),exact_next_action:id('directorNextAction').value.trim()};
    if(!args.mission||!args.current_user_direction||!args.exact_next_action){id('productionStatus').textContent='Mission, current direction, and exact next action are required.';return;}
    id('saveDirectorMode').disabled=true;
    try{operatingState=await toolCall('operating.configure_v3',args);id('directorDialog').close();id('productionStatus').textContent='Director Brain v3 enabled with explicit authority and production mode.';await refreshOperating();}
    catch(e){id('productionStatus').textContent=e.message;}
    finally{id('saveDirectorMode').disabled=false;}
  }

  function enhanceRouteForms(){
    document.querySelectorAll('#routeForms [data-route]').forEach((fs,i)=>{
      if(fs.querySelector('[data-route-mode]'))return;
      const existing=approachState?.route_options?.[i]?.production_mode||operatingState?.production_mode||'cinematic';
      const label=document.createElement('label');label.className='stage-mode-select';label.innerHTML='Production mode<select data-route-mode><option value="cinematic">Cinematic</option><option value="living_scene">Living scene</option><option value="hybrid">Hybrid</option></select>';fs.insertBefore(label,fs.querySelector('[data-route-story]')?.closest('label')||fs.firstChild);label.querySelector('select').value=existing;
    });
  }

  async function saveRoutesModeAware(e){
    e.preventDefault();e.stopImmediatePropagation();enhanceRouteForms();
    const routes=[...document.querySelectorAll('#routeForms [data-route]')].map(fs=>({number:Number(fs.dataset.route),name:fs.querySelector('[data-route-name]').value.trim(),production_mode:fs.querySelector('[data-route-mode]').value,story_approach:fs.querySelector('[data-route-story]').value.trim(),rendering_route:fs.querySelector('[data-route-render]').value.trim(),storyboard:[...fs.querySelectorAll('[data-route-beat]')].map(b=>({number:Number(b.dataset.routeBeat),description:b.value.trim()}))}));
    if(routes.some(r=>!r.name||!r.story_approach||!r.rendering_route||!r.production_mode||r.storyboard.some(b=>!b.description))){id('productionStatus').textContent='Complete the mode, concept, rendering treatment, and three beats for every route.';return;}
    id('saveRoutes').disabled=true;
    try{approachState=await toolCall('approach.set_routes',{project_id:projectId(),routes,presentation_channel:'studio'});id('routesDialog').close();id('productionStatus').textContent='Visual routes saved with explicit production modes.';await loadApproachStatus();}
    catch(err){id('productionStatus').textContent=err.message;}
    finally{id('saveRoutes').disabled=false;}
  }

  async function groupCapabilities(){
    const host=id('approachCapabilities');if(!host)return;
    const labels=[...host.querySelectorAll(':scope > label')];if(!labels.length)return;
    let caps=[];try{caps=(await toolCall('capabilities.list')).capabilities||[];}catch(_){return;}
    const byId=new Map(caps.map(c=>[String(c.id),c])),groups=new Map();
    labels.forEach(label=>{const input=label.querySelector('[data-capability]');if(!input)return;const name=capabilityGroup(byId.get(input.dataset.capability)||{id:input.dataset.capability});if(!groups.has(name))groups.set(name,[]);groups.get(name).push(label);});
    host.innerHTML='';
    for(const [name,items] of groups){const box=document.createElement('section');box.className='capability-group';box.innerHTML=`<h4>${safe(name)}</h4>`;items.forEach(label=>{label.classList.add('capability-option');box.appendChild(label)});host.appendChild(box);}
  }

  const routeObserver=new MutationObserver(()=>enhanceRouteForms());
  if(id('routeForms'))routeObserver.observe(id('routeForms'),{childList:true,subtree:true});
  id('configureDirector')?.addEventListener('click',openDirector);
  id('saveDirectorMode')?.addEventListener('click',saveDirector);
  id('saveRoutes')?.addEventListener('click',saveRoutesModeAware,true);
  setInterval(()=>{refreshOperating();groupCapabilities();},1800);setTimeout(()=>{refreshOperating();groupCapabilities();},500);
})();
