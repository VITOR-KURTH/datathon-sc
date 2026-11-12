"""Etapa 1 - Ingestão, validação e JOIN (CAGED x Municípios IBGE).

Uso: python src/01_ingestao_join.py <caminho_Novo_Caged_MOV_Limpo.csv>
Saídas em data/processed/:
  caged_enriquecido.parquet   (1 linha por movimentação, já com dados do município)
  municipio_setor_mes.parquet (agregado: município x seção CNAE x mês)
  municipios_limpo.parquet
"""
import sys, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data/raw", ROOT / "data/processed"
OUT.mkdir(parents=True, exist_ok=True)
caged_path = Path(sys.argv[1]) if len(sys.argv) > 1 else RAW / "Novo_Caged_MOV_Limpo.csv"

# ---------------- 1. CAGED ----------------
c = pd.read_csv(caged_path, sep=";", decimal=",", low_memory=False)
c = c.drop(columns=[x for x in c.columns if x.startswith("Unnamed")])
c = c.rename(columns={
    "competênciamov": "competencia", "município": "municipio_cod6", "seção": "secao",
    "saldomovimentação": "saldo", "cbo2002ocupação": "cbo", "graudeinstrução": "grau_instrucao",
    "salário": "salario", "tipomovimentação": "tipo_mov", "tamestabjan": "faixa_tam_estab"})
n0 = len(c)
c["idade"] = pd.to_numeric(c["idade"], errors="coerce")

# Registros de origem "EmpregadoWEB" com categoria "Não identificado" (510 linhas) -> inválidos
inval = (c["categoria"] == 999) | c["secao"].isin(["Z"])
print(f"CAGED: {n0:,} linhas | removidas por categoria/seção não identificada: {inval.sum():,}")
c = c[~inval].copy()
# Obs.: nao existe coluna indicadordeexclusao nesta base ('Limpo'): filtro MOV x EX ja aplicado pela organização.

c["competencia_dt"] = pd.to_datetime(c["competencia"].astype(str), format="%Y%m")
c["salario_valido"] = c["salario"].where((c["salario"] > 0) & (c["salario"] <= 50_000))  # 0 e outliers -> NaN
# ATENCAO: so ha dados reais de 09/2025 a 08/2026 (12 meses). Linhas com competencia anterior (~6 mil) sao
# declaracoes tardias (competenciadec >= 202509) e distorcem series mensais -> flag para filtrar no dashboard.
c["janela_12m"] = c["competencia"] >= 202509
c["admissao"] = (c["saldo"] == 1).astype(int)
c["desligamento"] = (c["saldo"] == -1).astype(int)
c["industria_estrita"] = c["secao"].isin(list("BCDE"))   # extrativa, transformação, eletricidade, água
c["industria_ampla"] = c["secao"].isin(list("BCDEF"))    # + construção

GRAU = {1:"Analfabeto",2:"Até 5ª incompl.",3:"5ª compl. fund.",4:"6ª a 9ª fund.",5:"Fundamental compl.",
        6:"Médio incompl.",7:"Médio compl.",8:"Superior incompl.",9:"Superior compl.",10:"Mestrado",11:"Doutorado",
        80:"Pós-graduação compl.",99:"Não identificado"}
c["grau_desc"] = c["grau_instrucao"].map(GRAU)
GRUPO_GRAU = {1:"Até fundamental",2:"Até fundamental",3:"Até fundamental",4:"Até fundamental",5:"Até fundamental",
              6:"Médio",7:"Médio",8:"Superior incompleto",9:"Superior completo",
              10:"Pós-graduação",11:"Pós-graduação",80:"Pós-graduação"}   # 99 (não identificado) -> NaN
c["grau_grupo"] = c["grau_instrucao"].map(GRUPO_GRAU)
SECAO = pd.read_excel(RAW / "Dicionario_de_dados.xlsx", sheet_name="seção", dtype=str)
SECAO.columns = ["secao", "secao_desc"]
c = c.merge(SECAO, on="secao", how="left")

# ---------------- 2. MUNICÍPIOS (IBGE) ----------------
m = pd.read_csv(RAW / "Municipios_SC_limpo.csv", dtype=str)
m = m.drop(columns=[x for x in m.columns if x.startswith("Unnamed")])
m = m[m["Código [-]"].str.fullmatch(r"\d{7}", na=False)].copy()   # descarta linhas de rodapé/fontes do IBGE
def limpa(nome):
    nome = re.sub(r"<[^>]+>.*?<[^>]+>|<[^>]+>", "", nome)         # tira tags HTML
    return re.sub(r"\s*\[.*?\]\s*$", "", nome).strip()
m = m.rename(columns={
    "Município [-]": "municipio", "Código [-]": "municipio_cod7",
    "Área Territorial - km² [2025]": "area_km2",
    "População no último censo - pessoas [2022]": "pop_2022",
    "Densidade demográfica - hab/km² [2022]": "densidade",
    "População estimada - pessoas [2026]": "pop_est_2026",
    "Escolarização <span>6 a 14 anos</span> - % [2022]": "escolarizacao_6_14",
    "IDHM <span>Índice de desenvolvimento humano municipal</span> [2010]": "idhm",
    "PIB per capita - R$ [2023]": "pib_per_capita"})
m = m[["municipio","municipio_cod7","area_km2","pop_2022","densidade","pop_est_2026",
       "escolarizacao_6_14","idhm","pib_per_capita"]]
for col in m.columns[2:]:
    m[col] = pd.to_numeric(m[col].replace("-", pd.NA), errors="coerce")
m["municipio_cod6"] = m["municipio_cod7"].str[:6].astype(int)   # CHAVE: CAGED usa 6 dígitos (sem dígito verificador)
assert m["municipio_cod6"].is_unique

# ---------------- 3. JOIN + validação ----------------
sem_par = set(c["municipio_cod6"]) - set(m["municipio_cod6"])
sem_mov = set(m["municipio_cod6"]) - set(c["municipio_cod6"])
print(f"Municípios CAGED: {c['municipio_cod6'].nunique()} | IBGE: {len(m)} | sem par no IBGE: {len(sem_par)} | sem movimentação: {len(sem_mov)}")
df = c.merge(m, on="municipio_cod6", how="left", validate="m:1")
assert len(df) == len(c), "o join duplicou/perdeu linhas"
print(f"Linhas sem município após join: {df['municipio'].isna().sum()}")

# ---------------- 4. Agregado base + exportação ----------------
agg = (df.groupby(["municipio_cod6","municipio","pop_est_2026","competencia_dt","secao","secao_desc"], observed=True)
         .agg(admissoes=("admissao","sum"), desligamentos=("desligamento","sum"), saldo=("saldo","sum"),
              salario_medio=("salario_valido","mean")).reset_index())
df.to_parquet(OUT / "caged_enriquecido.parquet", index=False)
agg.to_parquet(OUT / "municipio_setor_mes.parquet", index=False)
m.to_parquet(OUT / "municipios_limpo.parquet", index=False)
print("OK ->", OUT, "| linhas finais:", f"{len(df):,}")
