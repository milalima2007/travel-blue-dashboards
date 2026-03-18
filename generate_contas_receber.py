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
        'clientes'  : uniq(df['Razao_Social']),
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
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
:root{--tb:#003087;--tb2:#004dcc;--c0:#e74c3c;--c1:#e67e22;--c2:#d4ac0d;--c3:#8e44ad;--c4:#555;
  --bg0:#fde8e8;--bg1:#fef0e0;--bg2:#fefbe0;--bg3:#f0e0f8;--bg4:#e8e8e8;}
body{background:#f0f2f5;font-family:'Segoe UI',Arial,sans-serif;font-size:.86rem;}
.topbar{background:var(--tb);padding:10px 20px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,.3);}
.topbar .brand{color:#fff;font-size:1.1rem;font-weight:700;letter-spacing:.3px;}
.topbar .sub{color:rgba(255,255,255,.55);font-size:.78rem;}
.kpi-wrap{display:flex;flex-wrap:wrap;gap:12px;padding:16px 20px;}
.kpi{background:#fff;border-radius:10px;padding:14px 18px;flex:1 1 180px;display:flex;align-items:center;gap:12px;
  box-shadow:0 2px 8px rgba(0,0,0,.07);border-left:5px solid;}
.kpi .ico{font-size:1.9rem;}
.kpi .lbl{font-size:.7rem;text-transform:uppercase;letter-spacing:.5px;color:#777;}
.kpi .val{font-size:1.3rem;font-weight:700;}
.kpi .cnt{font-size:.72rem;color:#999;}
.main-nav{display:flex;gap:0;padding:0 20px;border-bottom:2px solid #dee2e6;background:#fff;}
.main-nav button{border:none;background:none;padding:10px 20px;font-size:.88rem;font-weight:500;
  color:#555;border-bottom:3px solid transparent;cursor:pointer;transition:color .2s;}
.main-nav button.active{color:var(--tb);border-bottom-color:var(--tb);font-weight:700;}
.main-nav button:hover:not(.active){color:var(--tb2);}
.content{padding:16px 20px;}
.panel{background:#fff;border-radius:10px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:16px;}
.fbar{background:#f7f8fa;border-radius:8px;padding:10px 14px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px;}
.fbar select{font-size:.82rem;padding:4px 8px;border-radius:6px;border:1px solid #ccc;max-width:240px;}
.vbtns{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap;}
.vbtns .vb{border:1px solid #ccc;background:#fff;border-radius:6px;padding:4px 14px;font-size:.8rem;cursor:pointer;transition:background .15s,color .15s;}
.vbtns .vb.active-d{background:#c0392b;color:#fff;border-color:#c0392b;}
.vbtns .vb.active-h{background:#e67e22;color:#fff;border-color:#e67e22;}
.vbtns .vb.active-f{background:#27ae60;color:#fff;border-color:#27ae60;}
.vbtns .vb:hover:not(.active-d):not(.active-h):not(.active-f){background:#f0f0f0;}
.period-grid{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px;}
.pc{flex:1 1 150px;border-radius:8px;padding:12px 14px;cursor:pointer;transition:transform .15s,box-shadow .15s;border:2px solid transparent;}
.pc:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.13);}
.pc.sel{border-color:var(--tb);}
.pc .pcl{font-size:.7rem;font-weight:700;text-transform:uppercase;margin-bottom:4px;}
.pc .pcv{font-size:1.15rem;font-weight:700;}
.pc .pcc{font-size:.75rem;color:#555;margin:3px 0;}
.tbl-wrap{overflow-x:auto;}
table.dt{width:100%;border-collapse:collapse;font-size:.82rem;}
table.dt thead th{background:var(--tb);color:#fff;padding:8px 10px;text-align:left;
  cursor:pointer;white-space:nowrap;user-select:none;}
table.dt thead th:hover{background:var(--tb2);}
table.dt tbody td{padding:6px 10px;border-bottom:1px solid #eee;}
table.dt tbody tr:hover td{background:#f0f6ff;}
table.dt tbody tr.tot td{background:#e8f0fe;font-weight:700;border-top:2px solid var(--tb);}
.nr{text-align:right;}
.sa{font-size:.65rem;margin-left:3px;opacity:.6;}
.badge-p{display:inline-block;padding:2px 8px;border-radius:20px;font-size:.72rem;font-weight:600;}
.bp0{background:var(--bg0);color:var(--c0);}
.bp1{background:var(--bg1);color:var(--c1);}
.bp2{background:var(--bg2);color:var(--c2);}
.bp3{background:var(--bg3);color:var(--c3);}
.bp4{background:var(--bg4);color:var(--c4);}
.wk{display:inline-block;background:#e3f2fd;color:#1565c0;padding:3px 10px;border-radius:20px;font-size:.78rem;font-weight:600;}
.cnt-badge{background:#e8f0fe;color:var(--tb);border-radius:20px;padding:2px 10px;font-size:.76rem;font-weight:600;}
.section-hdr{display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;}
.empty{text-align:center;color:#aaa;padding:32px 0;font-size:.9rem;}
footer{text-align:center;color:#bbb;font-size:.75rem;padding:16px;border-top:1px solid #e5e5e5;margin-top:8px;}
@media(max-width:600px){.kpi{flex:1 1 140px;}.pc{flex:1 1 130px;}}
</style>
</head>
<body>

<div class="topbar">
  <span class="brand"><i class="bi bi-cash-stack me-2"></i>Contas a Receber – Travel Blue</span>
  <span class="sub">Gerado em __GERADO_EM__</span>
</div>

<div class="kpi-wrap" id="kpis"></div>

<div class="main-nav" id="nav">
  <button class="active" data-t="vencidas"><i class="bi bi-exclamation-triangle-fill text-danger me-1"></i>Contas Vencidas</button>
  <button data-t="hoje"><i class="bi bi-clock-fill text-warning me-1"></i>Vencem Hoje</button>
  <button data-t="futuras"><i class="bi bi-calendar-check-fill text-success me-1"></i>Contas Futuras</button>
</div>

<div class="content" id="content"></div>

<footer>Travel Blue Brasil · Dashboard Contas a Receber · Dados processados automaticamente</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
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
    {l:'Total Vencido',v:BRL(tv),c:'#e74c3c',ico:'bi-exclamation-triangle-fill',n:D.vencidas.length},
    {l:'Vence Hoje',v:BRL(th2),c:'#e67e22',ico:'bi-clock-fill',n:D.hoje.length},
    {l:'A Receber (Futuro)',v:BRL(tf),c:'#27ae60',ico:'bi-calendar-check-fill',n:D.futuras.length},
    {l:'Total Geral',v:BRL(tot),c:'#2980b9',ico:'bi-bank',n:D.vencidas.length+D.hoje.length+D.futuras.length},
  ];
  document.getElementById('kpis').innerHTML=ks.map(k=>
    '<div class="kpi" style="border-left-color:'+k.c+'">'
    +'<i class="bi '+k.ico+' ico" style="color:'+k.c+'"></i>'
    +'<div><div class="lbl">'+k.l+'</div>'
    +'<div class="val" style="color:'+k.c+'">'+k.v+'</div>'
    +'<div class="cnt">'+k.n+' título'+(k.n!==1?'s':'')+'</div></div></div>'
  ).join('');
}

/* ── STATE ── */
let activeTab='vencidas';
const F={vencidas:{periodo:'',vendedor:'',cliente:''},futuras:{semana:'',vendedor:'',cliente:''}};
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
  const f=F[section];
  return data.filter(r=>
    (!f.periodo||r.Periodo===f.periodo)&&
    (!f.semana ||r.Semana===f.semana)&&
    (!f.vendedor||r.Vendedor===f.vendedor)&&
    (!f.cliente||r.Razao_Social===f.cliente)
  );
}
function setF(sec,k,v){F[sec][k]=v;activeTab=sec;renderTab();}
function clrF(sec){Object.keys(F[sec]).forEach(k=>F[sec][k]='');renderTab();}
function setV(sec,v){V[sec]=v;renderTab();}
function setPeriodo(p){F.vencidas.periodo=F.vencidas.periodo===p?'':p;renderVencidas();}

/* ── TABLE BUILDERS ── */
function buildDetalhe(rows,id,cols,hdrs){
  const ths=hdrs.map((h,i)=>TH(h,i,id)).join('');
  const trs=rows.map(r=>{
    const tds=cols.map(c=>{
      const v=r[c]; const isN=NUM_COLS.has(c);
      let disp=v===''||v===null||v===undefined?'—':v;
      if((c==='A_Receber'||c==='Pago_Recebido')&&typeof v==='number') disp=R(v);
      const dv=isN?(parseFloat(v)||0):esc(String(v??''));
      return '<td class="'+(isN?'nr':'')+'" data-v="'+dv+'">'+esc(String(disp??''))+'</td>';
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
  const g=grp(data,'Razao_Social');
  const rows=Object.entries(g).map(([c,rs])=>({c,n:rs.length,t:sum(rs,'A_Receber')})).sort((a,b)=>b.t-a.t);
  const id=pfx+'_cli';
  const ths=[TH('Razão Social',0,id),TH('Títulos',1,id),TH('Valor a Receber',2,id)].join('');
  const trs=rows.map(r=>'<tr>'
    +'<td data-v="'+esc(r.c)+'">'+esc(r.c)+'</td>'
    +'<td class="nr" data-v="'+r.n+'">'+r.n+'</td>'
    +'<td class="nr" data-v="'+r.t+'">'+R(r.t)+'</td></tr>').join('');
  return '<div class="tbl-wrap"><table class="dt" id="'+id+'">'
    +'<thead><tr>'+ths+'</tr></thead>'
    +'<tbody>'+trs
    +'<tr class="tot"><td>TOTAL ('+rows.length+' clientes)</td>'
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

  const periodCards=D.periodos.map((p,i)=>{
    const all=D.vencidas.filter(r=>r.Periodo===p);
    const fil=data.filter(r=>r.Periodo===p);
    const sel=f.periodo===p?'sel':'';
    return '<div class="pc pc-'+i+' '+sel+'" onclick="setPeriodo(\''+esc(p)+'\')" style="background:var(--bg'+i+')">'
      +'<div class="pcl" style="color:var(--c'+i+')">'+esc(p.split('(')[0].trim())+'</div>'
      +'<div class="pcc">'+esc(p.match(/\(.*\)/)?.[0]||'')+'</div>'
      +'<div class="pcv" style="color:var(--c'+i+')">'+BRL(sum(fil,'A_Receber'))+'</div>'
      +'<div style="font-size:.71rem;color:#888">'+fil.length+' títulos'+(f.vendedor||f.cliente?' filtrado':'')
      +(fil.length!==all.length?' · '+all.length+' total':'')+' </div>'
      +'</div>';
  }).join('');

  const vbs=['periodo','cliente','vendedor','detalhe'].map(vv=>{
    const lbl=vv==='periodo'?'Por Período':vv==='cliente'?'Por Cliente':vv==='vendedor'?'Por Vendedor':'Detalhado';
    return '<button class="vb'+(V.vencidas===vv?' active-d':'')+'" onclick="setV(\'vencidas\',\''+vv+'\')">'+lbl+'</button>';
  }).join('');

  let tbl='';
  if(v==='periodo') tbl=buildVencidasPeriodo(data);
  else if(v==='cliente') tbl=buildByCliente(data,'venc');
  else if(v==='vendedor') tbl=buildByVendedor(data,'venc');
  else tbl=buildDetalhe(data,'vd',
    ['Razao_Social','Vendedor','Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber','Pago_Recebido','Dias_Atraso','Periodo'],
    ['Razão Social','Vendedor','Vencimento','NF','Parcela','Valor a Receber','Pago','Dias Atraso','Período']);

  const hasF=Object.values(f).some(x=>x);
  document.getElementById('content').innerHTML=
    '<div class="panel">'
    +'<div class="fbar">'
    +'<i class="bi bi-funnel-fill text-secondary"></i>'
    +'<select onchange="setF(\'vencidas\',\'periodo\',this.value)">'+opts(D.periodos,'— Todos os Períodos —')+'</select>'
    +'<select onchange="setF(\'vencidas\',\'vendedor\',this.value)">'+opts(D.vendedores,'— Todos os Vendedores —')+'</select>'
    +'<select onchange="setF(\'vencidas\',\'cliente\',this.value)">'+opts(D.clientes,'— Todos os Clientes —')+'</select>'
    +(hasF?'<button class="btn btn-sm btn-outline-danger" onclick="clrF(\'vencidas\')"><i class="bi bi-x-circle me-1"></i>Limpar</button>':'')
    +'<span class="cnt-badge ms-auto">'+data.length+' títulos · '+BRL(sum(data,'A_Receber'))+'</span>'
    +'</div>'
    +'<div class="period-grid">'+periodCards+'</div>'
    +'<div class="vbtns">'+vbs+'</div>'
    +tbl
    +'</div>';

  const sels=document.querySelectorAll('#content .fbar select');
  const ks=['periodo','vendedor','cliente'];
  sels.forEach((s,i)=>{if(ks[i]) s.value=f[ks[i]]||'';});
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
      +'<span class="ms-auto fw-bold">'+BRL(sum(rows,'A_Receber'))+'</span>'
      +'</div>'
      +buildDetalhe(rows,'vp'+i,
        ['Razao_Social','Vendedor','Vencimento_fmt','Nota_Fiscal','A_Receber','Dias_Atraso'],
        ['Razão Social','Vendedor','Vencimento','NF','Valor a Receber','Dias Atraso'])
      +'</div>';
  });
  return html||'<div class="empty">Nenhuma conta vencida encontrada.</div>';
}

/* ── HOJE ── */
function renderHoje(){
  const data=D.hoje, v=V.hoje;
  const vbs=['cliente','vendedor','detalhe'].map(vv=>{
    const lbl=vv==='cliente'?'Por Cliente':vv==='vendedor'?'Por Vendedor':'Detalhado';
    return '<button class="vb'+(V.hoje===vv?' active-h':'')+'" onclick="setV(\'hoje\',\''+vv+'\')">'+lbl+'</button>';
  }).join('');

  let tbl='';
  if(v==='cliente') tbl=buildByCliente(data,'hoje');
  else if(v==='vendedor') tbl=buildByVendedor(data,'hoje');
  else tbl=buildDetalhe(data,'hd',
    ['Razao_Social','Vendedor','Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber','Pago_Recebido'],
    ['Razão Social','Vendedor','Vencimento','NF','Parcela','Valor a Receber','Pago']);

  document.getElementById('content').innerHTML=
    '<div class="panel">'
    +'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px">'
    +'<div class="kpi" style="border-left-color:#e67e22;flex:0 1 260px">'
    +'<i class="bi bi-clock-fill ico" style="color:#e67e22"></i>'
    +'<div><div class="lbl">Vencem Hoje</div>'
    +'<div class="val" style="color:#e67e22">'+BRL(sum(data,'A_Receber'))+'</div>'
    +'<div class="cnt">'+data.length+' título'+(data.length!==1?'s':'')+'</div></div></div>'
    +'</div>'
    +'<div class="vbtns">'+vbs+'</div>'
    +tbl+'</div>';
}

/* ── FUTURAS ── */
function renderFuturas(){
  const f=F.futuras, data=applyF(D.futuras,'futuras'), v=V.futuras;
  const vbs=['semana','cliente','vendedor','detalhe'].map(vv=>{
    const lbl=vv==='semana'?'Por Semana':vv==='cliente'?'Por Cliente':vv==='vendedor'?'Por Vendedor':'Detalhado';
    return '<button class="vb'+(V.futuras===vv?' active-f':'')+'" onclick="setV(\'futuras\',\''+vv+'\')">'+lbl+'</button>';
  }).join('');

  let tbl='';
  if(v==='semana') tbl=buildBySemana(data);
  else if(v==='cliente') tbl=buildByCliente(data,'fut');
  else if(v==='vendedor') tbl=buildByVendedor(data,'fut');
  else tbl=buildDetalhe(data,'fd',
    ['Razao_Social','Vendedor','Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber','Semana'],
    ['Razão Social','Vendedor','Vencimento','NF','Parcela','Valor a Receber','Semana']);

  const hasF=Object.values(f).some(x=>x);
  document.getElementById('content').innerHTML=
    '<div class="panel">'
    +'<div class="fbar">'
    +'<i class="bi bi-funnel-fill text-secondary"></i>'
    +'<select onchange="setF(\'futuras\',\'semana\',this.value)">'+opts(D.semanas,'— Todas as Semanas —')+'</select>'
    +'<select onchange="setF(\'futuras\',\'vendedor\',this.value)">'+opts(D.vendedores,'— Todos os Vendedores —')+'</select>'
    +'<select onchange="setF(\'futuras\',\'cliente\',this.value)">'+opts(D.clientes,'— Todos os Clientes —')+'</select>'
    +(hasF?'<button class="btn btn-sm btn-outline-danger" onclick="clrF(\'futuras\')"><i class="bi bi-x-circle me-1"></i>Limpar</button>':'')
    +'<span class="cnt-badge ms-auto">'+data.length+' títulos · '+BRL(sum(data,'A_Receber'))+'</span>'
    +'</div>'
    +'<div class="vbtns">'+vbs+'</div>'
    +tbl+'</div>';

  const sels=document.querySelectorAll('#content .fbar select');
  const ks=['semana','vendedor','cliente'];
  sels.forEach((s,i)=>{if(ks[i]) s.value=f[ks[i]]||'';});
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
      +'<span class="ms-auto fw-bold text-success">'+BRL(sum(rows,'A_Receber'))+'</span>'
      +'</div>'
      +buildDetalhe(rows,'sw'+i,
        ['Razao_Social','Vendedor','Vencimento_fmt','Nota_Fiscal','Parcela','A_Receber'],
        ['Razão Social','Vendedor','Vencimento','NF','Parcela','Valor a Receber'])
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
