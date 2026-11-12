"""Etapa 3 - Tabelas compactas para o dashboard (janela 09/2025-08/2026).

Saídas em data/processed/:
  cubo_dashboard.parquet      município x mês x divisão CNAE x escolaridade, com somas para recalcular
                              médias ponderadas no app (salário, idade) e a contagem de saídas a pedido.
  atividades_municipio.parquet município x subclasse CNAE (12 meses, todos os setores): admissões,
                              desligamentos e saldo, usado no raio-X do município e na seção de contexto.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed"
cols = ["municipio_cod6", "competencia", "secao", "subclasse", "grau_grupo", "janela_12m", "tipo_mov",
        "admissao", "desligamento", "salario_valido", "idade"]
df = pd.read_parquet(OUT / "caged_enriquecido.parquet", columns=cols)
df = df[df.janela_12m].drop(columns="janela_12m").copy()
df["grau_grupo"] = df["grau_grupo"].astype(object).fillna("Não identificado")
df["divisao"] = df["subclasse"].astype(str).str.zfill(7).str[:2]

adm, des = df.admissao == 1, df.desligamento == 1
sal = df.salario_valido.fillna(0)
idade = df.idade.fillna(0)
df["adm"] = df.admissao
df["des"] = df.desligamento
df["des_pedido"] = (des & (df.tipo_mov == 40)).astype(int)          # 40 = desligamento a pedido do trabalhador
df["sal_adm_sum"] = np.where(adm, sal, 0.0)
df["sal_adm_n"] = (adm & df.salario_valido.notna()).astype(int)
df["sal_des_sum"] = np.where(des, sal, 0.0)
df["sal_des_n"] = (des & df.salario_valido.notna()).astype(int)
df["idade_adm_sum"] = np.where(adm, idade, 0.0)
df["idade_adm_n"] = (adm & df.idade.notna()).astype(int)

meas = ["adm", "des", "des_pedido", "sal_adm_sum", "sal_adm_n", "sal_des_sum", "sal_des_n", "idade_adm_sum", "idade_adm_n"]
cubo = (df.groupby(["municipio_cod6", "competencia", "secao", "divisao", "grau_grupo"], observed=True)[meas]
          .sum().reset_index())
cubo.to_parquet(OUT / "cubo_dashboard.parquet", index=False)
assert cubo.adm.sum() == df.adm.sum() and cubo.des.sum() == df.des.sum()

# ---- atividades (subclasse) por município, 12 meses ----
dic = pd.read_excel(ROOT / "data/raw/Dicionario_de_dados.xlsx", sheet_name="subclasse", dtype=str)
dic.columns = ["subclasse", "atividade"]
dic["subclasse"] = pd.to_numeric(dic["subclasse"].str.strip(), errors="coerce")
dic = dic.dropna().astype({"subclasse": int})
dic["atividade"] = dic["atividade"].str.replace(r"\s*\(Desativad[oa].*?\)", "", regex=True).str.strip()
atv = (df.groupby(["municipio_cod6", "secao", "subclasse"]).agg(adm=("adm", "sum"), des=("des", "sum")).reset_index()
         .merge(dic, on="subclasse", how="left"))
atv["saldo"] = atv.adm - atv.des
atv["atividade"] = atv["atividade"].fillna("Subclasse " + atv.subclasse.astype(str))
atv.to_parquet(OUT / "atividades_municipio.parquet", index=False)

print(f"cubo: {len(cubo):,} linhas | atividades: {len(atv):,} linhas | "
      f"admissões {cubo.adm.sum():,} | desligamentos {cubo.des.sum():,} | a pedido {cubo.des_pedido.sum():,}")
