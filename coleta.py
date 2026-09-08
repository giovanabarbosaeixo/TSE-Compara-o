"""
coleta.py — votação de Presidente por UF no 2º turno de 2018 (Haddad x
Bolsonaro) e 2022 (Lula x Bolsonaro), pra comparar os dois anos: quanto
cada um tirou por estado, e como a distância entre Lula/Haddad e
Bolsonaro mudou de um ciclo pro outro.

Script INDEPENDENTE — não importa nada de app.py/tse_api.py/clientes.py/
senado2026.py, só bibliotecas padrão + requests + pandas.

FONTE: Portal de Dados Abertos do TSE (dadosabertos.tse.jus.br), dataset
"votacao_candidato_munzona_<ano>" — voto por candidato/município/zona,
oficial e PERMANENTE (ao contrário do site de apuração ao vivo usado no
resto deste projeto, que só mantém pleitos recentes — por isso 2018 não
dá pra buscar por lá, only 2022+). Mesmo formato de arquivo nos dois
anos, o que permite comparar 2018 com 2022 de forma direta.

Candidato é identificado pelo NÚMERO na urna, não pelo nome (mais
confiável contra variação de grafia/maiúscula entre arquivos) — mas o
número NÃO é o mesmo nos dois anos pro mesmo lado, então há um mapa
número->candidato SEPARADO por ano (CANDIDATOS_POR_ANO):
  13 = PT nos dois anos -> Haddad em 2018, Lula em 2022.
  17 = Bolsonaro em 2018 (PSL).
  22 = Bolsonaro em 2022 (PL — trocou de partido/número; a suposição
       inicial de que ele teria mantido o "17" por marca estava ERRADA,
       corrigida depois de rodar contra o dado real e ver "17: NENHUM
       ENCONTRADO" em 2022 — checado direto no CSV: NR_CANDIDATO 22 =
       "JAIR BOLSONARO" no 2º turno de 2022).
O script imprime os nomes encontrados pra cada número como conferência —
se algum outro número mudar de novo no futuro, aparece na hora, não fica
errado em silêncio.

AVISO IMPORTANTE sobre esta implementação: o ambiente onde este script
foi escrito tomou HTTP 403 da TSE (cdn.tse.jus.br e dadosabertos.tse.jus.br)
depois de poucas tentativas — parece bloqueio de IP de nuvem/datacenter
da própria TSE, não erro de URL (o link de 2022 foi confirmado ao vivo,
raspando a página do dataset, ANTES do bloqueio começar). Rodando de um
computador normal isso deve funcionar liso. Se mesmo assim travar com
403/404:
  1. Abra no navegador: https://dadosabertos.tse.jus.br/dataset/resultados-2018
     (e o -2022) e ache o arquivo "Resultados – Votação por candidato e
     município" (nome do link: votacao_candidato_munzona_<ano>.zip).
  2. Baixe na mão e rode: python coleta.py --zip-2018 caminho\\arquivo.zip
     (idem --zip-2022).
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

URL_ZIP = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"

PASTA_CACHE = Path(__file__).parent / "cache_coleta"

# ano -> {número de urna: rótulo normalizado}. O NOME de verdade (Haddad/
# Lula/Bolsonaro) vem do próprio arquivo e é só impresso como conferência;
# o rótulo aqui ("pt"/"bolsonaro") é a chave usada pra juntar os dois anos
# na mesma coluna, já que o NÚMERO de um dos lados muda entre eles.
CANDIDATOS_POR_ANO = {
    2018: {13: "pt", 17: "bolsonaro"},
    2022: {13: "pt", 22: "bolsonaro"},
}
CARGO_ALVO = "PRESIDENTE"
TURNO_ALVO = 2

# Nomes de coluna aceitos por campo lógico — os arquivos da TSE às vezes
# variam a coluna de votos entre vintages; olhar por uma LISTA em vez de
# um nome fixo evita ler tudo zerado em silêncio se um nome mudar (mesma
# armadilha documentada em clientes.py deste projeto, replicada aqui sem
# importar nada de lá).
COLUNAS_ACEITAS = {
    "uf": ["SG_UF"],
    "cargo": ["DS_CARGO"],
    "turno": ["NR_TURNO"],
    "numero": ["NR_CANDIDATO"],
    "nome_urna": ["NM_URNA_CANDIDATO"],
    "votos": ["QT_VOTOS_NOMINAIS_VALIDOS", "QT_VOTOS_NOMINAIS"],
}


class ColunaNaoEncontrada(Exception):
    pass


def _indice_colunas(cabecalho: list[str]) -> dict[str, str]:
    """campo lógico -> nome REAL da coluna neste arquivo específico."""
    limpo = [c.strip().upper() for c in cabecalho]
    resultado: dict[str, str] = {}
    faltando = []
    for campo, aceitos in COLUNAS_ACEITAS.items():
        achou = next((c for c in aceitos if c in limpo), None)
        if achou is None:
            faltando.append(campo)
        else:
            # devolve o nome como apareceu de fato no cabeçalho (mesma
            # capitalização), pra usar em usecols/rename sem confundir pandas.
            resultado[campo] = cabecalho[limpo.index(achou)]
    if faltando:
        raise ColunaNaoEncontrada(
            f"Não achei coluna pra {faltando} neste CSV. Cabeçalho real: {cabecalho}. "
            f"A TSE deve ter renomeado — adicione a variante nova em COLUNAS_ACEITAS."
        )
    return resultado


def baixar_zip(ano: int, caminho_manual: str | None = None, timeout: float = 120) -> Path:
    """
    Baixa (com cache local) o zip de votação por candidato/município/zona
    do ano pedido — ou devolve `caminho_manual` direto se foi passado
    (aceita tanto o .zip baixado quanto a PASTA já descompactada; muito
    navegador extrai sozinho ao baixar).
    """
    if caminho_manual:
        caminho = Path(caminho_manual)
        if not caminho.exists():
            raise FileNotFoundError(f"Caminho indicado em --zip-{ano} não existe: {caminho}")
        return caminho

    PASTA_CACHE.mkdir(exist_ok=True)
    destino = PASTA_CACHE / f"votacao_candidato_munzona_{ano}.zip"
    if destino.exists():
        print(f"[{ano}] usando cache local: {destino}")
        return destino

    url = URL_ZIP.format(ano=ano)
    print(f"[{ano}] baixando {url} ...")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(
            f"Falha ao baixar dados de {ano} em {url}: {e}\n"
            f"Se for 403/404, baixe manualmente pelo navegador em "
            f"https://dadosabertos.tse.jus.br/dataset/resultados-{ano} "
            f"e rode de novo com --zip-{ano} <arquivo baixado>."
        ) from e

    destino.write_bytes(resp.content)
    print(f"[{ano}] salvo em {destino} ({len(resp.content) / 1_048_576:.1f} MB)")
    return destino


def _localizar_fontes(caminho: Path, ano: int) -> list[tuple[str, object]]:
    """
    Devolve uma lista de (rótulo, abridor) — `abridor()` devolve um
    arquivo-texto (latin-1) pronto pra ler, novo a cada chamada (o
    cabeçalho é lido antes do corpo, então cada fonte precisa ser aberta
    duas vezes).

    Prioriza um arquivo terminado em "_<ano>_BR.csv" quando existe — nos
    dados da TSE esse é o recorte de abrangência NACIONAL (SG_UE="BR"),
    que cobre só Presidente (o único cargo que não é por estado) já
    isolado dos outros — ~90 mil linhas em vez de percorrer os 27 CSVs
    por estado (que misturam Governador/Senador/Deputado) ou abrir o
    "_BRASIL.csv" com tudo junto (~4 GB, sem necessidade se esse recorte
    menor já existe). Só cai pra "todo mundo" se não achar esse arquivo.
    """
    alvo = f"_{ano}_br.csv"

    if caminho.is_dir():
        preferido = next((p for p in caminho.glob("*.csv") if p.name.lower().endswith(alvo)), None)
        arquivos = [preferido] if preferido else sorted(caminho.glob("*.csv"))
        if not arquivos:
            raise RuntimeError(f"Nenhum .csv encontrado em {caminho}")
        return [(a.name, (lambda a=a: open(a, encoding="latin-1", newline=""))) for a in arquivos]

    with zipfile.ZipFile(caminho) as zf:
        membros = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not membros:
        raise RuntimeError(f"Nenhum .csv dentro de {caminho}")
    preferido_zip = [n for n in membros if n.lower().endswith(alvo)]
    escolhidos = preferido_zip or membros

    def _abrir_membro(membro):
        # reabre o zip a cada chamada — um ZipExtFile não dá pra "rebobinar",
        # e cada fonte aqui é lida duas vezes (cabeçalho, depois corpo).
        return io.TextIOWrapper(zipfile.ZipFile(caminho).open(membro), encoding="latin-1")

    return [(m, (lambda m=m: _abrir_membro(m))) for m in escolhidos]


def extrair_votos_presidente(caminho: Path, ano: int) -> pd.DataFrame:
    """
    Lê o(s) CSV(s) de `caminho` (.zip ou pasta já extraída) e devolve só
    os votos válidos de Presidente, 2º turno, dos candidatos de
    CANDIDATOS_POR_ANO[ano] — agregados por UF e por rótulo ("pt"/
    "bolsonaro"). Lê em pedaços (chunksize) e filtra a cada pedaço em vez
    de carregar o arquivo inteiro (que pode trazer TODOS os cargos, não
    só presidente) — evita estourar memória com dados que vão ser
    descartados de qualquer forma.
    """
    candidatos_ano = CANDIDATOS_POR_ANO[ano]
    linhas: list[dict] = []
    nomes_por_rotulo: dict[str, set[str]] = {r: set() for r in candidatos_ano.values()}

    for rotulo_arquivo, abrir in _localizar_fontes(caminho, ano):
        print(f"[{ano}] lendo {rotulo_arquivo} ...")
        with abrir() as f:
            # sondagem só do cabeçalho pra descobrir os nomes reais das colunas
            cabecalho = pd.read_csv(f, sep=";", nrows=0).columns.tolist()
        idx = _indice_colunas(cabecalho)

        with abrir() as f:
            leitor = pd.read_csv(
                f,
                sep=";",
                usecols=list(idx.values()),
                dtype=str,
                chunksize=200_000,
            )
            for pedaco in leitor:
                pedaco = pedaco.rename(columns={v: k for k, v in idx.items()})
                pedaco["cargo"] = pedaco["cargo"].str.strip().str.upper()
                pedaco["numero"] = pd.to_numeric(pedaco["numero"], errors="coerce")
                pedaco["turno"] = pd.to_numeric(pedaco["turno"], errors="coerce")
                pedaco["votos"] = pd.to_numeric(pedaco["votos"], errors="coerce").fillna(0)

                filtrado = pedaco[
                    (pedaco["cargo"] == CARGO_ALVO)
                    & (pedaco["turno"] == TURNO_ALVO)
                    & (pedaco["numero"].isin(candidatos_ano))
                ].copy()
                if filtrado.empty:
                    continue
                filtrado["candidato"] = filtrado["numero"].map(candidatos_ano)

                for rotulo, grupo in filtrado.groupby("candidato"):
                    nomes_por_rotulo[rotulo].update(grupo["nome_urna"].str.strip().unique())

                agregado = filtrado.groupby(["uf", "candidato"], as_index=False)["votos"].sum()
                linhas.extend(agregado.to_dict("records"))

    if not linhas:
        raise RuntimeError(
            f"Não encontrei nenhuma linha de Presidente/2º turno/candidatos "
            f"{list(candidatos_ano)} em {caminho} — confira se o ano/arquivo "
            f"está certo (2018 e 2022 são os únicos com 2º turno de "
            f"Presidente; os números de cada lado estão em CANDIDATOS_POR_ANO)."
        )

    print(f"[{ano}] conferência de nomes por rótulo:")
    for numero, rotulo in candidatos_ano.items():
        print(f"    {numero} ({rotulo}): {sorted(nomes_por_rotulo[rotulo]) or 'NENHUM ENCONTRADO'}")

    df = pd.DataFrame(linhas).groupby(["uf", "candidato"], as_index=False)["votos"].sum()
    df["ano"] = ano
    df["votos"] = df["votos"].astype(int)
    return df[["ano", "uf", "candidato", "votos"]]


def montar_comparativo(df_2018: pd.DataFrame, df_2022: pd.DataFrame) -> pd.DataFrame:
    """
    Uma linha por UF: votos e % de cada candidato em cada ano, mais a
    variação de margem (Lula/Haddad menos Bolsonaro) entre os dois —
    positivo = o candidato do PT ganhou terreno sobre o Bolsonaro daquele
    ano pro outro.
    """

    def _pivotar(df: pd.DataFrame, sufixo: str) -> pd.DataFrame:
        p = df.pivot(index="uf", columns="candidato", values="votos").rename(
            columns={"pt": f"pt_votos_{sufixo}", "bolsonaro": f"bolsonaro_votos_{sufixo}"}
        )
        total = p.sum(axis=1)
        p[f"pt_pct_{sufixo}"] = (p[f"pt_votos_{sufixo}"] / total * 100).round(2)
        p[f"bolsonaro_pct_{sufixo}"] = (p[f"bolsonaro_votos_{sufixo}"] / total * 100).round(2)
        p[f"margem_pt_{sufixo}"] = (p[f"pt_pct_{sufixo}"] - p[f"bolsonaro_pct_{sufixo}"]).round(2)
        return p

    p18 = _pivotar(df_2018, "2018")
    p22 = _pivotar(df_2022, "2022")
    comp = p18.join(p22, how="outer")
    comp["variacao_margem_pt"] = (comp["margem_pt_2022"] - comp["margem_pt_2018"]).round(2)
    comp["virou_a_favor_do_pt"] = (comp["margem_pt_2018"] < 0) & (comp["margem_pt_2022"] > 0)
    return comp.reset_index().sort_values("variacao_margem_pt", ascending=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip-2018", help="Caminho local pro zip de 2018 (pula o download)")
    ap.add_argument("--zip-2022", help="Caminho local pro zip de 2022 (pula o download)")
    ap.add_argument("--saida", default="comparativo_presidente_2018_2022.csv")
    args = ap.parse_args()

    caminho_2018 = baixar_zip(2018, args.zip_2018)
    caminho_2022 = baixar_zip(2022, args.zip_2022)

    df_2018 = extrair_votos_presidente(caminho_2018, 2018)
    df_2022 = extrair_votos_presidente(caminho_2022, 2022)

    comparativo = montar_comparativo(df_2018, df_2022)
    comparativo.to_csv(args.saida, index=False, encoding="utf-8-sig")
    print(f"\nSalvo em {args.saida} ({len(comparativo)} UFs)")

    print("\n--- Resumo nacional ---")
    for ano, df in ((2018, df_2018), (2022, df_2022)):
        total = df.groupby("candidato")["votos"].sum()
        pt = total.get("pt", 0)
        bolso = total.get("bolsonaro", 0)
        pct_pt = pt / (pt + bolso) * 100
        pct_bolso = bolso / (pt + bolso) * 100
        print(f"{ano}: PT {pt:,} ({pct_pt:.2f}%)  x  Bolsonaro {bolso:,} ({pct_bolso:.2f}%)".replace(",", "."))

    viraram = comparativo[comparativo["virou_a_favor_do_pt"]]["uf"].tolist()
    print(f"\nEstados que estavam com Bolsonaro à frente em 2018 e viraram pro PT em 2022: {viraram or 'nenhum'}")
    print("\nMaiores avanços do PT (margem 2022 menos margem 2018), por UF:")
    print(comparativo[["uf", "margem_pt_2018", "margem_pt_2022", "variacao_margem_pt"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
