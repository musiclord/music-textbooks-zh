/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 musiclord and contributors
 */
(() => {
  'use strict';
  function prepareFormula(source){
    // Preserve the original in data-latex; adapt only this unsupported layout.
    const match=/^\s*\\begin\{alignat\*\}\{2\}([\s\S]*)\\end\{alignat\*\}\s*$/.exec(source);
    if(match&&match[1].includes('\\hline')){
      const body=match[1].replace(/\u00a0/g,' ');
      const rows=body.split(/\\\\/).map(row=>row.trim()).filter(Boolean);
      if(rows.length&&rows.every(row=>row.includes('&&')&&(row.match(/&/g)||[]).length===2)){
        return {tex:'\\begin{array}{rr}'+body.replace(/&&/g,'&')+'\\end{array}',displayMode:true};
      }
    }
    return {tex:source,displayMode:/^\s*\\begin\{(?:align\*?|alignat\*?|equation\*?|gather\*?)\}/.test(source)};
  }
  // Allow the same pure preparation code to be checked with the bundled KaTeX.
  if(typeof document==='undefined'){
    if(typeof module!=='undefined')module.exports={prepareFormula};
    return;
  }
  const root=document.documentElement;
  const siteBase=new URL('.',document.currentScript.src);
  const siteURL=path=>new URL(path.replace(/^\//,''),siteBase);
  // This header remains mounted while chapter URLs change.
  const homeLink=document.querySelector('.library-name');
  if(homeLink)homeLink.href=siteURL('index.html').href;
  const content=document.getElementById('reader-content');
  if(!content)return;
  // Initialization runs on a page or newly appended chapter, never on the whole book.
  function prepareContent(scope){
    const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT),formulaNodes=[];
    while(walker.nextNode()){if(walker.currentNode.textContent.includes('[latex]'))formulaNodes.push(walker.currentNode);}
    for(const node of formulaNodes){
      const parts=node.textContent.split(/\[latex\]([\s\S]*?)\[\/latex\]/g),fragment=document.createDocumentFragment();
      parts.forEach((part,i)=>{if(i%2){const span=document.createElement('span');span.className='local-formula';span.dataset.latex=part;const formula=prepareFormula(part);try{katex.render(formula.tex,span,{displayMode:formula.displayMode,throwOnError:false,strict:'ignore'});}catch{span.textContent=part;}fragment.append(span);}else fragment.append(document.createTextNode(part));});node.replaceWith(fragment);
    }
    const articles=[...scope.querySelectorAll('[data-page-url]')];if(scope.matches?.('[data-page-url]'))articles.unshift(scope);
    articles.forEach(a=>{a.dataset.pageUrl=siteURL(a.dataset.pageUrl).href;if(a.dataset.nextUrl)a.dataset.nextUrl=siteURL(a.dataset.nextUrl).href;});
    const menu=scope.querySelector('#book-menu');if(menu)menu.open=matchMedia('(min-width:901px)').matches;
  }
  const get=(k,d)=>{try{return localStorage.getItem(k)||d;}catch{return d;}};
  const save=(k,v)=>{try{localStorage.setItem(k,v);}catch{}};
  let size=Number(get('readings-font','19'));
  root.style.setProperty('--reading-size',size+'px');
  root.dataset.theme=get('readings-theme','light');
  const theme=document.getElementById('theme-toggle');
  const themeLabel=()=>{theme.textContent=root.dataset.theme==='dark'?'淺色':'深色';};
  themeLabel();
  theme.addEventListener('click',()=>{root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';root.style.colorScheme=root.dataset.theme;save('readings-theme',root.dataset.theme);themeLabel();});
  for(const [id,delta] of [['font-smaller',-1],['font-larger',1]])document.getElementById(id).addEventListener('click',()=>{size=Math.max(16,Math.min(28,size+delta));root.style.setProperty('--reading-size',size+'px');save('readings-font',String(size));});
  const mq=matchMedia('(min-width:901px)');
  mq.addEventListener('change',()=>{const menu=content.querySelector('#book-menu');if(menu)menu.open=mq.matches;});
  const imageDialog=document.getElementById('image-dialog');
  const openImage=(src,alt,caption)=>{const large=document.getElementById('enlarged-image');large.src=src;large.alt=alt;document.getElementById('image-caption').textContent=caption;imageDialog.showModal();};
  const zoom=(img)=>openImage(img.src,img.alt,img.closest('figure')?.querySelector('figcaption')?.textContent||img.alt);
  content.addEventListener('keydown',e=>{if(e.target.matches('img.zoomable')&&(e.key==='Enter'||e.key===' ')){e.preventDefault();zoom(e.target);}});
  const searchDialog=document.getElementById('search-dialog'),input=document.getElementById('book-search'),results=document.getElementById('search-results'),summary=document.getElementById('search-summary');
  let index=null,pending=null;
  async function search(){
    const query=input.value.trim().toLocaleLowerCase();results.replaceChildren();if(!query){summary.textContent='輸入詞語以搜尋正文與英文對照。';return;}
    if(!index){summary.textContent='正在讀取搜尋資料…';try{pending=pending||fetch(new URL('search-index.json',siteBase)).then(r=>{if(!r.ok)throw Error('index');return r.json();});index=await pending;}catch{pending=null;summary.textContent='搜尋資料未能載入，請稍後重試。';return;}}
    if(query!==input.value.trim().toLocaleLowerCase())return;
    const terms=query.split(/\s+/),matches=index.filter(p=>terms.every(t=>(p.title+' '+p.text+' '+p.en).toLocaleLowerCase().includes(t)));
    summary.textContent='找到 '+matches.length+' 個段落'+(matches.length>60?'，顯示前 60 筆。':'。');
    for(const item of matches.slice(0,60)){const li=document.createElement('li'),a=document.createElement('a'),p=document.createElement('p');a.href=siteURL(item.url);a.textContent=item.title;p.textContent=item.text.slice(0,180);li.append(a,p);results.append(li);}
  }
  document.getElementById('search-open').addEventListener('click',()=>{searchDialog.showModal();input.focus();search();});
  input.addEventListener('input',search);
  let generation=0,nextBusy=false,navigating=false,nextObserver=null,continuous=get('readings-continuous','off')==='on';
  const continuousButton=document.getElementById('continuous-toggle');
  const notice=document.getElementById('navigation-status');
  const pageCache=new Map();
  function decodedHash(hash){try{return decodeURIComponent(hash.slice(1));}catch{return '';}}
  function reveal(el){
    if(!el)return false;
    if(el.dataset.forward){navigate(siteURL(el.dataset.forward),{replace:true});return true;}
    for(let p=el.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;
    el.scrollIntoView({behavior:'instant',block:'start'});return true;
  }
  function remember(){
    if(navigating)return;
    const units=[...content.querySelectorAll('.translation-unit')];
    const unit=units.find(u=>u.getBoundingClientRect().bottom>90&&u.getBoundingClientRect().height>0);
    history.replaceState({reader:true,y:scrollY,anchor:unit?.id,offset:unit?.getBoundingClientRect().top},'',location.href);
  }
  async function loadPage(url){
    const key=url.origin+url.pathname;
    let raw=pageCache.get(key);
    if(!raw){
      const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
      try{const response=await fetch(key,{signal:controller.signal});if(!response.ok)throw Error('page');raw=await response.text();}
      finally{clearTimeout(timeout);}
      pageCache.set(key,raw);if(pageCache.size>8)pageCache.delete(pageCache.keys().next().value);
    }
    const doc=new DOMParser().parseFromString(raw,'text/html'),main=doc.getElementById('reader-content');
    if(!main)throw Error('unrecognized page');
    // Relative resource paths belong to the fetched page, not the current URL.
    main.querySelectorAll('[href],[src]').forEach(el=>{for(const attr of ['href','src'])if(el.hasAttribute(attr))el.setAttribute(attr,new URL(el.getAttribute(attr),url).href);});
    return {doc,main};
  }
  function updateSidebar(url){
    content.querySelectorAll('.book-sidebar a').forEach(a=>{
      if(new URL(a.href).pathname===url.pathname){a.setAttribute('aria-current','page');const group=a.closest('.toc-group');if(group)group.open=true;}
      else a.removeAttribute('aria-current');
    });
  }
  async function navigate(url,{replace=false,popState=null}={}){
    if(!popState)remember();
    const token=++generation;navigating=true;clearTimeout(scrollTimer);nextObserver?.disconnect();nextBusy=false;
    notice.textContent='正在載入章節…';
    try{
      const {doc,main}=await loadPage(url);if(token!==generation)return;
      if(!popState)history[replace?'replaceState':'pushState']({reader:true,y:0},'',url);
      content.replaceChildren(...main.childNodes);document.title=doc.title;
      prepareContent(content);updateSidebar(url);
      document.querySelectorAll('dialog[open]').forEach(d=>d.close());
      const heading=content.querySelector('h1');heading?.setAttribute('tabindex','-1');heading?.focus({preventScroll:true});
      const hash=decodedHash(url.hash);
      if(hash&&reveal(document.getElementById(hash))){}
      else if(popState?.anchor&&document.getElementById(popState.anchor)){
        const target=document.getElementById(popState.anchor);reveal(target);
        scrollBy(0,target.getBoundingClientRect().top-(popState.offset||0));
      }else scrollTo({top:popState?.y||0,behavior:'instant'});
      if(token!==generation)return;
      notice.textContent='已載入 '+(heading?.textContent||doc.title);setupContinuation();
    }catch(error){if(token===generation){notice.textContent='重新開啟章節…';location.assign(url.href);}}
    finally{if(token===generation)navigating=false;}
  }
  function setupContinuation(){
    nextObserver?.disconnect();content.querySelectorAll('.continuation').forEach(n=>n.remove());
    continuousButton.setAttribute('aria-pressed',String(continuous));
    const stack=content.querySelector('.reading-stack'),last=stack?.querySelector('.reading:last-of-type');
    continuousButton.disabled=!stack;
    if(!continuous||!last?.dataset.nextUrl)return;
    const sentinel=document.createElement('div');sentinel.className='continuation';
    const button=document.createElement('button');button.textContent='載入下一節';button.dataset.loadNext='';
    sentinel.append(button);stack.append(sentinel);
    if('IntersectionObserver' in window){nextObserver=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting))appendNext();},{rootMargin:'350px'});nextObserver.observe(sentinel);}
  }
  async function appendNext(){
    if(nextBusy||navigating||!continuous)return;
    const stack=content.querySelector('.reading-stack'),last=stack?.querySelector('.reading:last-of-type');
    if(!last?.dataset.nextUrl)return;
    const token=generation,url=new URL(last.dataset.nextUrl),sentinel=stack.querySelector('.continuation');
    if([...stack.querySelectorAll('.reading')].some(a=>new URL(a.dataset.pageUrl).pathname===url.pathname))return;
    nextBusy=true;nextObserver?.disconnect();if(sentinel)sentinel.textContent='正在載入下一節…';
    try{
      const {main}=await loadPage(url);if(token!==generation||!continuous)return;
      const article=main.querySelector('article.reading');
      if(!article||article.dataset.book!==last.dataset.book)throw Error('book boundary');
      // Legacy bookmarks exist on the old page; avoid duplicating real unit IDs.
      article.querySelectorAll('[id]').forEach(el=>{const old=document.getElementById(el.id);if(old?.classList.contains('legacy-anchor'))old.removeAttribute('id');});
      stack.querySelector('.continuation')?.remove();stack.append(article);prepareContent(article);setupContinuation();
      notice.textContent='已接續載入 '+article.querySelector('h1').textContent;
    }catch(error){
      if(token===generation&&sentinel){sentinel.replaceChildren();const button=document.createElement('button');button.dataset.loadNext='';button.textContent='載入失敗，重試下一節';sentinel.append(button);}
    }finally{if(token===generation)nextBusy=false;}
  }
  continuousButton.addEventListener('click',()=>{continuous=!continuous;save('readings-continuous',continuous?'on':'off');setupContinuation();notice.textContent=continuous?'已開啟連續閱讀。捲至底部會接續下一節。':'已關閉自動接續載入。';});
  document.addEventListener('click',e=>{
    if(e.defaultPrevented||e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
    const load=e.target.closest('[data-load-next]');if(load){e.preventDefault();appendNext();return;}
    const img=e.target.closest('img.zoomable');if(img){e.preventDefault();zoom(img);return;}
    const a=e.target.closest('a[href]');if(!a||a.target==='_blank'||a.hasAttribute('download'))return;
    if(a.classList.contains('linked-score-image')){e.preventDefault();openImage(a.href,a.dataset.imageAlt,a.dataset.imageCaption);return;}
    const url=new URL(a.href);
    if(url.origin!==siteBase.origin||!url.pathname.startsWith(siteBase.pathname)||(!url.pathname.endsWith('.html')&&url.pathname!==siteBase.pathname))return;
    e.preventDefault();
    const loaded=[...content.querySelectorAll('.reading[data-page-url]')].find(p=>new URL(p.dataset.pageUrl).pathname===url.pathname);
    const target=url.hash?document.getElementById(decodedHash(url.hash)):loaded?.querySelector('h1');
    if((loaded||url.pathname===location.pathname)&&target){remember();history.pushState({reader:true,y:0},'',url);document.querySelectorAll('dialog[open]').forEach(d=>d.close());reveal(target);updateSidebar(url);return;}
    navigate(url);
  });
  addEventListener('popstate',e=>navigate(new URL(location.href),{popState:e.state||{y:0}}));
  addEventListener('hashchange',()=>reveal(document.getElementById(decodedHash(location.hash))));
  let scrollTimer;
  addEventListener('scroll',()=>{clearTimeout(scrollTimer);if(navigating)return;scrollTimer=setTimeout(()=>{
    if(continuous){
      const articles=[...content.querySelectorAll('.reading[data-page-url]')];
      const active=articles.filter(a=>a.getBoundingClientRect().top<=130).at(-1);
      if(active&&new URL(active.dataset.pageUrl).pathname!==location.pathname){
        history.replaceState(history.state,'',active.dataset.pageUrl);document.title=active.querySelector('h1').textContent+' – 音樂教材';updateSidebar(new URL(active.dataset.pageUrl));
      }
    }
    remember();
  },160);},{passive:true});
  prepareContent(content);setupContinuation();
  if(location.hash)reveal(document.getElementById(decodedHash(location.hash)));
  else history.replaceState({reader:true,y:scrollY},'',location.href);
})();
