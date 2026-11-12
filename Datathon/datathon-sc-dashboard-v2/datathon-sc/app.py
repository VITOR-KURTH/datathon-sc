"""Dashboard - Raio-X do Mercado de Trabalho e Vagas Industriais em Santa Catarina.

Rodar:   streamlit run app.py
Dados:   python src/01_ingestao_join.py <csv>  ->  python src/03_cubo_dashboard.py
Textos:  data/contexto.json (contexto, casos por município e recomendações; editável sem mexer no código)
"""
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).parent
DATA = ROOT / "data/processed"
st.set_page_config(page_title="Raio-X do Mercado de Trabalho Industrial · SC", page_icon="🏭", layout="wide")

# ============================================================== Tokens (paleta validada: skill dataviz)
INK, INK2, MUTED = "#0a0a0a", "#404040", "#616161"  # tinta / ferro / cinza (ficha técnica)
GRID, AXIS = "#ececea", "#0a0a0a"
BLUE, ORANGE, RED, NEG = "#2a78d6", "#eb6834", "#a32d2d", "#e34948"
GRAY_EST, GRAY_NA = "#cfcfcb", "#ececea"
DIVERGENTE = [[0, "#7f1f1f"], [0.25, "#d34a47"], [0.45, "#f3c4c2"], [0.5, "#f4f4f5"],
              [0.55, "#b7d3f6"], [0.75, "#2a78d6"], [1, "#104281"]]
SEQ_AZUL = [[0, "#cde2fb"], [0.5, "#3987e5"], [1, "#0d366b"]]
DIAG_CORES = {"Expansão acelerada": BLUE, "Alta rotatividade": ORANGE, "Retração": RED,
              "Estável": GRAY_EST, "Dados insuficientes": GRAY_NA}
FONT = '"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
# Rótulos de referência no mapa: (lat, lon, posição do texto)
CIDADES = {"Joinville": (-26.273, -48.996, "middle right"), "Blumenau": (-26.864, -49.098, "middle left"),
           "Navegantes": (-26.826, -48.73, "middle right"), "Florianópolis": (-27.614, -48.492, "middle right"),
           "Criciúma": (-28.718, -49.387, "middle left"), "Lages": (-27.96, -50.353, "middle right"),
           "Mafra": (-26.215, -49.878, "top center"), "Joaçaba": (-27.152, -51.587, "bottom center"),
           "Chapecó": (-27.116, -52.661, "bottom center"), "São Miguel do Oeste": (-26.728, -53.509, "top right")}

INDUSTRIA_AMPLA, INDUSTRIA_ESTRITA = list("BCDEF"), list("BCDE")
ORDEM_GRAU = ["Até fundamental", "Médio", "Superior incompleto", "Superior completo", "Pós-graduação"]
TICK_GRAU = ["Até<br>fundamental", "Médio", "Superior<br>incompleto", "Superior<br>completo", "Pós-<br>graduação"]
MEDIDAS = ["adm", "des", "des_pedido", "sal_adm_sum", "sal_adm_n", "sal_des_sum", "sal_des_n", "idade_adm_sum", "idade_adm_n"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
DIV = {
    "01": "Agropecuária", "02": "Produção florestal", "03": "Pesca e aquicultura", "05": "Extração de carvão",
    "06": "Petróleo e gás", "07": "Minerais metálicos", "08": "Extração de minerais não metálicos", "09": "Apoio à extração",
    "10": "Alimentos", "11": "Bebidas", "12": "Fumo", "13": "Têxtil", "14": "Vestuário", "15": "Couro e calçados",
    "16": "Madeira", "17": "Papel e celulose", "18": "Gráficas", "19": "Derivados de petróleo", "20": "Químicos",
    "21": "Farmacêuticos", "22": "Borracha e plástico", "23": "Cerâmica e minerais não metálicos", "24": "Metalurgia",
    "25": "Produtos de metal", "26": "Eletrônicos e informática", "27": "Materiais elétricos", "28": "Máquinas e equipamentos",
    "29": "Veículos e autopeças", "30": "Naval e outros transportes", "31": "Móveis", "32": "Produtos diversos",
    "33": "Manutenção de máquinas", "35": "Eletricidade e gás", "36": "Água", "37": "Esgoto", "38": "Resíduos",
    "39": "Descontaminação", "41": "Construção de edifícios", "42": "Obras de infraestrutura", "43": "Serviços de construção",
    "45": "Comércio de veículos", "46": "Comércio atacadista", "47": "Comércio varejista", "49": "Transporte terrestre",
    "50": "Transporte aquaviário", "51": "Transporte aéreo", "52": "Armazenagem e logística", "53": "Correios e entregas",
    "55": "Alojamento", "56": "Restaurantes e alimentação", "58": "Edição", "59": "Audiovisual", "60": "Rádio e TV",
    "61": "Telecomunicações", "62": "Tecnologia da informação", "63": "Serviços de informação", "64": "Serviços financeiros",
    "65": "Seguros", "66": "Auxiliares financeiros", "68": "Imobiliárias", "69": "Jurídico e contabilidade",
    "70": "Consultoria e gestão", "71": "Engenharia e arquitetura", "72": "Pesquisa e desenvolvimento", "73": "Publicidade",
    "74": "Outras atividades técnicas", "75": "Veterinária", "77": "Aluguéis", "78": "Agências de mão de obra",
    "79": "Agências de viagem", "80": "Vigilância", "81": "Serviços para edifícios", "82": "Apoio administrativo",
    "84": "Administração pública", "85": "Educação", "86": "Saúde", "87": "Assistência com alojamento",
    "88": "Assistência social", "90": "Artes e espetáculos", "91": "Patrimônio cultural", "92": "Jogos",
    "93": "Esporte e lazer", "94": "Associações", "95": "Reparação de equipamentos", "96": "Serviços pessoais",
    "97": "Serviços domésticos", "99": "Organismos internacionais",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');
/* ================= Ficha técnica industrial
   Referências (styles.refero.design): Freitag (grade de linhas que se tocam, rótulos mono maiúsculos, sem sombras),
   teenage engineering (cantos 0, faixa Carbon, âmbar de alerta), Browserbase (um marca-texto por título, metadados mono). */
:root{
  --paper:#f5f5f2;--sheet:#ffffff;--ink:#0a0a0a;--iron:#404040;--ash:#616161;--concrete:#cacaca;--mist:#ececea;
  --carbon:#0f0e12;--caution:#ffdd00;--accent:#2a78d6;
  --sans:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;--display:"Space Grotesk","IBM Plex Sans",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,monospace;--spring:cubic-bezier(.32,1.36,.56,1);
}
.stMarkdown{font-family:var(--sans)}
/* papel milimetrado: grade de 24px quase invisível */
.stApp{background-color:var(--paper);
  background-image:linear-gradient(rgba(10,10,10,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(10,10,10,.035) 1px,transparent 1px);
  background-size:24px 24px}
.block-container{padding-top:4.6rem;padding-bottom:3rem;max-width:1320px}
[data-testid="stSidebar"]{border-right:1px solid var(--ink)}
[data-testid="stSidebar"] h3{font-family:var(--mono);font-size:.7rem;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:var(--ink);
  border-bottom:1px solid var(--ink);padding-bottom:.4rem}
[data-testid="stExpander"] details{border:1px solid var(--ink);border-radius:0;background:var(--sheet)}
[data-testid="stExpander"] summary{font-family:var(--mono);font-size:.78rem;letter-spacing:.06em;text-transform:uppercase}
[data-testid="stCaptionContainer"]{color:var(--ash)}
[data-testid="stPlotlyChart"]{background:var(--sheet);border:1px solid var(--concrete);padding:6px 4px 2px}
/* rótulo do seletor do mapa e do Raio-X no estilo de campo de ficha */
[data-testid="stWidgetLabel"] p{font-family:var(--mono);font-size:.7rem!important;letter-spacing:.1em;text-transform:uppercase;color:var(--iron)}

/* ---- Dynamic Island (cult-ui): placa de status preta, expande com spring ao passar o mouse */
.island{position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:1000001;
  background:var(--carbon);color:#fafafa;border-radius:22px;box-shadow:0 10px 30px -10px rgba(0,0,0,.5);
  width:min(460px,calc(100vw - 32px));max-height:40px;overflow:hidden;cursor:default;
  transition:width .55s var(--spring),max-height .55s var(--spring),border-radius .4s ease}
.island:hover,.island:focus-within{width:min(640px,calc(100vw - 32px));max-height:260px;border-radius:26px}
.island .cmp{display:flex;align-items:center;gap:10px;height:40px;padding:0 16px;font-family:var(--mono);font-size:.74rem;letter-spacing:.04em;white-space:nowrap}
.island .dot{width:8px;height:8px;background:var(--caution);flex:none;animation:blink 1.6s steps(2,start) infinite}
@keyframes blink{to{visibility:hidden}}
.island .lbl{color:#a3a3a3;text-transform:uppercase;overflow:hidden;text-overflow:ellipsis}
.island .sep{flex:1}
.island .num{font-weight:600;font-variant-numeric:tabular-nums}
.island .num.pos{color:var(--caution)}.island .num.neg{color:#ff6b5e}
.island .exp{opacity:0;transform:translateY(-4px);padding:0 16px 14px;transition:opacity .25s ease,transform .45s var(--spring)}
.island:hover .exp,.island:focus-within .exp{opacity:1;transform:none;transition-delay:.08s}
.island .grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid #2c2c30;border-left:1px solid #2c2c30}
.island .cell{border-right:1px solid #2c2c30;border-bottom:1px solid #2c2c30;padding:9px 12px}
.island .cell .k{font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:#8a8a8a}
.island .cell .v{font-family:var(--display);font-size:1.2rem;font-weight:600;margin-top:2px;font-variant-numeric:tabular-nums}
.island .links{display:flex;gap:0;margin-top:10px;border:1px solid #2c2c30}
.island .links a{flex:1;text-align:center;font-family:var(--mono);font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:#d4d4d4;
  text-decoration:none;padding:6px 4px;border-right:1px solid #2c2c30;transition:background .15s,color .15s}
.island .links a:last-child{border-right:none}
.island .links a:hover{background:var(--caution);color:var(--ink)}

/* ---- carimbo da prancha (title block de desenho técnico) */
.tblock{display:grid;grid-template-columns:1.1fr 1fr 1.1fr 1.6fr;border:1px solid var(--ink);background:var(--sheet);margin-bottom:1.6rem}
.tblock div{padding:7px 12px 8px;border-right:1px solid var(--ink);font-family:var(--mono);font-size:.78rem;color:var(--ink);font-weight:500}
.tblock div:last-child{border-right:none}
.tblock span{display:block;font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ash);font-weight:400;margin-bottom:1px}
.hero-title{font-family:var(--display);font-size:3.2rem;font-weight:600;line-height:1.02;color:var(--ink);margin:0 0 1rem;letter-spacing:-.035em;max-width:24ch}
.hero-title mark{white-space:nowrap;background:var(--caution);color:var(--ink);padding:0 .12em;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.hero-lead{font-size:1.1rem;line-height:1.65;color:var(--iron);max-width:74ch;margin:.2rem 0 1.4rem;padding-left:16px;border-left:2px solid var(--ink)}
.hero-lead b{color:var(--ink);font-weight:600}
/* nav = régua de seções */
.nav{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid var(--ink);margin:0 0 1.6rem;background:var(--sheet)}
.nav a{display:flex;align-items:baseline;gap:10px;font-size:.88rem;font-weight:500;text-decoration:none;color:var(--ink);padding:10px 14px;
  border-right:1px solid var(--ink);transition:background .15s}
.nav a:last-child{border-right:none}
.nav a b{font-family:var(--mono);font-size:.72rem;font-weight:500;color:var(--ash)}
.nav a:hover{background:var(--caution)}
.nav a:hover b{color:var(--ink)}

/* ---- KPIs: linha principal = faixa Carbon; demais = grade de células que se tocam */
.kpis{display:grid;gap:1px;background:var(--concrete);border:1px solid var(--concrete);margin-bottom:16px}
.kpis.k3{grid-template-columns:repeat(3,minmax(0,1fr));background:#2c2c30;border-color:var(--carbon);margin-bottom:0}
.kpis.k4{grid-template-columns:repeat(4,minmax(0,1fr))}
.kpi{background:var(--sheet);padding:14px 18px 16px;transition:background .15s}
.kpi:hover{background:#fffbe0}
.kpi .bar{display:none}
.kpi .lbl{font-family:var(--mono);font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ash);font-weight:500}
.kpi .val{font-family:var(--display);font-size:1.7rem;font-weight:600;color:var(--ink);line-height:1.15;margin-top:6px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:.78rem;color:var(--ash);margin-top:3px}
.kpi.main{background:var(--carbon);padding:18px 22px 20px}
.kpi.main:hover{background:#18171c}
.kpi.main .lbl{color:#a3a3a3;display:flex;align-items:center;gap:8px}
.kpi.main .lbl::before{content:"";width:8px;height:8px;background:var(--caution);flex:none}
.kpi.main .val{color:#fff;font-size:2.7rem;letter-spacing:-.04em}
.kpi.main .sub{color:#8a8a8a}

/* ---- capítulos: régua grossa + número de seção */
.chap{display:flex;align-items:baseline;gap:1rem;margin:3rem 0 .1rem;padding-top:.9rem;border-top:3px solid var(--ink)}
.chap .n{font-family:var(--mono);font-weight:500;font-size:.9rem;color:var(--ink);flex:none;background:var(--caution);padding:1px 7px}
.chap .t{font-family:var(--display);font-size:2rem;font-weight:600;color:var(--ink);letter-spacing:-.03em}
.chap-q{font-family:var(--mono);color:var(--ash);font-size:.8rem;letter-spacing:.02em;margin:.3rem 0 1.1rem}
.chap-q::before{content:"PERGUNTA — ";color:var(--ink)}
/* insight = nota técnica com aba "▲ LEITURA" */
.insight{position:relative;background:var(--sheet);border:1px solid var(--ink);padding:26px 18px 14px;color:var(--iron);font-size:.98rem;line-height:1.6;margin:.4rem 0 1.4rem}
.insight::before{content:"▲ LEITURA DOS DADOS";position:absolute;top:-1px;left:-1px;background:var(--caution);color:var(--ink);border:1px solid var(--ink);
  font-family:var(--mono);font-size:.62rem;font-weight:600;letter-spacing:.12em;padding:2px 8px}
.insight b{color:var(--ink);font-weight:600}
.chart-t{display:flex;align-items:baseline;gap:10px;font-family:var(--display);font-size:1.08rem;font-weight:600;color:var(--ink);margin:1.3rem 0 0;letter-spacing:-.01em}
.chart-t .fig{font-family:var(--mono);font-size:.68rem;font-weight:500;letter-spacing:.08em;color:var(--sheet);background:var(--ink);padding:2px 6px;flex:none;position:relative;top:-2px}
.chart-s{font-size:.84rem;color:var(--ash);margin:.2rem 0 .5rem}

/* ---- cards: fichas de caso */
/* bordas que se tocam sem preencher células vazias da grade: cada card tem borda e sobrepõe 1px ao vizinho */
.cards{display:grid;gap:0;padding:0 1px 1px 0;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));margin:.4rem 0 1rem}
.cards.c4{grid-template-columns:repeat(4,minmax(0,1fr))}
.card{background:var(--sheet);border:1px solid var(--concrete);margin:0 -1px -1px 0;padding:16px 18px;display:flex;flex-direction:column;gap:8px;transition:background .15s}
.card:hover{background:#fffdf0}
.tag{align-self:flex-start;font-family:var(--mono);font-size:.64rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;
  background:var(--sheet);color:var(--ink);border:1px solid var(--ink)}
.tag.exp{background:var(--accent);color:#fff;border-color:var(--accent)}.tag.ret{background:#a32d2d;color:#fff;border-color:#a32d2d}
.tag.inv{background:var(--caution);border-color:var(--ink)}
.card .big{font-family:var(--display);font-size:2.1rem;font-weight:600;color:var(--ink);line-height:1;letter-spacing:-.04em;font-variant-numeric:tabular-nums}
.card .ct{font-family:var(--display);font-size:1.05rem;font-weight:600;color:var(--ink);letter-spacing:-.01em;line-height:1.25}
.card .mun{font-family:var(--mono);font-size:.68rem;font-weight:500;color:var(--ash);text-transform:uppercase;letter-spacing:.1em}
.card .dado{font-family:var(--mono);font-size:.78rem;color:var(--ink);background:var(--paper);border-left:3px solid var(--caution);padding:6px 10px}
.card .dado b{font-weight:600}
.card .tx{font-size:.88rem;line-height:1.55;color:var(--iron)}
.card .src{font-family:var(--mono);font-size:.7rem;color:var(--ash);margin-top:auto;padding-top:8px;border-top:1px solid var(--mist)}
.card .src a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--caution);text-decoration-thickness:2px;text-underline-offset:3px}
/* recomendações: ordens de serviço */
.recs{display:grid;gap:1px;background:var(--ink);border:1px solid var(--ink);grid-template-columns:repeat(3,minmax(0,1fr));align-items:stretch}
.rec{background:var(--sheet);padding:0 0 18px;height:100%}
.rec .rn{font-family:var(--mono);font-size:.7rem;font-weight:600;color:var(--ink);background:var(--caution);border-bottom:1px solid var(--ink);
  padding:6px 18px;letter-spacing:.12em;text-transform:uppercase}
.rec .rt{margin:.8rem 18px .2rem;font-family:var(--display);font-size:1.25rem;font-weight:600;color:var(--ink);letter-spacing:-.02em;line-height:1.2}
.rec .k{font-family:var(--mono);font-size:.62rem;font-weight:600;color:var(--ash);text-transform:uppercase;letter-spacing:.12em;
  margin:.9rem 18px 0;padding-top:.6rem;border-top:1px solid var(--mist)}
.rec p{font-size:.9rem;line-height:1.55;color:var(--iron);margin:.2rem 18px 0}
.draft{display:inline-block;font-family:var(--mono);font-size:.72rem;letter-spacing:.04em;background:repeating-linear-gradient(-45deg,var(--caution) 0 10px,#ffe94d 10px 20px);
  color:var(--ink);border:1px solid var(--ink);padding:5px 11px;margin:0 0 1rem}
/* listas laterais = tabela de ficha */
.list{font-size:.88rem;margin-bottom:.8rem;border:1px solid var(--ink);background:var(--sheet)}
.list .h{font-family:var(--mono);font-size:.62rem;font-weight:600;color:var(--sheet);background:var(--ink);text-transform:uppercase;letter-spacing:.12em;padding:5px 12px}
.list .row{display:flex;justify-content:space-between;gap:8px;padding:6px 12px;border-bottom:1px solid var(--mist);color:var(--ink)}
.list .row:last-of-type{border-bottom:none}
.list .row span:last-child{font-family:var(--mono);font-size:.78rem;font-variant-numeric:tabular-nums;color:var(--iron);white-space:nowrap}
.legend-d{font-size:.84rem;line-height:1.75;color:var(--ash);margin-bottom:.8rem}
.legend-d .sw{display:inline-block;width:10px;height:10px;margin-right:6px}
.legend-d b{color:var(--ink);font-weight:600}
/* botões de zoom do mapa: blocos quadrados com borda */
[data-testid="stPlotlyChart"] .modebar-container{top:8px!important;right:8px!important}
[data-testid="stPlotlyChart"] .modebar{border:1px solid var(--ink);background:var(--sheet)!important;opacity:1!important}
[data-testid="stPlotlyChart"] .modebar-group{padding:0!important;background:transparent!important}
[data-testid="stPlotlyChart"] .modebar-btn{display:block;padding:6px!important;border-bottom:1px solid var(--concrete)}
[data-testid="stPlotlyChart"] .modebar-btn:last-child{border-bottom:none}
[data-testid="stPlotlyChart"] .modebar-btn:hover{background:var(--caution)}
[data-testid="stPlotlyChart"] .modebar-btn svg{width:16px;height:16px}
@media (max-width:900px){.kpis.k3,.kpis.k4,.cards.c4,.recs,.nav,.tblock{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-title{font-size:2.3rem}
  .nav a:nth-child(2),.tblock div:nth-child(2){border-right:none}.nav a:nth-child(-n+2),.tblock div:nth-child(-n+2){border-bottom:1px solid var(--ink)}}
@media (max-width:560px){.kpis.k3,.kpis.k4,.cards.c4,.recs{grid-template-columns:1fr}.island .grid{grid-template-columns:1fr 1fr}}
</style>
"""


# ============================================================== Helpers
def md(s):
    st.markdown(s, unsafe_allow_html=True)


def esc(s):
    return html.escape(str(s))


def num(x):
    return "—" if pd.isna(x) else f"{x:,.0f}".replace(",", ".")


def snum(x):
    return "—" if pd.isna(x) else f"{x:+,.0f}".replace(",", ".").replace("-", "−")


def brl(x):
    return "—" if pd.isna(x) else "R$ " + num(x)


def pct(x, d=1):
    return "—" if pd.isna(x) else f"{x * 100:.{d}f}%".replace(".", ",")


def dec(x, d=2):
    return "—" if pd.isna(x) else f"{x:.{d}f}".replace(".", ",")


def sdec(x, d=1):
    return "—" if pd.isna(x) else f"{x:+.{d}f}".replace(".", ",").replace("-", "−")


def mes_tick(c):
    return f"{MESES[c % 100 - 1]}<br>{str(c // 100)[2:]}"


def mes_label(c):
    return f"{MESES[c % 100 - 1]}/{str(c // 100)[2:]}"


def div_nome(cod):
    return DIV.get(cod, f"Divisão {cod}")


def resumo(d, por):
    g = d.groupby(por, observed=True)[MEDIDAS].sum().reset_index()
    g["saldo"] = g.adm - g.des
    g["movs"] = g.adm + g.des
    g["turnover"] = g.des / g.adm.replace(0, np.nan)
    g["pct_pedido"] = g.des_pedido / g.des.replace(0, np.nan)
    g["sal_adm"] = g.sal_adm_sum / g.sal_adm_n.replace(0, np.nan)
    g["sal_des"] = g.sal_des_sum / g.sal_des_n.replace(0, np.nan)
    g["idade_adm"] = g.idade_adm_sum / g.idade_adm_n.replace(0, np.nan)
    return g


def total(d):
    return resumo(d.assign(_k=1), "_k").iloc[0]


def estilo(fig, h=380, legenda=True):
    fig.update_layout(
        height=h, margin=dict(l=4, r=16, t=30 if legenda else 8, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=INK2), separators=",.",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#0a0a0a", font=dict(family=FONT, color=INK, size=13)),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, title=None, font=dict(color=INK2)),
        showlegend=legenda, barcornerradius=0, bargap=0.3)
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=AXIS, linecolor=AXIS, tickfont=dict(color=MUTED), title_font=dict(color=INK2, size=12))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=AXIS, linecolor=AXIS, tickfont=dict(color=MUTED), title_font=dict(color=INK2, size=12))
    return fig


def folga(serie, f=0.22):
    lo, hi = min(float(serie.min()), 0.0), max(float(serie.max()), 0.0)
    span = (hi - lo) or 1.0
    return [lo - f * span if lo < 0 else lo, hi + f * span if hi > 0 else hi]


def grafico(fig, mapa=False):
    # topojsonURL: o mapa usa o arquivo base em static/ (servido pelo Streamlit), sem depender da CDN do Plotly
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": mapa, "displaylogo": False, "topojsonURL": "app/static/"})


FIG = {"cap": 0, "n": 0}  # numeração "FIG. capítulo.n", como numa ficha técnica


def titulo_grafico(t, s=None):
    FIG["n"] += 1
    md(f'<div class="chart-t"><span class="fig">FIG. {FIG["cap"]}.{FIG["n"]}</span>{esc(t)}</div>'
       + (f'<div class="chart-s">{esc(s)}</div>' if s else ""))


def capitulo(n, ancora, titulo, pergunta):
    FIG.update(cap=n, n=0)
    md(f'<div id="{ancora}" class="chap"><span class="n">{n:02d}</span><span class="t">{esc(titulo)}</span></div>'
       f'<div class="chap-q">{esc(pergunta)}</div>')


def kpi(lbl, val, sub="", main=False, dica=""):
    cls = "kpi main" if main else "kpi"
    bar = '<div class="bar"></div>' if main else ""
    return (f'<div class="{cls}" title="{esc(dica)}">{bar}<div class="lbl">{esc(lbl)}</div>'
            f'<div class="val">{esc(val)}</div><div class="sub">{esc(sub)}</div></div>')


TAG_CLASSE = {"Expansão": "exp", "Retração": "ret", "A investigar": "inv"}


def card_estado(c):
    return (f'<div class="card"><span class="tag">{esc(c["tag"])}</span><div class="big">{esc(c["numero"])}</div>'
            f'<div class="ct">{esc(c["titulo"])}</div><div class="tx">{esc(c["texto"])}</div>'
            f'<div class="src">Fonte: <a href="{esc(c["url"])}" target="_blank">{esc(c["fonte"])}</a></div></div>')


def card_caso(c, saldo):
    fontes = " · ".join(f'<a href="{esc(f["url"])}" target="_blank">{esc(f["nome"])}</a>' for f in c.get("fontes", []))
    fontes = f'<div class="src">Fonte: {fontes}</div>' if fontes else '<div class="src">Sem fonte encontrada</div>'
    dado = f'<div class="dado">Nosso dado: <b>{snum(saldo)} vagas</b> em {esc(c["rotulo_dado"])} (12 meses)</div>'
    return (f'<div class="card"><span class="tag {TAG_CLASSE.get(c["tag"], "")}">{esc(c["tag"])}</span>'
            f'<div class="mun">{esc(" + ".join(c["municipios"]))}</div><div class="ct">{esc(c["titulo"])}</div>'
            f'{dado}<div class="tx">{esc(c["texto"])}</div>{fontes}</div>')


class Preenche(dict):
    def __missing__(self, k):
        return "{" + k + "}"


# ============================================================== Dados
@st.cache_data
def carregar():
    cubo = pd.read_parquet(DATA / "cubo_dashboard.parquet")
    mun = pd.read_parquet(DATA / "municipios_limpo.parquet")[["municipio_cod6", "municipio", "municipio_cod7", "pop_est_2026"]]
    atv = pd.read_parquet(DATA / "atividades_municipio.parquet")
    with open(DATA / "sc_municipios.geojson", encoding="utf-8") as f:
        geo = json.load(f)
    return cubo, mun, atv, geo


def carregar_contexto():
    with open(ROOT / "data/contexto.json", encoding="utf-8") as f:
        return json.load(f)


cubo, mun, atv, geo = carregar()
ctx = carregar_contexto()
POP_TOTAL = mun.pop_est_2026.sum()
NOME = mun.set_index("municipio_cod6").municipio
COD_POR_NOME = mun.set_index("municipio").municipio_cod6
COD7_POR_NOME = mun.set_index("municipio").municipio_cod7.to_dict()
NOME_POR_COD7 = {v: k for k, v in COD7_POR_NOME.items()}
GEO_POR_COD7 = {f["properties"]["id"]: f["geometry"] for f in geo["features"]}


def contorno(cod7):
    """Anéis externos do município como uma linha (lon, lat) separada por None, para desenhar o destaque no mapa."""
    g = GEO_POR_COD7.get(cod7)
    if not g:
        return [], []
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    lon, lat = [], []
    for poly in polys:
        lon += [p[0] for p in poly[0]] + [None]
        lat += [p[1] for p in poly[0]] + [None]
    return lon, lat


def saldo_caso(c):
    cods = [COD_POR_NOME[n] for n in c["municipios"] if n in COD_POR_NOME]
    sel = atv[atv.municipio_cod6.isin(cods) & atv.subclasse.isin(c["subclasses"])]
    return sel.saldo.sum() if len(sel) else np.nan


md(CSS)

# ============================================================== Filtros
with st.sidebar:
    st.markdown("### Filtros")
    escopo = st.radio("Setores analisados", ["Indústria ampla (B–F)", "Indústria estrita (B–E)", "Todos os setores"],
                      help="Indústria ampla inclui a Construção (seção F da CNAE). Estrita: extrativas, transformação, eletricidade/gás e água/resíduos.")
    meses = sorted(cubo.competencia.unique())
    ini, fim = st.select_slider("Período", options=meses, value=(meses[0], meses[-1]), format_func=mes_label)
    min_movs = st.slider("Mín. de movimentações por município", 0, 2000, 300, 50,
                         help="Abaixo desse volume no recorte, o município aparece como 'Dados insuficientes': taxas de cidades muito pequenas oscilam demais.")
    st.caption("Fonte: Novo CAGED (MTE), competências set/25 a ago/26, e IBGE (população estimada 2026). Só emprego formal (CLT).")

periodo = cubo[(cubo.competencia >= ini) & (cubo.competencia <= fim)]
SECOES = {"Indústria ampla (B–F)": INDUSTRIA_AMPLA, "Indústria estrita (B–E)": INDUSTRIA_ESTRITA}.get(escopo)
d = periodo[periodo.secao.isin(SECOES)] if SECOES else periodo
escopo_curto = escopo.split(" (")[0].lower()

if d.empty:
    st.warning("Sem dados para esse recorte.")
    st.stop()

tot = total(d)
n_meses = d.competencia.nunique()
saldo_10k = tot.saldo / POP_TOTAL * 1e4
gap = tot.sal_adm / tot.sal_des - 1 if tot.sal_des else np.nan
grau = d.groupby("grau_grupo")[["adm", "des", "sal_adm_sum", "sal_adm_n"]].sum().reindex(ORDEM_GRAU).fillna(0)
grau["sal"] = grau.sal_adm_sum / grau.sal_adm_n.replace(0, np.nan)
pct_sup = (grau.adm["Superior completo"] + grau.adm["Pós-graduação"]) / grau.adm.sum() if grau.adm.sum() else np.nan
pct_medio = grau.adm["Médio"] / grau.adm.sum() if grau.adm.sum() else np.nan
grau_pred = grau.adm.idxmax() if grau.adm.sum() else "—"
prem_med = grau.sal["Médio"] / grau.sal["Até fundamental"] - 1

# ============================================================== Abertura
md(f'<div class="tblock"><div><span>Projeto</span>Datathon SC 2026</div><div><span>Ficha</span>Nº 01 · Raio-X</div>'
   f'<div><span>Fonte</span>Novo CAGED + IBGE</div><div><span>Recorte</span>{esc(escopo)} · {mes_label(ini)}–{mes_label(fim)}</div></div>'
   '<div class="hero-title">Raio-X do mercado de trabalho industrial de <mark>Santa Catarina</mark></div>')
entram_saem = f"Para cada 100 contratados, <b>{dec(tot.turnover * 100, 1)} saíram</b>" if pd.notna(tot.turnover) else ""
md(f'<div class="hero-lead">Em {n_meses} {"mês" if n_meses == 1 else "meses"}, foram <b>{num(tot.adm)} admissões</b> e '
   f'<b>{num(tot.des)} desligamentos</b>, um saldo de <b>{snum(tot.saldo)} vagas</b>. {entram_saem}, e '
   f'<b>{pct(tot.pct_pedido)} das saídas foram a pedido do próprio trabalhador</b>. Num estado em pleno emprego, '
   f'o gargalo não é falta de vagas: é reter as pessoas.</div>')
md('<div class="nav"><a href="#onde"><b>01</b>Onde está o problema</a><a href="#porque"><b>02</b>Por que acontece</a>'
   '<a href="#contexto"><b>03</b>O que está por trás</a><a href="#fazer"><b>04</b>O que fazer</a></div>')

# Dynamic Island (cult-ui): pílula fixa com o recorte ativo; ao passar o mouse expande com os KPIs e atalhos
md(f'<div class="island" tabindex="0"><div class="cmp"><span class="dot"></span>'
   f'<span class="lbl">{esc(escopo.split(" (")[0])} · {mes_label(ini)} – {mes_label(fim)}</span><span class="sep"></span>'
   f'<span class="num {"pos" if tot.saldo >= 0 else "neg"}">{snum(tot.saldo)} vagas</span></div>'
   f'<div class="exp"><div class="grid">'
   f'<div class="cell"><div class="k">Turnover</div><div class="v">{dec(tot.turnover)}</div></div>'
   f'<div class="cell"><div class="k">Saídas a pedido</div><div class="v">{pct(tot.pct_pedido)}</div></div>'
   f'<div class="cell"><div class="k">Salário admissão</div><div class="v">{brl(tot.sal_adm)}</div></div></div>'
   '<div class="links"><a href="#onde">Onde</a><a href="#porque">Por quê</a><a href="#contexto">Contexto</a><a href="#fazer">O que fazer</a></div>'
   '</div></div>')

md('<div class="kpis k3">'
   + kpi("Turnover (desligamentos ÷ admissões)", dec(tot.turnover), f"100 entram, {dec(tot.turnover * 100, 1)} saem" if pd.notna(tot.turnover) else "", True,
         "Perto de 1,00: a empresa contrata quase só para repor quem saiu. Acima de 1: encolhendo. Abaixo de 1: crescendo. "
         "O CAGED não traz o estoque de empregados, por isso usamos a razão entre fluxos.")
   + kpi("Salário médio de admissão", brl(tot.sal_adm), f"{pct(gap)} vs. quem saiu ({brl(tot.sal_des)})", True,
         "Média do salário mensal de quem foi admitido. Salários zerados ou acima de R$ 50 mil são ignorados.")
   + kpi("Crescimento do emprego", sdec(saldo_10k, 1), f"vagas por 10 mil hab. · saldo de {snum(tot.saldo)}", True,
         "Admissões menos desligamentos por 10 mil habitantes (população estimada IBGE 2026). Substitui a '% de pessoas empregadas', "
         "que o CAGED não permite calcular por não trazer o total de empregados.")
   + '</div>')
md('<div class="kpis k4">'
   + kpi("Saídas a pedido do trabalhador", pct(tot.pct_pedido), "das saídas no período", dica="Desligamentos do tipo 'a pedido' sobre o total de desligamentos. Alto = trabalhador com opções (sinal de apagão).")
   + kpi("Idade média de quem entra", f"{dec(tot.idade_adm, 1)} anos")
   + kpi("Contratados com superior completo", pct(pct_sup), "inclui pós-graduação")
   + kpi("Escolaridade mais contratada", grau_pred, f"{pct(pct_medio, 0)} das admissões têm ensino médio")
   + '</div>')

# ============================================================== 1. Onde
capitulo(1, "onde", "Onde está o problema", "Quais municípios e atividades crescem, encolhem ou giram demais?")

m = mun.merge(resumo(d, "municipio_cod6"), on="municipio_cod6", how="left")
for c in MEDIDAS + ["saldo", "movs"]:
    m[c] = m[c].fillna(0)
m["saldo_10k"] = m.saldo / m.pop_est_2026 * 1e4
m["giro_1k"] = m.movs / m.pop_est_2026 * 1e3
ok = m.movs >= max(min_movs, 1)
if ok.sum() >= 5:
    q_hi, q_lo, g_hi = m.loc[ok, "saldo_10k"].quantile(.8), m.loc[ok, "saldo_10k"].quantile(.2), m.loc[ok, "giro_1k"].quantile(.8)
else:
    q_hi, q_lo, g_hi = np.inf, -np.inf, np.inf
m["diag"] = np.select(
    [~ok, ok & (m.saldo_10k >= q_hi) & (m.saldo > 0), ok & (m.saldo_10k <= q_lo) & (m.saldo < 0), ok & (m.giro_1k >= g_hi)],
    ["Dados insuficientes", "Expansão acelerada", "Retração", "Alta rotatividade"], "Estável")

top = resumo(d, ["municipio_cod6", "divisao"])
top["part"] = top.adm / top.groupby("municipio_cod6").adm.transform("sum").replace(0, np.nan)
top = top.dropna(subset=["part"]).sort_values(["municipio_cod6", "part"], ascending=[True, False]).groupby("municipio_cod6").head(3)
top["txt"] = top.divisao.map(div_nome) + " (" + (top.part * 100).round(0).astype(int).astype(str) + "%)"
m = m.merge(top.groupby("municipio_cod6").txt.agg("<br>".join).rename("top_setores").reset_index(), on="municipio_cod6", how="left")
m["top_setores"] = m.top_setores.fillna("—")
m["h_saldo"] = m.saldo.map(snum)
m["h_10k"] = m.saldo_10k.map(lambda x: dec(x, 1))
m["h_turn"] = m.turnover.map(dec)
m["h_ped"] = m.pct_pedido.map(lambda x: pct(x, 0))
m["h_sal"] = m.sal_adm.map(brl)
m["h_movs"] = m.movs.map(num)
HOVER = ["municipio", "diag", "h_saldo", "h_10k", "h_turn", "h_ped", "h_sal", "h_movs", "top_setores"]
HT = ("<b>%{customdata[0]}</b> · %{customdata[1]}<br>Saldo: %{customdata[2]} vagas (%{customdata[3]} por 10 mil hab.)"
      "<br>Turnover: %{customdata[4]} · Saídas a pedido: %{customdata[5]}<br>Salário de admissão: %{customdata[6]}"
      "<br>Movimentações: %{customdata[7]}<br><br><i>Mais admissões em:</i><br>%{customdata[8]}<extra></extra>")

dv = resumo(d, "divisao")
dv["nome"] = dv.divisao.map(div_nome)
dv_ok = dv[dv.movs >= 500]
cnt = m.diag.value_counts()
exp_nomes = m[m.diag == "Expansão acelerada"].nlargest(3, "saldo_10k").municipio.tolist()
ret_nomes = m[m.diag == "Retração"].nsmallest(3, "saldo_10k").municipio.tolist()
frase_exp = f" (destaque para {', '.join(exp_nomes)})" if exp_nomes else ""
frase_ret = f" (como {', '.join(ret_nomes)})" if ret_nomes else ""
frase_atv = ""
if len(dv_ok) >= 2:
    g1, p1 = dv_ok.nlargest(1, "saldo").iloc[0], dv_ok.nsmallest(1, "saldo").iloc[0]
    frase_atv = (f" Entre as atividades, <b>{esc(g1.nome)}</b> lidera as contratações líquidas ({snum(g1.saldo)}) e "
                 f"<b>{esc(p1.nome)}</b> lidera as perdas ({snum(p1.saldo)}).")
md(f'<div class="insight"><b>{cnt.get("Expansão acelerada", 0)} municípios em expansão acelerada</b>{esc(frase_exp)} e '
   f'<b>{cnt.get("Retração", 0)} em retração</b>{esc(frase_ret)}. Outros {cnt.get("Alta rotatividade", 0)} têm alta rotatividade: '
   f'muito movimento e pouco saldo.{frase_atv}</div>')

metrica = st.segmented_control("Colorir o mapa por", ["Diagnóstico", "Saldo por 10 mil hab.", "Turnover", "Saídas a pedido", "Salário de admissão"],
                               default="Diagnóstico") or "Diagnóstico"
# Clique no mapa -> abre o município no Raio-X. O estado da seleção chega em session_state antes do rerun;
# só aplicamos quando o clique muda, para não sobrescrever uma escolha feita depois no selectbox.
_clique = (st.session_state.get("mapa_sel") or {}).get("selection", {}).get("points", [])
_cod7 = next((p.get("location") for p in _clique if p.get("location")), None)
if _cod7 != st.session_state.get("_ult_clique"):
    st.session_state["_ult_clique"] = _cod7
    if _cod7 and _cod7 in NOME_POR_COD7:
        st.session_state["mun_sel"] = NOME_POR_COD7[_cod7]
        st.session_state["_rolar_raiox"] = True
mun_atual = st.session_state.get("mun_sel", "Navegantes")

c_map, c_lado = st.columns([2.15, 1], gap="large")
with c_map:
    # Mapa vetorial (go.Choropleth): não depende de internet (tiles) nem de WebGL -> seguro para apresentar ao vivo
    fig = go.Figure()
    base = dict(geojson=geo, featureidkey="properties.id", marker=dict(line=dict(color="white", width=0.6)), hovertemplate=HT,
                # sem esmaecer o resto do mapa quando um município é clicado (o destaque é o contorno abaixo)
                selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))
    if metrica == "Diagnóstico":
        for cat, cor in DIAG_CORES.items():
            sub = m[m.diag == cat]
            if sub.empty:
                continue
            fig.add_trace(go.Choropleth(locations=sub.municipio_cod7, z=np.ones(len(sub)), colorscale=[[0, cor], [1, cor]],
                                        showscale=False, name=cat, showlegend=True, customdata=sub[HOVER], **base))
        fig.update_layout(legend=dict(orientation="h", x=0.0, y=0.0, yanchor="bottom", bgcolor="rgba(255,255,255,0)", font=dict(color=INK, size=12)))
    else:
        col, escala, centro, fmt = {
            "Saldo por 10 mil hab.": ("saldo_10k", DIVERGENTE, 0.0, ",.0f"),
            # turnover alto = ruim: mesma escala divergente, invertida (abaixo de 1 azul, acima de 1 vermelho)
            "Turnover": ("turnover", [[1 - p, cor] for p, cor in DIVERGENTE][::-1], 1.0, ".2f"),
            "Saídas a pedido": ("pct_pedido", SEQ_AZUL, None, ".0%"),
            "Salário de admissão": ("sal_adm", SEQ_AZUL, None, ",.0f"),
        }[metrica]
        fig.add_trace(go.Choropleth(locations=m.municipio_cod7, z=np.zeros(len(m)), colorscale=[[0, GRAY_NA], [1, GRAY_NA]],
                                    showscale=False, customdata=m[HOVER], **base))
        v = m[ok & m[col].notna()]
        if len(v):
            if centro is None:
                zmin, zmax = float(v[col].quantile(.02)), float(v[col].quantile(.98))
            else:
                lim = float((v[col] - centro).abs().quantile(.95)) or 1.0
                zmin, zmax = centro - lim, centro + lim
            fig.add_trace(go.Choropleth(locations=v.municipio_cod7, z=v[col], colorscale=escala, zmin=zmin, zmax=zmax,
                                        colorbar=dict(thickness=12, len=0.6, x=1.0, tickformat=fmt, outlinewidth=0,
                                                      tickfont=dict(color=INK2)), customdata=v[HOVER], **base))
        fig.update_layout(showlegend=False)
    fig.add_trace(go.Scattergeo(lon=[c[1] for c in CIDADES.values()], lat=[c[0] for c in CIDADES.values()],
                                text=list(CIDADES), mode="markers+text", textposition=[c[2] for c in CIDADES.values()],
                                marker=dict(size=4, color=INK), textfont=dict(family=FONT, size=11, color=INK),
                                hoverinfo="skip", showlegend=False))
    # Contorno do município aberto no Raio-X (linha, não preenchimento: não bloqueia hover nem clique por baixo)
    lon_c, lat_c = contorno(COD7_POR_NOME.get(mun_atual))
    if lon_c:
        fig.add_trace(go.Scattergeo(lon=lon_c, lat=lat_c, mode="lines", line=dict(color=INK, width=2.4),
                                    hoverinfo="skip", showlegend=False))
    # Enquadramento: o estado vai de lon −53,84 a −48,36 e lat −29,35 a −25,96. As faixas antigas tinham só 0,1° de folga
    # (cortava as pontas) e os rótulos da costa saíam do quadro; agora há ~0,9° a leste para eles e folga nas divisas.
    # O domain reserva a faixa de baixo para a legenda, que antes cobria o sul do estado.
    fig.update_geos(fitbounds=False, visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator",
                    lonaxis_range=[-54.1, -47.35], lataxis_range=[-29.6, -25.72],
                    domain=dict(x=[0, 1], y=[0.08 if metrica == "Diagnóstico" else 0, 1]))
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", separators=",.",
                      dragmode="pan", uirevision="mapa",  # uirevision: o zoom/arraste do usuário sobrevive aos reruns
                      modebar=dict(orientation="v", bgcolor="rgba(255,255,255,0.95)", color=MUTED, activecolor=INK),
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor="#0a0a0a", font=dict(family=FONT, color=INK, size=13)))
    st.plotly_chart(fig, width="stretch", key="mapa_sel", on_select="rerun", selection_mode="points",
                    config={"displayModeBar": True, "displaylogo": False, "scrollZoom": False, "topojsonURL": "app/static/",
                            "modeBarButtons": [["zoomInGeo", "zoomOutGeo", "resetGeo"]]})
    st.caption(f"Use **+ / −** no canto do mapa para dar zoom, arraste para mover e **clique num município para abrir o Raio-X**. "
               f"Cinza claro: menos de {min_movs} movimentações no recorte. "
               "Pescaria Brava e Balneário Rincão não existem na malha geográfica usada.")

with c_lado:
    if metrica == "Diagnóstico":
        md('<div class="legend-d">'
           f'<span class="sw" style="background:{BLUE}"></span><b>Expansão acelerada</b>: 20% maiores saldos por habitante.<br>'
           f'<span class="sw" style="background:{RED}"></span><b>Retração</b>: 20% menores saldos, com perda de vagas.<br>'
           f'<span class="sw" style="background:{ORANGE}"></span><b>Alta rotatividade</b>: muito movimento por habitante e pouco saldo.<br>'
           f'<span class="sw" style="background:{GRAY_EST}"></span><b>Estável</b> · '
           f'<span class="sw" style="background:{GRAY_NA};border:1px solid #0a0a0a"></span><b>Dados insuficientes</b></div>')
    elegiveis = m[ok]
    linhas = lambda df: "".join(f'<div class="row"><span>{esc(r.municipio)}</span><span>{snum(r.saldo)} · {sdec(r.saldo_10k, 0)}/10 mil</span></div>'
                                for r in df.itertuples())
    md('<div class="list"><div class="h">Maiores altas (saldo por 10 mil hab.)</div>' + linhas(elegiveis.nlargest(6, "saldo_10k"))
       + '<div class="h">Maiores quedas</div>' + linhas(elegiveis.nsmallest(6, "saldo_10k")) + '</div>')

with st.expander("Ver tabela dos municípios"):
    st.dataframe(m.loc[ok, ["municipio", "diag", "saldo", "saldo_10k", "turnover", "pct_pedido", "sal_adm", "movs"]]
                 .sort_values("saldo_10k", ascending=False)
                 .rename(columns={"municipio": "Município", "diag": "Diagnóstico", "saldo": "Saldo", "saldo_10k": "Saldo/10 mil hab.",
                                  "turnover": "Turnover", "pct_pedido": "% saídas a pedido", "sal_adm": "Salário admissão", "movs": "Movimentações"}),
                 hide_index=True, width="stretch",
                 column_config={"Saldo/10 mil hab.": st.column_config.NumberColumn(format="%.1f"),
                                "Turnover": st.column_config.NumberColumn(format="%.2f"),
                                "% saídas a pedido": st.column_config.NumberColumn(format="percent"),
                                "Salário admissão": st.column_config.NumberColumn(format="R$ %.0f")})

titulo_grafico(f"Atividades que mais cresceram e encolheram ({escopo_curto})",
               "Saldo de vagas por divisão da CNAE no período. Atividades com menos de 500 movimentações ficam de fora.")
if len(dv_ok):
    sel = pd.concat([dv_ok.nlargest(8, "saldo"), dv_ok.nsmallest(8, "saldo")]).drop_duplicates("divisao").sort_values("saldo")
    sel["cor"] = np.where(sel.saldo >= 0, "Cresceu", "Encolheu")
    sel["rot"] = sel.saldo.map(snum)
    fig = px.bar(sel, x="saldo", y="nome", orientation="h", color="cor", text="rot",
                 color_discrete_map={"Cresceu": BLUE, "Encolheu": NEG}, custom_data=["adm", "des", "turnover", "pct_pedido"],
                 category_orders={"cor": ["Cresceu", "Encolheu"]}, labels={"saldo": "Saldo de vagas", "nome": "", "cor": ""})
    fig.update_traces(textposition="outside", cliponaxis=False, textfont=dict(color=INK2, size=12),
                      hovertemplate="<b>%{y}</b><br>Saldo: %{x:+,.0f}<br>Admissões: %{customdata[0]:,.0f} · Desligamentos: %{customdata[1]:,.0f}"
                                    "<br>Turnover: %{customdata[2]:.2f} · Saídas a pedido: %{customdata[3]:.0%}<extra></extra>")
    estilo(fig, h=max(320, 30 * len(sel) + 60))
    fig.update_xaxes(range=folga(sel.saldo), tickformat=",.0f")
    fig.update_yaxes(categoryorder="array", categoryarray=sel.nome.tolist(), gridcolor="rgba(0,0,0,0)")
    grafico(fig)

# ---- Raio-X do município
md('<div id="raiox"></div>')
titulo_grafico("Raio-X de um município", "Escolha uma cidade aqui ou clique nela no mapa acima.")
nomes = sorted(mun.municipio)
st.session_state.setdefault("mun_sel", "Navegantes" if "Navegantes" in nomes else nomes[0])
escolha = st.selectbox("Município", nomes, key="mun_sel", label_visibility="collapsed")
if st.session_state.pop("_rolar_raiox", False):
    # leva a tela até o Raio-X depois do clique no mapa (o iframe do componente é same-origin com a página)
    components.html(f"""<script>/*{escolha}*/setTimeout(()=>window.parent.document.getElementById('raiox')
        ?.scrollIntoView({{behavior:'smooth',block:'start'}}),350)</script>""", height=0)
cod = COD_POR_NOME[escolha]
dm = d[d.municipio_cod6 == cod]
if dm.empty:
    st.info(f"{escolha} não tem movimentações neste recorte ({escopo_curto}, {mes_label(ini)} a {mes_label(fim)}).")
else:
    tm = total(dm)
    pop = mun.set_index("municipio_cod6").pop_est_2026[cod]
    diag_m = m.set_index("municipio_cod6").diag[cod]
    gap_m = tm.sal_adm / tm.sal_des - 1 if tm.sal_des else np.nan
    md('<div class="kpis k4">'
       + kpi("Saldo de vagas", snum(tm.saldo), f"{sdec(tm.saldo / pop * 1e4, 1)} por 10 mil hab. · {diag_m}")
       + kpi("Turnover", dec(tm.turnover), f"{num(tm.adm)} admissões · {num(tm.des)} desligamentos")
       + kpi("Saídas a pedido", pct(tm.pct_pedido), f"média do recorte: {pct(tot.pct_pedido)}")
       + kpi("Salário de admissão", brl(tm.sal_adm), f"{pct(gap_m)} vs. quem saiu")
       + '</div>')
    c1, c2 = st.columns([1.35, 1], gap="large")
    with c1:
        titulo_grafico("Atividades que mais explicam o saldo", "Subclasses da CNAE, 12 meses completos (o filtro de período não se aplica aqui).")
        am = atv[(atv.municipio_cod6 == cod) & (atv.secao.isin(SECOES) if SECOES else True)]
        am = pd.concat([am[am.saldo > 0].nlargest(5, "saldo"), am[am.saldo < 0].nsmallest(5, "saldo")]).sort_values("saldo")
        if len(am):
            am["nome"] = am.atividade.where(am.atividade.str.len() <= 40, am.atividade.str.slice(0, 38).str.rstrip() + "…")
            am["cor"] = np.where(am.saldo >= 0, "Cresceu", "Encolheu")
            am["rot"] = am.saldo.map(snum)
            fig = px.bar(am, x="saldo", y="nome", orientation="h", color="cor", text="rot",
                         color_discrete_map={"Cresceu": BLUE, "Encolheu": NEG}, custom_data=["atividade", "adm", "des"],
                         labels={"saldo": "Saldo de vagas", "nome": "", "cor": ""})
            fig.update_traces(textposition="outside", cliponaxis=False, textfont=dict(color=INK2, size=12),
                              hovertemplate="<b>%{customdata[0]}</b><br>Saldo: %{x:+,.0f}<br>Admissões: %{customdata[1]:,.0f} · "
                                            "Desligamentos: %{customdata[2]:,.0f}<extra></extra>")
            estilo(fig, h=max(260, 34 * len(am) + 60), legenda=False)
            fig.update_xaxes(range=folga(am.saldo, 0.3), tickformat=",.0f")
            fig.update_yaxes(categoryorder="array", categoryarray=am.nome.tolist(), gridcolor="rgba(0,0,0,0)")
            grafico(fig)
        else:
            st.caption("Sem atividades com saldo diferente de zero.")
    with c2:
        titulo_grafico("Saldo mês a mês", f"{escopo_curto.capitalize()}, {mes_label(ini)} a {mes_label(fim)}.")
        mm = resumo(dm, "competencia")
        mm["mes"] = mm.competencia.map(mes_tick)
        mm["cor"] = np.where(mm.saldo >= 0, "Positivo", "Negativo")
        fig = px.bar(mm, x="mes", y="saldo", color="cor", color_discrete_map={"Positivo": BLUE, "Negativo": NEG},
                     labels={"mes": "", "saldo": "Saldo de vagas", "cor": ""}, custom_data=["adm", "des"])
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Saldo: %{y:+,.0f}<br>Admissões: %{customdata[0]:,.0f} · "
                                        "Desligamentos: %{customdata[1]:,.0f}<extra></extra>")
        estilo(fig, h=360, legenda=False)
        fig.update_xaxes(categoryorder="array", categoryarray=mm.mes.tolist(), tickangle=0)
        fig.update_yaxes(tickformat=",.0f", title_text=None)
        grafico(fig)
    casos = [c for c in ctx["municipios"] if escolha in c["municipios"]]
    if casos:
        md('<div class="cards">' + "".join(card_caso(c, saldo_caso(c)) for c in casos) + '</div>')

# ============================================================== 2. Por quê
capitulo(2, "porque", "Por que acontece", "Renda e escolaridade explicam a rotatividade?")
abs_gap = pct(abs(gap)) if pd.notna(gap) else "—"
quem = "a menos" if pd.notna(gap) and gap < 0 else "a mais"
md(f'<div class="insight">Quem entra ganha <b>{abs_gap} {quem}</b> do que quem sai, e <b>{pct(tot.pct_pedido)} das saídas são a pedido '
   f'do trabalhador</b>. {pct(pct_medio, 0)} dos contratados têm ensino médio, e esse nível paga só <b>{pct(prem_med, 0)} a mais</b> que o '
   f'fundamental na contratação. É um sinal de que, para muita gente, trocar de empresa compensa mais do que ficar.</div>')

c1, c2 = st.columns(2, gap="large")
with c1:
    titulo_grafico("Quem paga mais cresce mais?", "Cada bolha é uma atividade: salário de admissão × saldo de vagas. O tamanho é o volume de movimentações.")
    b = dv[dv.movs >= 2000].copy()
    if len(b):
        b["cor"] = np.where(b.saldo >= 0, "Cresceu", "Encolheu")
        destaque = set(b.nlargest(2, "saldo").divisao) | set(b.nsmallest(2, "saldo").divisao)
        b["rot"] = np.where(b.divisao.isin(destaque), b.nome, "")
        fig = px.scatter(b, x="sal_adm", y="saldo", size="movs", color="cor", text="rot", size_max=46,
                         color_discrete_map={"Cresceu": BLUE, "Encolheu": NEG},
                         custom_data=["nome", "movs", "turnover", "pct_pedido"],
                         labels={"sal_adm": "Salário médio de admissão (R$)", "saldo": "Saldo de vagas", "cor": ""})
        fig.update_traces(textfont=dict(color=INK, size=11),
                          marker=dict(opacity=0.75, line=dict(color="white", width=2)),
                          hovertemplate="<b>%{customdata[0]}</b><br>Salário de admissão: R$ %{x:,.0f}<br>Saldo: %{y:+,.0f}"
                                        "<br>Movimentações: %{customdata[1]:,.0f}<br>Turnover: %{customdata[2]:.2f} · "
                                        "Saídas a pedido: %{customdata[3]:.0%}<extra></extra>")
        fig.for_each_trace(lambda t: t.update(textposition="top center" if t.name == "Cresceu" else "bottom center"))
        fig.add_hline(y=0, line_color=AXIS, line_width=1)
        estilo(fig, h=430)
        fig.update_yaxes(tickformat=",.0f")
        fig.update_xaxes(tickformat=",.0f")
        grafico(fig)
with c2:
    titulo_grafico("Salário de quem entra × de quem sai", "As 10 atividades com mais movimentações. Ordenadas pela diferença.")
    db = dv.nlargest(10, "movs").dropna(subset=["sal_adm", "sal_des"]).copy()
    if len(db):
        db["gap"] = db.sal_adm / db.sal_des - 1
        db = db.sort_values("gap", ascending=False)
        fig = go.Figure()
        xs, ys = [], []
        for r in db.itertuples():
            xs += [r.sal_adm, r.sal_des, None]
            ys += [r.nome, r.nome, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=GRAY_EST, width=3), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=db.sal_adm, y=db.nome, mode="markers", name="Quem entrou", marker=dict(color=BLUE, size=12, line=dict(color="white", width=2)),
                                 customdata=db.gap, hovertemplate="<b>%{y}</b><br>Salário de quem entrou: R$ %{x:,.0f}<br>Diferença: %{customdata:+.1%}<extra></extra>"))
        fig.add_trace(go.Scatter(x=db.sal_des, y=db.nome, mode="markers", name="Quem saiu", marker=dict(color=ORANGE, size=12, line=dict(color="white", width=2)),
                                 customdata=db.gap, hovertemplate="<b>%{y}</b><br>Salário de quem saiu: R$ %{x:,.0f}<extra></extra>"))
        estilo(fig, h=430)
        fig.update_xaxes(title_text="Salário médio (R$)", tickformat=",.0f")
        fig.update_yaxes(categoryorder="array", categoryarray=db.nome.tolist()[::-1], gridcolor="rgba(0,0,0,0)")
        grafico(fig)

c3, c4 = st.columns(2, gap="large")
with c3:
    titulo_grafico("Escolaridade de quem entra × de quem sai", "Percentual de cada grupo por nível de instrução.")
    g = grau[grau.adm + grau.des > 0]
    if len(g):
        esc_df = pd.DataFrame({"Quem entrou": g.adm / g.adm.sum(), "Quem saiu": g.des / g.des.sum()}).reset_index(names="grau") \
            .melt(id_vars="grau", var_name="grupo", value_name="pct")
        esc_df["rot"] = esc_df.pct.map(lambda x: pct(x, 0))
        fig = px.bar(esc_df, x="grau", y="pct", color="grupo", barmode="group", text="rot",
                     category_orders={"grau": ORDEM_GRAU, "grupo": ["Quem entrou", "Quem saiu"]},
                     color_discrete_map={"Quem entrou": BLUE, "Quem saiu": ORANGE}, labels={"grau": "", "pct": "", "grupo": ""})
        fig.update_traces(textposition="outside", cliponaxis=False, textfont=dict(color=INK2, size=11),
                          hovertemplate="<b>%{x}</b><br>%{y:.1%}<extra></extra>")
        estilo(fig, h=380)
        fig.update_yaxes(tickformat=".0%", showgrid=True, range=[0, float(esc_df.pct.max()) * 1.15])
        fig.update_xaxes(tickangle=0, tickvals=ORDEM_GRAU, ticktext=TICK_GRAU)
        grafico(fig)
with c4:
    titulo_grafico("Quanto vale estudar na contratação", "Salário médio de admissão por nível de instrução.")
    s = grau[grau.adm > 0].reset_index(names="grau")
    if len(s):
        s["rot"] = s.sal.map(brl)
        s["part"] = s.adm / s.adm.sum()
        fig = px.bar(s, x="grau", y="sal", text="rot", custom_data=["part"], category_orders={"grau": ORDEM_GRAU},
                     labels={"grau": "", "sal": ""})
        fig.update_traces(marker_color=BLUE, textposition="outside", cliponaxis=False, textfont=dict(color=INK2, size=12),
                          hovertemplate="<b>%{x}</b><br>Salário de admissão: R$ %{y:,.0f}<br>%{customdata[0]:.1%} das admissões<extra></extra>")
        estilo(fig, h=380, legenda=False)
        fig.update_yaxes(tickformat=",.0f", tickprefix="R$ ", range=[0, float(s.sal.max()) * 1.15])
        fig.update_xaxes(tickangle=0, tickvals=ORDEM_GRAU, ticktext=TICK_GRAU)
        grafico(fig)

c5, c6 = st.columns(2, gap="large")
with c5:
    titulo_grafico("Onde os trabalhadores mais pedem para sair", "Saídas a pedido sobre o total de desligamentos, nas 10 atividades com mais desligamentos.")
    p = dv[dv.des > 0].nlargest(10, "des").sort_values("pct_pedido")
    if len(p):
        p["rot"] = p.pct_pedido.map(lambda x: pct(x, 0))
        fig = px.bar(p, x="pct_pedido", y="nome", orientation="h", text="rot", custom_data=["des", "des_pedido"],
                     labels={"pct_pedido": "", "nome": ""})
        fig.update_traces(marker_color=BLUE, textposition="outside", cliponaxis=False, textfont=dict(color=INK2, size=12),
                          hovertemplate="<b>%{y}</b><br>%{x:.1%} das saídas a pedido<br>%{customdata[1]:,.0f} de %{customdata[0]:,.0f} desligamentos<extra></extra>")
        fig.add_vline(x=tot.pct_pedido, line_color=INK2, line_width=1, layer="below")
        fig.add_annotation(x=tot.pct_pedido, y=1.0, yref="paper", yanchor="bottom", text=f"média {pct(tot.pct_pedido, 0)}", showarrow=False,
                           font=dict(color=INK2, size=11), xanchor="center")
        estilo(fig, h=400, legenda=False)
        fig.update_layout(margin=dict(t=26))
        fig.update_xaxes(tickformat=".0%", range=[0, max(0.8, float(p.pct_pedido.max()) * 1.15)])
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        grafico(fig)
with c6:
    titulo_grafico("Sazonalidade: saldo mês a mês", f"{escopo_curto.capitalize()}, todo o estado.")
    sm = resumo(d, "competencia")
    sm["mes"] = sm.competencia.map(mes_tick)
    sm["cor"] = np.where(sm.saldo >= 0, "Positivo", "Negativo")
    fig = px.bar(sm, x="mes", y="saldo", color="cor", color_discrete_map={"Positivo": BLUE, "Negativo": NEG},
                 labels={"mes": "", "saldo": "Saldo de vagas", "cor": ""}, custom_data=["adm", "des"])
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Saldo: %{y:+,.0f}<br>Admissões: %{customdata[0]:,.0f} · "
                                    "Desligamentos: %{customdata[1]:,.0f}<extra></extra>")
    if len(sm) > 1:
        pior = sm.loc[sm.saldo.idxmin()]
        if pior.saldo < 0:
            fig.add_annotation(x=pior.mes, y=pior.saldo, text=f"{mes_label(int(pior.competencia))}: {snum(pior.saldo)}", showarrow=False, yshift=-12, xanchor="left",
                               font=dict(color=INK2, size=11))
    estilo(fig, h=400, legenda=False)
    fig.update_xaxes(categoryorder="array", categoryarray=sm.mes.tolist(), tickangle=0)
    fig.update_yaxes(tickformat=",.0f", title_text=None)
    grafico(fig)

with st.expander("Ver tabela das atividades"):
    st.dataframe(dv.sort_values("movs", ascending=False)[["nome", "adm", "des", "saldo", "turnover", "pct_pedido", "sal_adm", "sal_des"]]
                 .rename(columns={"nome": "Atividade (divisão CNAE)", "adm": "Admissões", "des": "Desligamentos", "saldo": "Saldo",
                                  "turnover": "Turnover", "pct_pedido": "% saídas a pedido", "sal_adm": "Salário entrada", "sal_des": "Salário saída"}),
                 hide_index=True, width="stretch",
                 column_config={"Turnover": st.column_config.NumberColumn(format="%.2f"),
                                "% saídas a pedido": st.column_config.NumberColumn(format="percent"),
                                "Salário entrada": st.column_config.NumberColumn(format="R$ %.0f"),
                                "Salário saída": st.column_config.NumberColumn(format="R$ %.0f")})

# ============================================================== 3. Contexto
capitulo(3, "contexto", "O que está por trás dos números", "O que aconteceu na economia que ajuda a explicar o mapa?")
md('<div class="insight">Os casos abaixo coincidem com as maiores altas e quedas do mapa. Eles reforçam a leitura dos dados, '
   'mas não provam a causa sozinhos. O caso de Mafra e Campo Alegre bate quase número a número com o registro da FIESC, '
   'o que dá confiança no tratamento da base.</div>')
md('<div class="cards c4">' + "".join(card_estado(c) for c in ctx["estado"]) + '</div>')
titulo_grafico("Casos que explicam o mapa")
md('<div class="cards">' + "".join(card_caso(c, saldo_caso(c)) for c in ctx["municipios"]) + '</div>')

# ============================================================== 4. O que fazer
capitulo(4, "fazer", "O que fazer", "Que decisões os dados sustentam?")
md('<div class="draft">Rascunho para a equipe revisar e conectar às macrofamílias de CBO. Números: indústria B–F, 12 meses.</div>')
ind = cubo[cubo.secao.isin(INDUSTRIA_AMPLA)]
ti = total(ind)
dvi = resumo(ind, "divisao").set_index("divisao")
gi = ind.groupby("grau_grupo")[["sal_adm_sum", "sal_adm_n"]].sum()
gi = gi.sal_adm_sum / gi.sal_adm_n.replace(0, np.nan)
plan = [COD_POR_NOME[n] for n in ["São Bento do Sul", "Rio Negrinho", "Campo Alegre", "Mafra"] if n in COD_POR_NOME]
pi = ind[ind.municipio_cod6.isin(plan)]


def dvi_get(cod, col):
    return dvi[col].get(cod, np.nan)


N = Preenche(
    pct_pedido_ind=pct(ti.pct_pedido), pct_pedido_alim=pct(dvi_get("10", "pct_pedido")), pct_pedido_vest=pct(dvi_get("14", "pct_pedido")),
    gap_ind=pct(abs(ti.sal_adm / ti.sal_des - 1)), saldo_planalto=snum(pi.adm.sum() - pi.des.sum()),
    saldo_alim=snum(dvi_get("10", "saldo")), saldo_eletr=snum(dvi_get("27", "saldo")), saldo_naval=snum(dvi_get("30", "saldo")),
    saldo_manut=snum(dvi_get("33", "saldo")), sal_sup=brl(gi.get("Superior completo")), sal_med=brl(gi.get("Médio")))
md('<div class="recs">' + "".join(
    f'<div class="rec"><div class="rn">Rec. {i:02d} — ordem de ação</div><div class="rt">{esc(r["titulo"])}</div>'
    f'<div class="k">Evidência</div><p>{esc(r["evidencia"].format_map(N))}</p>'
    f'<div class="k">Ação</div><p>{esc(r["acao"].format_map(N))}</p>'
    f'<div class="k">Como medir</div><p>{esc(r["medir"].format_map(N))}</p></div>'
    for i, r in enumerate(ctx["recomendacoes"], start=1)) + '</div>')

st.write("")
with st.expander("Notas metodológicas e limites da análise"):
    st.markdown("""
- **Base:** Novo CAGED (movimentações), SC, competências set/2025 a ago/2026. Cada linha é uma movimentação, não uma pessoa. As cerca de 6 mil linhas com competência anterior são declarações tardias e foram excluídas.
- **Saldo** = admissões − desligamentos. **Turnover** aqui = desligamentos ÷ admissões, porque o CAGED não traz o estoque de empregados.
- **Saídas a pedido** = desligamentos do tipo 40 ("a pedido") sobre o total de desligamentos.
- **Salário e idade médios** são calculados sobre quem foi admitido (ou desligado, quando indicado). Salários zerados ou acima de R$ 50 mil foram desconsiderados.
- **Diagnóstico dos municípios** (entre os que têm o mínimo de movimentações): *expansão acelerada* = 20% maiores saldos por 10 mil hab. com saldo positivo; *retração* = 20% menores com saldo negativo; *alta rotatividade* = 20% maiores movimentações por mil hab. que não caíram nas anteriores; o resto é *estável*. É uma classificação relativa ao recorte escolhido.
- **Atividades** = divisões da CNAE 2.0 (2 dígitos). **Indústria ampla** = seções B a F; **estrita** = B a E.
- **Contexto e recomendações** vêm de `data/contexto.json`; as notícias reforçam os dados, mas não provam causa.
- **Limites:** só emprego formal (autônomos, MEIs e informais não aparecem); municípios pequenos oscilam muito.
""")
