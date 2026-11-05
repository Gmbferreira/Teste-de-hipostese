"""Coleta dos dados reais da issue #3.

Baixa pull requests mergeados de um repositório público, verifica quais
receberam review de um bot de revisão de código e grava a amostra em CSV.

Uso:
    python -m src.coleta
    python -m src.coleta --repo supabase/supabase --n-por-grupo 35
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.config import make_rng

API = "https://api.github.com"
RAIZ = Path(__file__).resolve().parent.parent
SAIDA_PADRAO = RAIZ / "data" / "prs_merge_time.csv"

# Bots cuja review é efetivamente uma revisão de código automatizada.
# Bots de CI, deploy ou comentário (github-actions, vercel, sentry etc.)
# não entram, para não contaminar a definição do grupo "com bot".
BOTS_REVISAO = {
    "coderabbitai[bot]",
    "copilot-pull-request-reviewer[bot]",
    "cubic-dev-ai[bot]",
    "greptile-apps[bot]",
    "chatgpt-codex-connector[bot]",
    "cursor[bot]",
    "qodo-merge-pro[bot]",
    "sourcery-ai[bot]",
    "gemini-code-assist[bot]",
    "devin-ai-integration[bot]",
    "open-swe[bot]",
}


def carregar_token() -> str:
    load_dotenv(RAIZ / ".env")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "GITHUB_TOKEN não encontrado. Copie .env.example para .env e preencha o token."
        )
    return token


def criar_sessao(token: str) -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    return sessao


def get(sessao: requests.Session, url: str, **params):
    for tentativa in range(5):
        try:
            resposta = sessao.get(url, params=params, timeout=30)
        except requests.exceptions.RequestException:
            if tentativa == 4:
                raise
            time.sleep(2 * (tentativa + 1))
            continue
        if resposta.status_code == 403 and "rate limit" in resposta.text.lower():
            reset = int(resposta.headers.get("x-ratelimit-reset", "0"))
            espera = max(reset - int(time.time()), 1)
            print(f"Rate limit atingido; aguardando {espera}s...")
            time.sleep(espera)
            continue
        if resposta.status_code >= 500 and tentativa < 4:
            time.sleep(2 * (tentativa + 1))
            continue
        resposta.raise_for_status()
        return resposta
    raise RuntimeError(f"Falha ao acessar {url}")


def listar_prs_mergeados(
    sessao: requests.Session,
    repo: str,
    desde: datetime,
    max_prs: int,
) -> list[dict]:
    prs: list[dict] = []
    pagina = 1
    while len(prs) < max_prs:
        lote = get(
            sessao,
            f"{API}/repos/{repo}/pulls",
            state="closed",
            sort="created",
            direction="desc",
            per_page=100,
            page=pagina,
        ).json()
        if not lote:
            break
        parar = False
        for pr in lote:
            criado = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
            if criado < desde:
                parar = True
                break
            if pr.get("merged_at"):
                prs.append(pr)
                if len(prs) >= max_prs:
                    break
        if parar:
            break
        pagina += 1
    return prs


def eh_bot(usuario: dict) -> bool:
    return usuario.get("type") == "Bot" or usuario.get("login", "").endswith("[bot]")


def analisar_reviews(sessao: requests.Session, pr: dict) -> dict:
    reviews = get(sessao, f"{pr['url']}/reviews", per_page=100).json()
    bots = sorted(
        {r["user"]["login"] for r in reviews if r["user"]["login"] in BOTS_REVISAO}
    )
    outros_bots = sorted(
        {
            r["user"]["login"]
            for r in reviews
            if eh_bot(r["user"]) and r["user"]["login"] not in BOTS_REVISAO
        }
    )
    humanas = sum(1 for r in reviews if not eh_bot(r["user"]))
    return {
        "bots_revisores": bots,
        "outros_bots": outros_bots,
        "revisoes_bot": len(bots),
        "revisoes_humanas": humanas,
    }


def completar_tamanhos(sessao: requests.Session, registros: list[dict]) -> None:
    def detalhe(registro: dict) -> dict:
        return get(
            sessao,
            f"{API}/repos/{registro['repo']}/pulls/{registro['pr_number']}",
        ).json()

    with ThreadPoolExecutor(max_workers=4) as pool:
        detalhes = list(pool.map(detalhe, registros))
    for registro, pr in zip(registros, detalhes):
        registro["adicoes"] = pr.get("additions")
        registro["delecoes"] = pr.get("deletions")
        registro["arquivos_alterados"] = pr.get("changed_files")


def coletar(repo: str, n_por_grupo: int, max_prs: int, dias: int) -> list[dict]:
    sessao = criar_sessao(carregar_token())
    limite = get(sessao, f"{API}/rate_limit").json()["resources"]["core"]
    print(f"Rate limit: {limite['remaining']}/{limite['limit']} requisições restantes.")

    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    prs = listar_prs_mergeados(sessao, repo, desde, max_prs)
    print(f"PRs mergeados encontrados nos últimos {dias} dias: {len(prs)}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        infos = list(pool.map(lambda pr: analisar_reviews(sessao, pr), prs))

    registros = []
    for pr, info in zip(prs, infos):
        if eh_bot(pr["user"]):
            continue  # PRs abertos por bots (dependabot, vercel etc.) são outra população
        aberto = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        mergeado = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
        horas = (mergeado - aberto).total_seconds() / 3600
        if horas < 5 / 60:  # descarta merge automático em menos de 5 minutos
            continue
        grupo = "com_bot" if info["revisoes_bot"] else "sem_bot"
        autor = pr["user"]["login"]
        registros.append(
            {
                "repo": repo,
                "pr_number": pr["number"],
                "grupo": grupo,
                "tempo_merge_horas": round(horas, 4),
                "aberto_em": pr["created_at"],
                "mergeado_em": pr["merged_at"],
                "autor": autor,
                "tipo_autor": pr["user"]["type"],
                "revisoes_bot": info["revisoes_bot"],
                "revisoes_humanas": info["revisoes_humanas"],
                "bots_revisores": ";".join(info["bots_revisores"]),
                "outros_bots": ";".join(info["outros_bots"]),
                "adicoes": pr.get("additions"),
                "delecoes": pr.get("deletions"),
                "arquivos_alterados": pr.get("changed_files"),
            }
        )

    # Amostra reproduzível por grupo, mantendo a ordem cronológica no CSV.
    rng = make_rng()
    amostra = []
    for grupo in ("com_bot", "sem_bot"):
        do_grupo = [r for r in registros if r["grupo"] == grupo]
        print(f"Grupo {grupo}: {len(do_grupo)} PRs disponíveis.")
        if len(do_grupo) > n_por_grupo:
            indices = sorted(rng.choice(len(do_grupo), size=n_por_grupo, replace=False))
            do_grupo = [do_grupo[i] for i in indices]
        elif len(do_grupo) < n_por_grupo:
            print(f"  AVISO: menos de {n_por_grupo} PRs em {grupo}; usando todos.")
        amostra.extend(do_grupo)

    amostra.sort(key=lambda r: r["mergeado_em"])
    print("Buscando tamanho dos PRs amostrados...")
    completar_tamanhos(sessao, amostra)
    return amostra


def salvar(registros: list[dict], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = list(registros[0].keys()) if registros else []
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(registros)
    print(f"CSV salvo em {destino} ({len(registros)} linhas).")


def resumo(registros: list[dict]) -> None:
    print("\nResumo da amostra:")
    for grupo in ("com_bot", "sem_bot"):
        tempos = [r["tempo_merge_horas"] for r in registros if r["grupo"] == grupo]
        if not tempos:
            continue
        media = statistics.mean(tempos)
        mediana = statistics.median(tempos)
        print(
            f"  {grupo:<8} n={len(tempos):>2} "
            f"mediana={mediana:7.2f}h média={media:7.2f}h "
            f"min={min(tempos):.2f}h max={max(tempos):.2f}h"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="supabase/supabase")
    parser.add_argument("--n-por-grupo", type=int, default=35)
    parser.add_argument("--max-prs", type=int, default=160)
    parser.add_argument("--dias", type=int, default=365)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args()

    registros = coletar(args.repo, args.n_por_grupo, args.max_prs, args.dias)
    salvar(registros, args.saida)
    resumo(registros)


if __name__ == "__main__":
    main()
