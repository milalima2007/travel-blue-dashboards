#!/usr/bin/env python3
"""
Gerador de Dashboard HTML - Contas a Receber Travel Blue
Uso: python generate_contas_receber.py [arquivo.xlsx] [saida.html]
"""
import pandas as pd
import json
from datetime import datetime
import os, sys

INPUT_DEFAULT  = r'C:\Users\Soporte\Downloads\pivot - 2026-03-18T112807.196.xlsx'
OUTPUT_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'contas-receber.html')

# ─────────────────────────────────────────────
# DATA PROCESSING
# ─────────────────────────────────────────────
def process_excel(path):
    df = pd.read_excel(path, sheet_name=0)
    df.columns = [
        'Previsao','CNPJ_CPF','Razao_Social','Emissao','Vencimento',
        'Nota_Fiscal','Parcela','Documento','Vendedor','Valor_Liquido',
        'Pago_Recebido','A_Receber','Cidade','Nome_Fantasia','Dias_Atraso'
    ]
    for col in ['Vencimento','Emissao','Previsao']:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    df['Vencimento_fmt'] = df['Vencimento'].dt.strftime('%d/%m/%Y')

    PERIODOS = [
        'Este Mês (1-31 dias)',
        'Últimos 3 Meses (32-90 dias)',
        '3 a 6 Meses (91-180 dias)',
        '6 Meses a 1 Ano (181-365 dias)',
        'Mais de 1 Ano (>365 dias)',
    ]

    def classify(d):
        if d <= 0:    return -1
        elif d <= 31: return 0
        elif d <= 90: return 1
        elif d <= 180:return 2
        elif d <= 365:return 3
        else:         return 4

    df['P_idx']  = df['Dias_Atraso'].apply(classify)
    df['Periodo']= df['P_idx'].apply(lambda i: PERIODOS[i] if i >= 0 else '')

    vencidas_df = df[df['Dias_Atraso'] >  0].copy()
    hoje_df     = df[df['Dias_Atraso'] == 0].copy()
    futuras_df  = df[df['Dias_Atraso'] <  0].copy()

    def wlabel(dt):
        if pd.isna(dt): return ''
        p = dt.to_period('W')
        return p.start_time.strftime('%d/%m/%Y') + ' a ' + p.end_time.strftime('%d/%m/%Y')
    def wsort(dt):
        if pd.isna(dt): return '9999'
        return dt.to_period('W').start_time.strftime('%Y-%m-%d')

    futuras_df['Semana']      = futuras_df['Vencimento'].apply(wlabel)
    futuras_df['Semana_Sort'] = futuras_df['Vencimento'].apply(wsort)

    def to_rec(d, extra=[]):
        base = ['Razao_Social','Nome_Fantasia','CNPJ_CPF','Vendedor',
                'Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber','Pago_Recebido','Cidade']
        cols = [c for c in base+extra if c in d.columns]
        out  = []
        for _, row in d[cols].iterrows():
            rec = {}
            for c in cols:
                v = row[c]
                if isinstance(v, float) and pd.isna(v): rec[c] = ''
                elif isinstance(v, float):              rec[c] = round(v, 2)
                elif isinstance(v, (int,)):             rec[c] = int(v)
                elif not isinstance(v, str) and pd.isna(v): rec[c] = ''
                else: rec[c] = str(v) if not isinstance(v, str) else v
            out.append(rec)
        return out

    def uniq(s):
        return sorted({str(x) for x in s.dropna() if str(x) not in ('','nan')})

    semanas_raw = futuras_df[['Semana','Semana_Sort']].drop_duplicates().values.tolist()
    semanas = [s[0] for s in sorted(semanas_raw, key=lambda x: x[1])]

    return {
        'gerado_em': datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'periodos' : PERIODOS,
        'vencidas' : to_rec(vencidas_df, ['Dias_Atraso','Periodo','P_idx']),
        'hoje'     : to_rec(hoje_df),
        'futuras'  : to_rec(futuras_df, ['Semana','Semana_Sort']),
        'vendedores': uniq(df['Vendedor']),
        'clientes'  : uniq(df['Nome_Fantasia']),
        'semanas'   : semanas,
    }

# ─────────────────────────────────────────────
# HTML BUILDER
# ─────────────────────────────────────────────
def build_html(data):
    data_json = json.dumps(data, ensure_ascii=False, default=str)
    return (HTML_TEMPLATE
            .replace('__DATA_JSON__', data_json)
            .replace('__GERADO_EM__', data['gerado_em']))

# ─────────────────────────────────────────────
# TEMPLATE
# ─────────────────────────────────────────────
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Contas a Receber – Travel Blue</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
:root{--bg:#0a0e1a;--card:#111827;--border:#1e293b;--text:#e2e8f0;--dim:#64748b;
  --accent:#f59e0b;--green:#10b981;--red:#ef4444;--blue:#3b82f6;--purple:#8b5cf6;
  --c0:#ef4444;--c1:#f97316;--c2:#eab308;--c3:#a855f7;--c4:#64748b;}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:13px;line-height:1.5}
/* ── HEADER ── */
.header{background:linear-gradient(135deg,#111827 0%,#1e293b 100%);padding:14px 24px;
  border-bottom:2px solid var(--accent);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}
.logo{display:flex;align-items:center;gap:10px;}
.logo-text .brand{font-size:17px;font-weight:700;color:#fff;display:block;}
.logo-text .sub{font-size:11px;color:var(--dim);}
.header-right{text-align:right;font-size:11px;color:var(--dim);}
/* ── TABS ── */
.tabs{display:flex;gap:2px;padding:6px 16px;background:#0f172a;overflow-x:auto;}
.tab{padding:8px 16px;border-radius:6px 6px 0 0;cursor:pointer;font-size:12px;font-weight:600;
  color:var(--dim);white-space:nowrap;transition:all .2s;border:none;background:none;}
.tab:hover{color:var(--text);background:#1e293b;}
.tab.active{color:var(--accent);background:var(--card);border-top:2px solid var(--accent);}
/* ── KPIs ── */
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px;}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 18px;text-align:center;}
.kpi .lbl{font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;}
.kpi .val{font-size:20px;font-weight:800;color:var(--accent);margin:4px 0;}
.kpi .cnt{font-size:11px;color:var(--dim);}
/* ── CONTENT ── */
.content{padding:16px 24px;max-width:1400px;margin:0 auto;}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px;margin-bottom:16px;}
/* ── FILTER BAR ── */
.fbar{background:#0f172a;border:1px solid var(--border);border-radius:8px;padding:10px 14px;
  display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px;}
.fbar select{background:#111827;border:1px solid var(--border);border-radius:6px;color:var(--text);
  font-size:11px;padding:5px 8px;cursor:pointer;max-width:220px;}
.fbar select:focus{outline:none;border-color:var(--accent);}
.fbar-reset{padding:5px 12px;border-radius:6px;background:#1e293b;border:1px solid var(--border);
  color:var(--dim);font-size:11px;font-weight:600;cursor:pointer;}
.fbar-reset:hover{background:var(--accent);color:#000;border-color:var(--accent);}
/* ── VIEW BUTTONS ── */
.vbtns{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap;}
.vb{padding:5px 14px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;
  background:#1e293b;border:1px solid var(--border);color:var(--dim);transition:all .15s;}
.vb:hover{color:var(--text);}
.vb.act-d{background:#ef444422;color:var(--red);border-color:var(--red);}
.vb.act-h{background:#f59e0b22;color:var(--accent);border-color:var(--accent);}
.vb.act-f{background:#10b98122;color:var(--green);border-color:var(--green);}
/* ── PERIOD CARDS ── */
.period-grid{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px;}
.pc{flex:1 1 150px;background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:12px 14px;cursor:pointer;transition:transform .15s,box-shadow .15s;border-left:3px solid;}
.pc:hover{transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,0,0,.4);}
.pc.sel{box-shadow:0 0 0 2px var(--accent);}
.pc .pcl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px;}
.pc .pcc{font-size:11px;color:var(--dim);margin:3px 0;}
.pc .pcv{font-size:16px;font-weight:800;}
.pc .pcsub{font-size:10px;color:var(--dim);margin-top:2px;}
/* ── TABLES ── */
.tbl-wrap{overflow-x:auto;}
table.dt{width:100%;border-collapse:collapse;font-size:12px;}
table.dt th{text-align:left;padding:8px 10px;border-bottom:2px solid var(--accent);
  color:var(--accent);font-weight:700;font-size:11px;text-transform:uppercase;
  cursor:pointer;white-space:nowrap;user-select:none;position:sticky;top:0;background:var(--card);z-index:1;}
table.dt th:hover{color:#fff;}
table.dt td{padding:6px 10px;border-bottom:1px solid #1e293b;}
table.dt tr:hover td{background:#1e293b55;}
table.dt tr.tot td{background:#1e293b;font-weight:700;border-top:2px solid var(--accent);color:var(--accent);}
.nr{text-align:right;}
.sa{font-size:10px;margin-left:3px;opacity:.5;}
/* ── BADGES ── */
.badge-p{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:700;}
.bp0{background:#ef444422;color:var(--c0);}
.bp1{background:#f9731622;color:var(--c1);}
.bp2{background:#eab30822;color:var(--c2);}
.bp3{background:#a855f722;color:var(--c3);}
.bp4{background:#64748b22;color:var(--c4);}
.wk{display:inline-block;background:#3b82f622;color:var(--blue);padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;}
.cnt-badge{background:#f59e0b22;color:var(--accent);border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;}
.section-hdr{display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;}
.empty{text-align:center;color:var(--dim);padding:32px 0;}
.nowrap{white-space:nowrap;}
footer{text-align:center;color:var(--dim);font-size:11px;padding:16px;border-top:1px solid var(--border);margin-top:8px;}
.fbar-search{background:#111827;border:1px solid var(--border);border-radius:6px;color:var(--text);
  font-size:11px;padding:5px 10px;min-width:180px;flex:1 1 180px;}
.fbar-search:focus{outline:none;border-color:var(--accent);}
.fbar-search::placeholder{color:var(--dim);}
.ss-wrap{display:flex;align-items:center;border:1px solid var(--border);border-radius:6px;background:#111827;overflow:hidden;flex:1 1 200px;max-width:280px;}
.ss-wrap:focus-within{border-color:var(--accent);}
.ss-lupa{padding:0 6px;color:var(--dim);pointer-events:none;display:flex;align-items:center;font-size:12px;}
.ss-inp{background:transparent;border:none;color:var(--text);font-size:11px;padding:5px 2px;width:72px;min-width:40px;outline:none;}
.ss-inp::placeholder{color:var(--dim);}
.ss-sel{background:transparent;border:none;border-left:1px solid var(--border);color:var(--text);font-size:11px;padding:5px 4px;cursor:pointer;flex:1;min-width:90px;max-width:180px;outline:none;}
.ss-sel:focus{outline:none;}
.ss-sel option{background:#1e293b;color:var(--text);}
@media(max-width:768px){.kpi-row{grid-template-columns:repeat(2,1fr);}.pc{flex:1 1 130px;}}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <svg viewBox="0 0 48 48" width="40" height="40" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="8" fill="#1B2A6B"/>
      <path d="M10 34 Q16 10 24 24 Q32 38 38 14" stroke="#FFC72C" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <circle cx="38" cy="14" r="2.5" fill="#FFC72C"/>
    </svg>
    <div class="logo-text">
      <span class="brand">Travel Blue</span>
      <span class="sub">Contas a Receber · Brasil</span>
    </div>
  </div>
  <div class="header-right">Gerado em __GERADO_EM__</div>
</div>

<div class="kpi-row" id="kpis"></div>

<div class="tabs" id="nav">
  <button class="tab active" data-t="vencidas">⚠ Contas Vencidas</button>
  <button class="tab" data-t="hoje">⏰ Vencem Hoje</button>
  <button class="tab" data-t="futuras">📅 Contas Futuras</button>
</div>

<div class="content" id="content"></div>

<footer>Travel Blue Brasil · Dashboard Contas a Receber · Dados processados automaticamente</footer>
<script>
const D = __DATA_JSON__;

/* ── HELPERS ── */
const R = (n,d=2) => typeof n==='number' ? n.toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d}) : (n||'—');
const BRL = v => 'R$ '+R(v);
const sum = (a,k) => a.reduce((s,r)=>s+(parseFloat(r[k])||0),0);
const grp = (a,k) => a.reduce((g,r)=>{const v=r[k]||'N/D';(g[v]=g[v]||[]).push(r);return g;},{});
const esc = s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const opts= (arr,ph)=>'<option value="">'+ph+'</option>'+arr.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');
const NUM_COLS = new Set(['A_Receber','Pago_Recebido','Dias_Atraso','Nota_Fiscal']);

/* sort state */
const SS = {};
function sortTbl(id,ci){
  const t=document.getElementById(id); if(!t) return;
  const prev=SS[id]||{c:-1,a:true};
  const asc = prev.c===ci?!prev.a:true;
  SS[id]={c:ci,a:asc};
  const tb=t.querySelector('tbody');
  const rows=[...tb.querySelectorAll('tr:not(.tot)')];
  rows.sort((a,b)=>{
    const av=a.cells[ci]?.dataset.v??'', bv=b.cells[ci]?.dataset.v??'';
    const an=parseFloat(av), bn=parseFloat(bv);
    const cmp=(!isNaN(an)&&!isNaN(bn))?(an-bn):av.localeCompare(bv,'pt-BR');
    return asc?cmp:-cmp;
  });
  rows.forEach(r=>tb.appendChild(r));
  t.querySelectorAll('thead th').forEach((th,i)=>{
    const s=th.querySelector('.sa'); if(s) s.textContent=i===ci?(asc?'▲':'▼'):'⇅';
  });
}
function TH(l,i,id){return '<th onclick="sortTbl(\''+id+'\','+i+')">'+esc(l)+' <span class="sa">⇅</span></th>';}

/* ── KPIs ── */
function renderKPIs(){
  const tv=sum(D.vencidas,'A_Receber'), th2=sum(D.hoje,'A_Receber'), tf=sum(D.futuras,'A_Receber');
  const tot=tv+th2+tf;
  const ks=[
    {l:'Total Vencido',v:BRL(tv),c:'#ef4444',n:D.vencidas.length},
    {l:'Vence Hoje',v:BRL(th2),c:'#f59e0b',n:D.hoje.length},
    {l:'A Receber (Futuro)',v:BRL(tf),c:'#10b981',n:D.futuras.length},
    {l:'Total Geral',v:BRL(tot),c:'#3b82f6',n:D.vencidas.length+D.hoje.length+D.futuras.length},
  ];
  document.getElementById('kpis').innerHTML=ks.map(k=>
    '<div class="kpi">'
    +'<div class="lbl">'+k.l+'</div>'
    +'<div class="val" style="color:'+k.c+'">'+k.v+'</div>'
    +'<div class="cnt">'+k.n+' título'+(k.n!==1?'s':'')+'</div></div>'
  ).join('');
}

/* ── STATE ── */
let activeTab='vencidas';
const F={vencidas:{periodo:'',vendedor:'',cliente:'',search:''},futuras:{semana:'',vendedor:'',cliente:'',search:''}};
const V={vencidas:'periodo',hoje:'cliente',futuras:'semana'};

/* ── TABS ── */
function initNav(){
  document.querySelectorAll('#nav button').forEach(b=>{
    b.addEventListener('click',()=>{
      document.querySelectorAll('#nav button').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      activeTab=b.dataset.t;
      renderTab();
    });
  });
}
function renderTab(){
  if(activeTab==='vencidas') renderVencidas();
  else if(activeTab==='hoje') renderHoje();
  else renderFuturas();
}

/* ── FILTER HELPERS ── */
function applyF(data,section){
  const f=F[section], q=(f.search||'').toLowerCase().trim();
  return data.filter(r=>{
    if(f.periodo&&r.Periodo!==f.periodo) return false;
    if(f.semana&&r.Semana!==f.semana) return false;
    if(f.vendedor&&r.Vendedor!==f.vendedor) return false;
    if(f.cliente&&r.Nome_Fantasia!==f.cliente) return false;
    if(q){const hay=[r.Razao_Social,r.Nome_Fantasia,r.Vendedor,String(r.Nota_Fiscal||''),r.CNPJ_CPF].map(x=>String(x||'').toLowerCase()).join(' ');if(!hay.includes(q)) return false;}
    return true;
  });
}
/* returns sorted unique values of rowField from allData filtered by f, ignoring selfKey filter */
function avail(allData,rowField,f,selfKey){
  const filterRow=r=>{
    if(f.periodo&&selfKey!=='periodo'&&r.Periodo!==f.periodo) return false;
    if(f.semana&&selfKey!=='semana'&&r.Semana!==f.semana) return false;
    if(f.vendedor&&selfKey!=='vendedor'&&r.Vendedor!==f.vendedor) return false;
    if(f.cliente&&selfKey!=='cliente'&&r.Nome_Fantasia!==f.cliente) return false;
    const q=(f.search||'').toLowerCase().trim();
    if(q){const hay=[r.Razao_Social,r.Nome_Fantasia,r.Vendedor,String(r.Nota_Fiscal||''),r.CNPJ_CPF].map(x=>String(x||'').toLowerCase()).join(' ');if(!hay.includes(q)) return false;}
    return true;
  };
  const vals=new Set();
  allData.filter(filterRow).forEach(r=>{const v=r[rowField];if(v!==undefined&&v!==''&&String(v)!=='nan') vals.add(String(v));});
  return [...vals].sort((a,b)=>a.localeCompare(b,'pt-BR'));
}
function copts(ph,available,selected){
  return '<option value="">'+ph+'</option>'+available.map(v=>'<option value="'+esc(v)+'"'+(v===selected?' selected':'')+'>'+esc(v)+'</option>').join('');
}
function setF(sec,k,v){
  F[sec][k]=v;
  if(k!=='search'){
    const src=sec==='vencidas'?D.vencidas:D.futuras;
    if(k!=='vendedor'){const av=avail(src,'Vendedor',F[sec],'vendedor');if(F[sec].vendedor&&!av.includes(F[sec].vendedor)) F[sec].vendedor='';}
    if(k!=='cliente'){const av=avail(src,'Nome_Fantasia',F[sec],'cliente');if(F[sec].cliente&&!av.includes(F[sec].cliente)) F[sec].cliente='';}
    if(sec==='vencidas'&&k!=='periodo'){const av=avail(src,'Periodo',F[sec],'periodo');if(F[sec].periodo&&!av.includes(F[sec].periodo)) F[sec].periodo='';}
    if(sec==='futuras'&&k!=='semana'){const avS=new Set(avail(src,'Semana',F[sec],'semana'));if(F[sec].semana&&!avS.has(F[sec].semana)) F[sec].semana='';}
  }
  activeTab=sec;renderTab();
}
function clrF(sec){Object.keys(F[sec]).forEach(k=>F[sec][k]='');Object.keys(SD[sec]).forEach(k=>SD[sec][k]='');renderTab();}
function setV(sec,v){V[sec]=v;renderTab();}

/* ── SEARCHABLE DROPDOWN (ss) ── */
const SD={vencidas:{vendedor:'',cliente:''},futuras:{vendedor:'',cliente:''}};
function filterSS(sec,key){
  const q=(SD[sec][key]||'').toLowerCase().trim();
  const sel=document.querySelector('[data-dds="'+sec+'-'+key+'"]');
  if(!sel) return;
  sel.querySelectorAll('option').forEach(o=>{if(!o.value) return; o.hidden=q&&!o.text.toLowerCase().includes(q);});
}
function setSS(sec,key,q){SD[sec][key]=q;filterSS(sec,key);}
function applySD(){
  ['vencidas','futuras'].forEach(sec=>['vendedor','cliente'].forEach(key=>{
    const inp=document.querySelector('[data-ddi="'+sec+'-'+key+'"]');
    if(inp) inp.value=SD[sec][key]||'';
    filterSS(sec,key);
  }));
}
function ssDd(sec,key,ph,available,selected){
  return '<span class="ss-wrap">'
    +'<span class="ss-lupa"><i class="bi bi-search"></i></span>'
    +'<input data-ddi="'+sec+'-'+key+'" class="ss-inp" type="text" placeholder="'+esc(ph)+'" oninput="setSS(\''+sec+'\',\''+key+'\',this.value)">'
    +'<select data-dds="'+sec+'-'+key+'" class="ss-sel" onchange="setF(\''+sec+'\',\''+key+'\',this.value)">'
    +copts('Todos',available,selected)
    +'</select></span>';
}
function setPeriodo(p){setF('vencidas','periodo',F.vencidas.periodo===p?'':p);}

/* ── TABLE BUILDERS ── */
function buildDetalhe(rows,id,cols,hdrs){
  const ths=hdrs.map((h,i)=>TH(h,i,id)).join('');
  const trs=rows.map(r=>{
    const tds=cols.map(c=>{
      const v=r[c]; const isN=NUM_COLS.has(c);
      let disp=v===''||v===null||v===undefined?'—':v;
      if((c==='A_Receber'||c==='Pago_Recebido')&&typeof v==='number') disp=R(v);
      const dv=isN?(parseFloat(v)||0):esc(String(v??''));
      return '<td class="'+(isN?'nr':'')+(c==='CNPJ_CPF'?' nowrap':'')+'" data-v="'+dv+'">'+esc(String(disp??''))+'</td>';
    }).join('');
    return '<tr>'+tds+'</tr>';
  }).join('');
  const totTds=cols.map((c,i)=>{
    if(c==='A_Receber') return '<td class="nr">'+R(sum(rows,c))+'</td>';
    if(c==='Pago_Recebido') return '<td class="nr">'+R(sum(rows,c))+'</td>';
    if(i===0) return '<td>TOTAL ('+rows.length+' títulos)</td>';
    return '<td></td>';
  }).join('');
  return '<div class="tbl-wrap"><table class="dt" id="'+id+'">'
    +'<thead><tr>'+ths+'</tr></thead>'
    +'<tbody>'+trs+'<tr class="tot">'+totTds+'</tr></tbody>'
    +'</table></div>';
}

function buildByCliente(data,pfx){
  const g=grp(data,'Nome_Fantasia');
  const rows=Object.entries(g).map(([c,rs])=>({c,cnpj:rs[0].CNPJ_CPF||'',n:rs.length,t:sum(rs,'A_Receber')})).sort((a,b)=>b.t-a.t);
  const id=pfx+'_cli';
  const ths=[TH('Cliente',0,id),TH('CNPJ',1,id),TH('Títulos',2,id),TH('Valor a Receber',3,id)].join('');
  const trs=rows.map(r=>'<tr>'
    +'<td data-v="'+esc(r.c)+'">'+esc(r.c)+'</td>'
    +'<td class="nowrap" data-v="'+esc(r.cnpj)+'">'+esc(r.cnpj)+'</td>'
    +'<td class="nr" data-v="'+r.n+'">'+r.n+'</td>'
    +'<td class="nr" data-v="'+r.t+'">'+R(r.t)+'</td></tr>').join('');
  return '<div class="tbl-wrap"><table class="dt" id="'+id+'">'
    +'<thead><tr>'+ths+'</tr></thead>'
    +'<tbody>'+trs
    +'<tr class="tot"><td>TOTAL ('+rows.length+' clientes)</td>'
    +'<td></td>'
    +'<td class="nr">'+rows.reduce((s,r)=>s+r.n,0)+'</td>'
    +'<td class="nr">'+R(sum(rows,'t'))+'</td></tr>'
    +'</tbody></table></div>';
}

function buildByVendedor(data,pfx){
  const g=grp(data,'Vendedor');
  const rows=Object.entries(g).map(([v,rs])=>({v,n:rs.length,t:sum(rs,'A_Receber')})).sort((a,b)=>b.t-a.t);
  const id=pfx+'_vnd';
  const ths=[TH('Vendedor',0,id),TH('Títulos',1,id),TH('Valor a Receber',2,id)].join('');
  const trs=rows.map(r=>'<tr>'
    +'<td data-v="'+esc(r.v)+'">'+esc(r.v)+'</td>'
    +'<td class="nr" data-v="'+r.n+'">'+r.n+'</td>'
    +'<td class="nr" data-v="'+r.t+'">'+R(r.t)+'</td></tr>').join('');
  return '<div class="tbl-wrap"><table class="dt" id="'+id+'">'
    +'<thead><tr>'+ths+'</tr></thead>'
    +'<tbody>'+trs
    +'<tr class="tot"><td>TOTAL ('+rows.length+' vendedores)</td>'
    +'<td class="nr">'+rows.reduce((s,r)=>s+r.n,0)+'</td>'
    +'<td class="nr">'+R(sum(rows,'t'))+'</td></tr>'
    +'</tbody></table></div>';
}

/* ── VENCIDAS ── */
function renderVencidas(){
  const f=F.vencidas, data=applyF(D.vencidas,'vencidas'), v=V.vencidas;

  const PC_COLORS=['#ef4444','#f97316','#eab308','#a855f7','#64748b'];
  const periodCards=D.periodos.map((p,i)=>{
    const all=D.vencidas.filter(r=>r.Periodo===p);
    const fil=data.filter(r=>r.Periodo===p);
    const sel=f.periodo===p?'sel':'';
    return '<div class="pc '+sel+'" onclick="setPeriodo(\''+esc(p)+'\')" style="border-left-color:'+PC_COLORS[i]+'">'
      +'<div class="pcl" style="color:'+PC_COLORS[i]+'">'+esc(p.split('(')[0].trim())+'</div>'
      +'<div class="pcc">'+esc(p.match(/\(.*\)/)?.[0]||'')+'</div>'
      +'<div class="pcv" style="color:'+PC_COLORS[i]+'">'+BRL(sum(fil,'A_Receber'))+'</div>'
      +'<div class="pcsub">'+fil.length+' títulos'+(f.vendedor||f.cliente?' filtrado':'')
      +(fil.length!==all.length?' · '+all.length+' total':'')+' </div>'
      +'</div>';
  }).join('');

  const vbs=['periodo','cliente','vendedor','detalhe'].map(vv=>{
    const lbl=vv==='periodo'?'Por Período':vv==='cliente'?'Por Cliente':vv==='vendedor'?'Por Vendedor':'Detalhado';
    return '<button class="vb'+(V.vencidas===vv?' act-d':'')+'" onclick="setV(\'vencidas\',\''+vv+'\')">'+lbl+'</button>';
  }).join('');

  let tbl='';
  if(v==='periodo') tbl=buildVencidasPeriodo(data);
  else if(v==='cliente') tbl=buildByCliente(data,'venc');
  else if(v==='vendedor') tbl=buildByVendedor(data,'venc');
  else tbl=buildDetalhe(data,'vd',
    ['Nome_Fantasia','CNPJ_CPF','Vendedor','Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber','Pago_Recebido','Dias_Atraso','Periodo'],
    ['Cliente','CNPJ','Vendedor','Vencimento','NF','Parcela','Valor a Receber','Pago','Dias Atraso','Período']);

  const hasF=Object.values(f).some(x=>x);
  const avP_set=new Set(avail(D.vencidas,'Periodo',f,'periodo'));
  const avP=D.periodos.filter(p=>avP_set.has(p));
  const avV=avail(D.vencidas,'Vendedor',f,'vendedor');
  const avC=avail(D.vencidas,'Nome_Fantasia',f,'cliente');
  document.getElementById('content').innerHTML=
    '<div class="card">'
    +'<div class="fbar">'
    +'<i class="bi bi-search" style="color:var(--dim)"></i>'
    +'<input class="fbar-search" type="text" placeholder="Buscar cliente, vendedor, NF..." value="'+esc(f.search||'')+'" oninput="setF(\'vencidas\',\'search\',this.value)">'
    +'<select onchange="setF(\'vencidas\',\'periodo\',this.value)">'+copts('— Todos os Períodos —',avP,f.periodo)+'</select>'
    +ssDd('vencidas','vendedor','Vendedor',avV,f.vendedor)
    +ssDd('vencidas','cliente','Cliente',avC,f.cliente)
    +(hasF?'<button class="fbar-reset" onclick="clrF(\'vencidas\')">✕ Limpar</button>':'')
    +'<span class="cnt-badge" style="margin-left:auto">'+data.length+' títulos · '+BRL(sum(data,'A_Receber'))+'</span>'
    +'</div>'
    +'<div class="period-grid">'+periodCards+'</div>'
    +'<div class="vbtns">'+vbs+'</div>'
    +tbl
    +'</div>';
  applySD();
}

function buildVencidasPeriodo(data){
  const byP={};
  D.periodos.forEach(p=>byP[p]=[]);
  data.forEach(r=>{if(r.Periodo&&byP[r.Periodo]) byP[r.Periodo].push(r);});
  let html='';
  D.periodos.forEach((p,i)=>{
    const rows=byP[p]; if(!rows.length) return;
    html+='<div style="margin-bottom:20px">'
      +'<div class="section-hdr">'
      +'<span class="badge-p bp'+i+'">'+esc(p)+'</span>'
      +'<span class="cnt-badge">'+rows.length+' títulos</span>'
      +'<span style="margin-left:auto;font-weight:700;color:var(--accent)">'+BRL(sum(rows,'A_Receber'))+'</span>'
      +'</div>'
      +buildDetalhe(rows,'vp'+i,
        ['Nome_Fantasia','CNPJ_CPF','Vendedor','Vencimento_fmt','Nota_Fiscal','A_Receber','Dias_Atraso'],
        ['Cliente','CNPJ','Vendedor','Vencimento','NF','Valor a Receber','Dias Atraso'])
      +'</div>';
  });
  return html||'<div class="empty">Nenhuma conta vencida encontrada.</div>';
}

/* ── HOJE ── */
function renderHoje(){
  const data=D.hoje, v=V.hoje;
  const vbs=['cliente','vendedor','detalhe'].map(vv=>{
    const lbl=vv==='cliente'?'Por Cliente':vv==='vendedor'?'Por Vendedor':'Detalhado';
    return '<button class="vb'+(V.hoje===vv?' act-h':'')+'" onclick="setV(\'hoje\',\''+vv+'\')">'+lbl+'</button>';
  }).join('');

  let tbl='';
  if(v==='cliente') tbl=buildByCliente(data,'hoje');
  else if(v==='vendedor') tbl=buildByVendedor(data,'hoje');
  else tbl=buildDetalhe(data,'hd',
    ['Nome_Fantasia','CNPJ_CPF','Vendedor','Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber','Pago_Recebido'],
    ['Cliente','CNPJ','Vendedor','Vencimento','NF','Parcela','Valor a Receber','Pago']);

  document.getElementById('content').innerHTML=
    '<div class="card">'
    +'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px">'
    +'<div class="kpi"><div class="lbl">Vencem Hoje</div>'
    +'<div class="val" style="color:#f59e0b">'+BRL(sum(data,'A_Receber'))+'</div>'
    +'<div class="cnt">'+data.length+' título'+(data.length!==1?'s':'')+'</div></div>'
    +'<div class="kpi"><div class="lbl">Clientes</div>'
    +'<div class="val" style="color:#3b82f6">'+Object.keys(grp(data,"Razao_Social")).length+'</div>'
    +'<div class="cnt">distintos</div></div>'
    +'<div class="kpi"><div class="lbl">Vendedores</div>'
    +'<div class="val" style="color:#10b981">'+Object.keys(grp(data,"Vendedor")).length+'</div>'
    +'<div class="cnt">distintos</div></div>'
    +'</div>'
    +'<div class="vbtns">'+vbs+'</div>'
    +tbl+'</div>';
}

/* ── FUTURAS ── */
function renderFuturas(){
  const f=F.futuras, data=applyF(D.futuras,'futuras'), v=V.futuras;
  const vbs=['semana','cliente','vendedor','detalhe'].map(vv=>{
    const lbl=vv==='semana'?'Por Semana':vv==='cliente'?'Por Cliente':vv==='vendedor'?'Por Vendedor':'Detalhado';
    return '<button class="vb'+(V.futuras===vv?' act-f':'')+'" onclick="setV(\'futuras\',\''+vv+'\')">'+lbl+'</button>';
  }).join('');

  let tbl='';
  if(v==='semana') tbl=buildBySemana(data);
  else if(v==='cliente') tbl=buildByCliente(data,'fut');
  else if(v==='vendedor') tbl=buildByVendedor(data,'fut');
  else tbl=buildDetalhe(data,'fd',
    ['Nome_Fantasia','CNPJ_CPF','Vendedor','Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber','Semana'],
    ['Cliente','CNPJ','Vendedor','Vencimento','NF','Parcela','Valor a Receber','Semana']);

  const hasF=Object.values(f).some(x=>x);
  const avS_set=new Set(avail(D.futuras,'Semana',f,'semana'));
  const avS=D.semanas.filter(s=>avS_set.has(s));
  const avV=avail(D.futuras,'Vendedor',f,'vendedor');
  const avC=avail(D.futuras,'Nome_Fantasia',f,'cliente');
  document.getElementById('content').innerHTML=
    '<div class="card">'
    +'<div class="fbar">'
    +'<i class="bi bi-search" style="color:var(--dim)"></i>'
    +'<input class="fbar-search" type="text" placeholder="Buscar cliente, vendedor, NF..." value="'+esc(f.search||'')+'" oninput="setF(\'futuras\',\'search\',this.value)">'
    +'<select onchange="setF(\'futuras\',\'semana\',this.value)">'+copts('— Todas as Semanas —',avS,f.semana)+'</select>'
    +ssDd('futuras','vendedor','Vendedor',avV,f.vendedor)
    +ssDd('futuras','cliente','Cliente',avC,f.cliente)
    +(hasF?'<button class="fbar-reset" onclick="clrF(\'futuras\')">✕ Limpar</button>':'')
    +'<span class="cnt-badge" style="margin-left:auto">'+data.length+' títulos · '+BRL(sum(data,'A_Receber'))+'</span>'
    +'</div>'
    +'<div class="vbtns">'+vbs+'</div>'
    +tbl+'</div>';
  applySD();
}

function buildBySemana(data){
  const g=grp(data,'Semana');
  const semanas=D.semanas.filter(s=>g[s]&&g[s].length);
  if(!semanas.length) return '<div class="empty">Nenhum registro encontrado.</div>';
  return semanas.map((s,i)=>{
    const rows=g[s];
    return '<div style="margin-bottom:20px">'
      +'<div class="section-hdr">'
      +'<span class="wk"><i class="bi bi-calendar3 me-1"></i>'+esc(s)+'</span>'
      +'<span class="cnt-badge">'+rows.length+' títulos</span>'
      +'<span style="margin-left:auto;font-weight:700;color:var(--green)">'+BRL(sum(rows,'A_Receber'))+'</span>'
      +'</div>'
      +buildDetalhe(rows,'sw'+i,
        ['Nome_Fantasia','CNPJ_CPF','Vendedor','Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber'],
        ['Cliente','CNPJ','Vendedor','Vencimento','NF','Parcela','Valor a Receber'])
      +'</div>';
  }).join('');
}

/* ── INIT ── */
renderKPIs();
initNav();
renderVencidas();
</script>
</body>
</html>
"""

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    excel_path  = sys.argv[1] if len(sys.argv) > 1 else INPUT_DEFAULT
    output_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_DEFAULT

    print(f"Lendo: {excel_path}")
    data = process_excel(excel_path)
    print(f"Registros: {len(data['vencidas'])} vencidas | {len(data['hoje'])} hoje | {len(data['futuras'])} futuras")

    html = build_html(data)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Dashboard salvo: {output_path}")

if __name__ == '__main__':
    main()
