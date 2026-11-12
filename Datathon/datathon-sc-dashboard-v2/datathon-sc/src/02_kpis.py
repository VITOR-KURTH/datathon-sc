"""Etapa 2 - KPIs candidatos (janela 09/2025-08/2026, industria_ampla = CNAE B-F)."""
import pandas as pd
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / "data/processed"
df = pd.read_parquet(OUT / "caged_enriquecido.parquet")
m = pd.read_parquet(OUT / "municipios_limpo.parquet")
d = df[df.janela_12m & df.industria_ampla]

k = (d.groupby(["municipio_cod6","municipio","pop_est_2026"])
       .agg(admissoes=("admissao","sum"), desligamentos=("desligamento","sum"), saldo=("saldo","sum")).reset_index())
k["movs"] = k.admissoes + k.desligamentos
k["saldo_10k"] = k.saldo / k.pop_est_2026 * 1e4
k["turnover"] = k.desligamentos / k.admissoes              # >1 = mais saidas que entradas
adm, des = d[d.admissao == 1], d[d.desligamento == 1]
k = k.merge(adm.groupby("municipio_cod6").agg(
        sal_adm=("salario_valido","mean"),
        pct_superior_adm=("grau_instrucao", lambda s: s.isin([9,10,11,80]).mean())).reset_index(), on="municipio_cod6", how="left")
k = k.merge(des.groupby("municipio_cod6").agg(sal_des=("salario_valido","mean")).reset_index(), on="municipio_cod6", how="left")
k["gap_salarial"] = k.sal_adm - k.sal_des                   # admitidos ganham menos que desligados?
k = k.merge(m[["municipio_cod6","idhm","pib_per_capita"]], on="municipio_cod6")
k["amostra_ok"] = k.movs >= 1000                            # evita ranking dominado por cidade minúscula
k.to_csv(OUT / "kpi_municipio.csv", index=False)

mensal = (df[df.janela_12m].assign(grupo=lambda x: x.industria_ampla.map({True:"Indústria (B-F)", False:"Demais setores"}))
          .groupby(["competencia_dt","grupo"]).agg(admissoes=("admissao","sum"), desligamentos=("desligamento","sum"), saldo=("saldo","sum")).reset_index())
mensal.to_csv(OUT / "serie_mensal.csv", index=False)

setor = (d.groupby(["secao","secao_desc"]).agg(admissoes=("admissao","sum"), desligamentos=("desligamento","sum"),
         saldo=("saldo","sum"), sal_medio=("salario_valido","mean")).reset_index())
setor["turnover"] = setor.desligamentos / setor.admissoes
setor.to_csv(OUT / "kpi_setor.csv", index=False)
print(k[k.amostra_ok].shape[0], "municípios com amostra ok de", len(k))
print(setor.to_string(index=False))
