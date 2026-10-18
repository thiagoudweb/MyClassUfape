#!/usr/bin/env python3
"""SAC — Sistema de Aprendizagem Contínua: CLI determinístico do harness.

O modelo ensina, pergunta e corrige. Este script cuida do que precisa ser
exato e auditável: timestamps reais, agendamento de revisões, estado de
domínio, validação e gravação verificada.

Fonte de verdade: disciplinas/<slug>/dados/eventos.jsonl (append-only).
Os arquivos Markdown de memória são VISÕES geradas por `render`.
Somente biblioteca padrão (Python 3.9+).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

try:  # trava de arquivo: fcntl (Linux/macOS) ou msvcrt (Windows); só biblioteca padrão
    import fcntl
except ImportError:
    fcntl = None
try:
    import msvcrt
except ImportError:
    msvcrt = None

ROOT = Path(os.environ.get("SAC_ROOT") or Path(__file__).resolve().parent.parent)
DISC_DIR = ROOT / "disciplinas"

CFG_PADRAO = {
    "limiar_dominio": 0.8,
    "limiar_critico_minimo": 0.6,
    "escada_dias": [1, 3, 7, 14, 30, 60],
    "janela_dominio": 3,
    "min_dias_consistencia": 7,
    "margem_prova_dias": 2,
    "horas_sessao_obsoleta": 12,
    "min_questoes_distintas": 2,   # questões CADASTRADAS distintas na janela de domínio
    "confianca_alta": 4,           # calibração: confiança >= este valor...
    "desempenho_baixo": 0.5,       # ...com pontuação <= este valor
}
TRAVA_TIMEOUT = float(os.environ.get("SAC_LOCK_TIMEOUT", "20"))
TIPOS_TENTATIVA = ["reconhecimento", "recuperacao", "explicacao", "aplicacao", "transferencia"]
TIPOS_ERRO = ["lacuna_conceitual", "confusao_conceitos", "erro_procedimento", "erro_calculo",
              "interpretacao_incorreta", "esquecimento", "aplicacao_inadequada",
              "justificativa_insuficiente"]
FORMATOS = ["multipla_escolha", "resposta_curta", "explicacao", "verdadeiro_falso", "associacao",
            "problema", "caso", "corrigir_erro", "cumulativa", "transferencia"]
ORIGENS_DATA = ["oficial", "confirmada_estudante", "estimada", "desconhecida"]
TIPOS_DATA = ["prova", "entrega", "outro"]
TIPOS_PENDENCIA = ["duvida", "conflito", "operacional", "fonte"]
ESTADOS = {
    "nao_avaliado": "Não avaliado", "nao_iniciado": "Não iniciado", "em_estudo": "Em estudo",
    "compreensao_inicial": "Compreensão inicial", "em_consolidacao": "Em consolidação",
    "provisoriamente_dominado": "Provisoriamente dominado",
    "dominio_consistente": "Domínio consistente", "revisao_necessaria": "Revisão necessária",
}
RISCO_ROTULO = {"sob_controle": "Sob controle", "atencao_necessaria": "Atenção necessária",
                "atraso_provavel": "Atraso provável", "atraso_confirmado": "Atraso confirmado",
                "indeterminado": "Indeterminado"}
RE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")


class ErroSAC(Exception):
    """Erro de uso ou de dados (exit 1)."""


class ErroGravacao(Exception):
    """Falha de gravação ou de verificação da gravação (exit 2)."""


# ----------------------------------------------------------------- utilidades
def agora():
    v = os.environ.get("SAC_NOW")  # somente para testes
    if v:
        return datetime.fromisoformat(v).astimezone().replace(microsecond=0)
    return datetime.now().astimezone().replace(microsecond=0)


def data_de(ts):
    return datetime.fromisoformat(ts).date()


def minutos(a, b):
    return round((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 60, 1)


def pct(x):
    return "—" if x is None else f"{round(x * 100)}%"


def media(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def cel(s):
    return str(s if s is not None else "—").replace("|", "\\|").replace("\n", " ")


def tabela(cab, linhas):
    if not linhas:
        return "_Sem registros._\n"
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    out += ["| " + " | ".join(cel(c) for c in l) + " |" for l in linhas]
    return "\n".join(out) + "\n"


def escrever_verificado(path, texto):
    """Grava de forma atômica e relê para confirmar. Nunca finge sucesso."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        if path.read_text(encoding="utf-8") != texto:
            raise ErroGravacao(f"conteúdo gravado difere do esperado: {path}")
    except OSError as e:
        raise ErroGravacao(f"{path}: {e}")


def iso_data(s, campo="data"):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        raise ErroSAC(f"{campo} inválida (use AAAA-MM-DD): {s!r}")


def checar_id(s, campo):
    if not s or not RE_ID.match(s):
        raise ErroSAC(f"{campo} inválido (minúsculas, números, - _ .): {s!r}")
    return s


# ------------------------------------------------------------------ disciplina
@contextmanager
def trava_disciplina(D):
    """Trava exclusiva por disciplina, mantida durante todo o ciclo ler → calcular → gravar.

    Serializa execuções simultâneas (duas janelas do agente, por exemplo) para que ids de eventos,
    questões e pendências não colidam. O SO libera a trava se o processo morrer (sem trava órfã).
    """
    caminho = D.dir / "dados" / ".sac.lock"
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        f = open(caminho, "a+b")
    except OSError as e:
        print(f"AVISO: sem trava de escrita ({e}); não rode duas execuções ao mesmo tempo.", file=sys.stderr)
        yield
        return
    try:
        if fcntl is None and msvcrt is None:
            yield
            return
        if msvcrt is not None and f.seek(0, 2) == 0:
            f.write(b"0")
            f.flush()
        limite = time.monotonic() + TRAVA_TIMEOUT
        while True:
            try:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() > limite:
                    raise ErroGravacao(f"outra execução do sac.py manteve a disciplina travada por mais de "
                                       f"{TRAVA_TIMEOUT:.0f} s ({caminho}); nada foi gravado")
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                else:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
    finally:
        f.close()


def resolver_disc(slug):
    slug = slug or os.environ.get("SAC_DISC")
    if not slug:
        ex = sorted(p.parent.name for p in DISC_DIR.glob("*/config.json"))
        if len(ex) == 1:
            slug = ex[0]
        elif not ex:
            raise ErroSAC("nenhuma disciplina. Rode: sac.py nova <slug> --nome \"...\"")
        else:
            raise ErroSAC("várias disciplinas; use -d <slug>: " + ", ".join(ex))
    checar_id(slug, "slug")
    return Disc(slug)


class Disc:
    def __init__(self, slug):
        self.slug = slug
        self.dir = DISC_DIR / slug
        self.log = self.dir / "dados" / "eventos.jsonl"
        if not (self.dir / "config.json").exists():
            raise ErroSAC(f"disciplina '{slug}' não existe (falta config.json)")

    def config(self):
        try:
            c = json.loads((self.dir / "config.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise ErroSAC(f"config.json ilegível: {e}")
        return {**CFG_PADRAO, **c}

    def eventos(self):
        if not self.log.exists():
            return []
        evs = []
        try:
            linhas = self.log.read_text(encoding="utf-8").split("\n")
        except OSError as e:
            raise ErroGravacao(f"não consegui ler {self.log}: {e}")
        for n, l in enumerate(linhas, 1):
            if not l.strip():
                continue
            try:
                evs.append(json.loads(l))
            except json.JSONDecodeError as e:
                raise ErroSAC(f"eventos.jsonl linha {n} corrompida: {e}. Nada foi alterado. Restaure seu backup/git "
                                f"ou corrija/remova só essa linha (o resto do histórico é preservado) e rode `validar`")
        return evs

    def anexar(self, _evento, **campos):
        evs = self.eventos()
        ev = {"id": f"E{len(evs) + 1:06d}", "ts": agora().isoformat(), "evento": _evento}
        ev.update({k: v for k, v in campos.items() if v is not None})
        linha = json.dumps(ev, ensure_ascii=False)
        try:
            self.log.parent.mkdir(parents=True, exist_ok=True)
            if self.log.exists() and self.log.stat().st_size and not self.log.read_bytes().endswith(b"\n"):
                raise ErroGravacao("eventos.jsonl não termina em quebra de linha (corrompido)")
            with open(self.log, "a", encoding="utf-8", newline="\n") as f:
                f.write(linha + "\n")
                f.flush()
                os.fsync(f.fileno())
            ultima = self.log.read_text(encoding="utf-8").rstrip("\n").split("\n")[-1]
        except OSError as e:
            raise ErroGravacao(f"{self.log}: {e}")
        if ultima != linha:
            raise ErroGravacao("a leitura de volta não confere com o evento gravado")
        return ev

    def estado(self, hoje=None):
        evs = self.eventos()
        hoje = hoje or agora().date()
        return calcular(evs, self.config(), hoje), evs

    def renderizar(self, hoje=None):
        S, evs = self.estado(hoje)
        hoje = hoje or agora().date()
        ult = evs[-1] if evs else {"id": "E000000", "ts": "—"}
        escritos = []
        for rel, txt in visoes(self, S, hoje, ult).items():
            escrever_verificado(self.dir / rel, txt)
            escritos.append(rel)
        return escritos


# -------------------------------------------------------------- cálculo (puro)
def novo_topico(tid, ordem):
    return {"id": tid, "nome": tid, "critico": False, "prereqs": [], "fonte": None,
            "previsto_ate": None, "previsto_origem": None, "ordem": ordem, "declarado": None,
            "tentativas": [], "passo": None, "proxima_base": None, "proxima": None,
            "ultima_data": None}


def independente(a):
    return a["tipo"] != "reconhecimento" and a.get("independente", True)


def agendar(top, a, cfg):
    """Escada de revisão determinística. O modelo informa a qualidade; o código agenda."""
    escada = cfg["escada_dias"]
    d, s, passo = a["_data"], a["pontuacao"], top["passo"]
    if s >= cfg["limiar_dominio"]:
        if independente(a):
            if passo is None:
                novo = 0
            elif top["proxima_base"] is None or d >= top["proxima_base"]:
                novo = min(passo + 1, len(escada) - 1)
            else:
                novo = passo  # revisão antecipada não avança o intervalo
        else:
            novo = passo if passo is not None else 0
    elif s >= 0.5:
        novo = passo if passo is not None else 0
    else:
        novo = 0  # esquecimento/erro: volta ao início da escada
    top["passo"] = novo
    top["ultima_data"] = d
    top["proxima_base"] = d + timedelta(days=escada[novo])


def estado_topico(t, cfg, hoje):
    todas = t["tentativas"]
    if not todas:
        return (t["declarado"] or "nao_avaliado"), ["sem tentativas registradas"]
    ind = [a for a in todas if independente(a)]
    if not ind:
        return "em_estudo", ["só há tentativas por reconhecimento ou com ajuda"]
    j, lim = cfg["janela_dominio"], cfg["limiar_dominio"]
    ult = ind[-j:]
    m = media(a["pontuacao"] for a in ult)
    motivos = [f"{len(ind)} tentativa(s) independente(s); média das últimas {len(ult)}: {pct(m)}"]
    estado = "compreensao_inicial" if len(ind) < 2 else "em_consolidacao"
    prov = False
    if len(ind) >= j:
        falhas = []
        if m < lim:
            falhas.append(f"média abaixo de {pct(lim)}")
        if not any(a["tipo"] in ("explicacao", "aplicacao", "transferencia") and a["pontuacao"] >= lim
                   for a in ult):
            falhas.append("falta explicação/aplicação/transferência ≥ limiar")
        if t["critico"] and min(a["pontuacao"] for a in ult) < cfg["limiar_critico_minimo"]:
            falhas.append("tópico crítico com tentativa abaixo do mínimo essencial")
        nq, minq = len({a["questao"] for a in ult if a.get("questao")}), cfg["min_questoes_distintas"]
        if nq < minq:
            falhas.append("evidência de uma única questão cadastrada" if nq == 1 else
                          f"sem questões cadastradas distintas ({nq} de {minq}); cite --questao nas tentativas")
        prov = not falhas
        if falhas:
            motivos.append("domínio não atendido: " + "; ".join(falhas))
    else:
        motivos.append(f"menos de {j} tentativas independentes para avaliar domínio")
    if prov:
        estado = "provisoriamente_dominado"
        boas = sorted(a["_data"] for a in ind if a["pontuacao"] >= lim)
        if boas and (boas[-1] - boas[0]).days >= cfg["min_dias_consistencia"]:
            estado = "dominio_consistente"
        else:
            motivos.append(f"consistência exige acertos com ≥{cfg['min_dias_consistencia']} dias de intervalo")
        if t["proxima"] and t["proxima"] < hoje:
            estado = "revisao_necessaria"
            motivos.append("revisão vencida")
    elif len(ind) >= 2 and ind[-1]["pontuacao"] < 0.5:
        estado = "revisao_necessaria"
        motivos.append("última tentativa independente abaixo de 50%")
    return estado, motivos


def calcular(evs, cfg, hoje):
    S = {"topicos": {}, "questoes": {}, "sessoes": {}, "ordem_sessoes": [], "datas": {},
         "fontes": {}, "pendencias": {}, "tentativas": [], "problemas": [], "aberta": None}
    T, SS = S["topicos"], S["sessoes"]
    for ev in evs:
        t = ev.get("evento")
        sid = ev.get("sessao")
        if sid in SS and t != "sessao_abandonada":
            SS[sid]["ultimo"] = ev["ts"]  # o evento de abandono não conta como atividade
        if t == "topico":
            d = T.setdefault(ev["topico"], novo_topico(ev["topico"], len(T)))
            for k in ("nome", "critico", "prereqs", "fonte", "previsto_ate", "previsto_origem"):
                if ev.get(k) is not None:
                    d[k] = ev[k]
        elif t == "marca":
            if ev["topico"] in T:
                T[ev["topico"]]["declarado"] = ev["estado"]
            else:
                S["problemas"].append(f"{ev['id']}: marca em tópico inexistente '{ev['topico']}'")
        elif t == "questao":
            if ev["topico"] not in T:
                S["problemas"].append(f"{ev['id']}: questão {ev['questao']} em tópico inexistente '{ev['topico']}'")
            S["questoes"][ev["questao"]] = ev
        elif t == "tentativa":
            top = T.get(ev["topico"])
            if top is None:
                S["problemas"].append(f"{ev['id']}: tentativa em tópico inexistente '{ev['topico']}'")
                continue
            if ev.get("questao") and ev["questao"] not in S["questoes"]:
                S["problemas"].append(f"{ev['id']}: tentativa cita questão inexistente '{ev['questao']}'")
            a = dict(ev)
            a["_data"] = data_de(ev["ts"])
            top["tentativas"].append(a)
            S["tentativas"].append(a)
            agendar(top, a, cfg)
            if sid in SS and ev["topico"] not in SS[sid]["topicos"]:
                SS[sid]["topicos"].append(ev["topico"])
            if sid in SS:
                SS[sid]["n_tentativas"] += 1
        elif t == "sessao_inicio":
            SS[sid] = {"id": sid, "inicio": ev["ts"], "objetivo": ev.get("objetivo"), "status": "aberta",
                       "pausas": [], "topicos": [], "n_tentativas": 0, "ultimo": ev["ts"],
                       "checkpoints": [], "fim": None, "resumo": None, "proximo": None,
                       "demonstrado": None, "concluida": None, "efetivo": None}
            S["ordem_sessoes"].append(sid)
            S["aberta"] = sid
        elif sid in SS:
            s = SS[sid]
            if t == "sessao_pausa":
                s["pausas"].append([ev["ts"], None])
            elif t == "sessao_retomada" and s["pausas"]:
                s["pausas"][-1][1] = ev["ts"]
            elif t == "sessao_checkpoint":
                s["checkpoints"].append(ev)
                for tp in ev.get("topicos", []):
                    if tp not in s["topicos"]:
                        s["topicos"].append(tp)
            elif t == "sessao_fim":
                s.update(status="encerrada", fim=ev["ts"], resumo=ev.get("resumo"),
                         proximo=ev.get("proximo"), demonstrado=ev.get("demonstrado"),
                         concluida=ev.get("concluida"), efetivo=ev.get("minutos_efetivos"))
                for tp in ev.get("topicos", []):
                    if tp not in s["topicos"]:
                        s["topicos"].append(tp)
                S["aberta"] = None
            elif t == "sessao_abandonada":
                s.update(status="abandonada", fim=ev.get("ultimo_registro") or s["ultimo"])
                S["aberta"] = None
        elif t == "data":
            S["datas"][ev["titulo"].lower()] = ev
        elif t == "fonte":
            S["fontes"][ev["fonte"]] = ev
        elif t == "pendencia":
            S["pendencias"][ev["pendencia"]] = dict(ev, aberta=True)
        elif t == "pendencia_resolvida" and ev["pendencia"] in S["pendencias"]:
            S["pendencias"][ev["pendencia"]].update(aberta=False, resolucao=ev.get("nota"))
    # durações
    for s in SS.values():
        fim = s["fim"] or s["ultimo"]
        s["relogio_min"] = minutos(s["inicio"], fim)
        if s["status"] == "abandonada":
            s["ativo_min"] = None
        else:
            pm = sum(minutos(a, b or fim) for a, b in s["pausas"])
            s["pausas_min"] = round(pm, 1)
            s["ativo_min"] = round(s["relogio_min"] - pm, 1)
    # provas e teto de revisão
    provas = []
    for d in S["datas"].values():
        try:
            dd = date.fromisoformat(d["data"])
        except ValueError:
            S["problemas"].append(f"{d['id']}: data inválida {d['data']!r}")
            continue
        if d["tipo"] == "prova" and d["origem"] != "desconhecida" and dd >= hoje:
            provas.append(dd)
    provas.sort()
    S["provas_futuras"] = provas
    for top in T.values():
        top["proxima"] = top["proxima_base"]
        top["limitada_por_prova"] = False
        if top["proxima_base"] and provas:
            lim = max(top["ultima_data"] + timedelta(days=1), provas[0] - timedelta(days=cfg["margem_prova_dias"]))
            if lim < top["proxima"]:
                top["proxima"], top["limitada_por_prova"] = lim, True
        top["estado"], top["motivos"] = estado_topico(top, cfg, hoje)
    return S


def calcular_risco(S, hoje):
    tops = list(S["topicos"].values())
    if not tops:
        return "indeterminado", ["nenhum tópico cadastrado"]
    if not any(t["previsto_ate"] for t in tops):
        return "indeterminado", ["nenhum tópico tem 'previsto_ate': cronograma sem datas, não estimado"]
    ev = []
    devidos = [t for t in tops if t["previsto_ate"] and date.fromisoformat(t["previsto_ate"]) <= hoje]
    atras = [t for t in devidos if t["estado"] == "nao_iniciado" and date.fromisoformat(t["previsto_ate"]) < hoje]
    fracos = [t for t in devidos if t["estado"] in ("em_estudo", "compreensao_inicial", "revisao_necessaria")]
    sem_dado = [t for t in devidos if t["estado"] == "nao_avaliado"]
    venc = [t for t in tops if t["proxima"] and t["proxima"] < hoje]
    prova14 = [p for p in S["provas_futuras"] if (p - hoje).days <= 14]
    for t in atras:
        ev.append(f"{t['id']}: previsto até {t['previsto_ate']} ({t['previsto_origem'] or 'origem não informada'}) e declarado não iniciado")
    for t in fracos:
        ev.append(f"{t['id']}: previsto até {t['previsto_ate']}, estado '{ESTADOS[t['estado']]}'")
    for t in sem_dado:
        ev.append(f"{t['id']}: previsto até {t['previsto_ate']}, sem nenhuma evidência (não é prova de atraso)")
    if venc:
        ev.append(f"{len(venc)} revisão(ões) vencida(s)")
    if prova14:
        ev.append(f"prova em {(prova14[0] - hoje).days} dia(s) ({prova14[0]})")
    if atras:
        classe = "atraso_confirmado"
    elif fracos and prova14:
        classe = "atraso_provavel"
    elif fracos or sem_dado or len(venc) >= 3:
        classe = "atencao_necessaria"
    else:
        classe = "sob_controle"
        ev.append("tópicos com prazo vencido estão em consolidação ou além, ou ainda não há prazos vencidos")
    return classe, ev


NOVOS = ("nao_avaliado", "nao_iniciado")
EM_ANDAMENTO = ("em_estudo", "compreensao_inicial", "em_consolidacao", "revisao_necessaria")


def _prazo(t):
    return date.fromisoformat(t["previsto_ate"]) if t["previsto_ate"] else None


def _raiz_pendente(t, T, visto=None):
    """Se o tópico tem pré-requisito ainda sem evidência, a ação começa por esse pré-requisito."""
    visto = visto if visto is not None else set()
    visto.add(t["id"])
    for p in t["prereqs"]:
        pt = T.get(p)
        if pt and p not in visto and pt["estado"] in NOVOS:
            return _raiz_pendente(pt, T, visto)
    return t


def sugerir_proxima(S, hoje):
    """Ordem: revisão vencida → prazo vencido (o mais antigo) → em andamento → novo (menor prazo)."""
    T = S["topicos"]
    tops = sorted(T.values(), key=lambda t: t["ordem"])
    if not tops:
        return "Sem tópicos cadastrados: faça a ingestão da ementa (skill sac-ingestao)."
    venc = sorted([t for t in tops if t["proxima"] and t["proxima"] <= hoje],
                  key=lambda t: (not t["critico"], t["proxima"]))
    if venc:
        t = venc[0]
        return f"Revisão por recuperação ativa de '{t['id']}' (devida desde {t['proxima']})."
    atrasados = sorted([t for t in tops if _prazo(t) and _prazo(t) < hoje
                        and t["estado"] not in ("provisoriamente_dominado", "dominio_consistente")],
                       key=lambda t: (_prazo(t), t["ordem"]))
    if atrasados:
        t = atrasados[0]
        alvo = _raiz_pendente(t, T)
        origem = t["previsto_origem"] or "origem não informada"
        if alvo is not t:
            return (f"Prazo vencido de '{t['id']}' (previsto até {t['previsto_ate']}, {origem}): "
                    f"comece pelo pré-requisito '{alvo['id']}', ainda sem evidência.")
        verbo = {"nao_avaliado": "Diagnóstico inicial de", "nao_iniciado": "Começar"}.get(t["estado"], "Continuar")
        return f"{verbo} '{t['id']}': prazo vencido em {t['previsto_ate']} ({origem})."
    emand = [t for t in tops if t["estado"] in EM_ANDAMENTO]
    if emand:
        return f"Continuar '{emand[0]['id']}' ({ESTADOS[emand[0]['estado']]}): recuperação breve e depois avançar."
    novos = sorted([t for t in tops if t["estado"] in NOVOS], key=lambda t: (_prazo(t) or date.max, t["ordem"]))
    if novos:
        alvo = _raiz_pendente(novos[0], T)
        return f"Diagnóstico inicial de '{alvo['id']}' antes de ensinar."
    return "Todos os tópicos cadastrados estão em provisório ou além: simulado cumulativo."


def indicadores(S, hoje):
    tops = list(S["topicos"].values())
    n = len(tops)
    ind = [a for a in S["tentativas"] if independente(a)]
    comp = [t for t in tops if t["proxima"]]
    venc = [t for t in comp if t["proxima"] < hoje]
    return {
        "Tópicos cadastrados": str(n),
        "Vinculados a alguma fonte (declarado, não prova cobertura da ementa)": f"{sum(1 for t in tops if t['fonte'])}/{n}",
        "Progresso de estudo (com qualquer evidência além de 'não avaliado/não iniciado')":
            f"{sum(1 for t in tops if t['estado'] not in ('nao_avaliado', 'nao_iniciado'))}/{n}",
        "Domínio demonstrado (provisório ou consistente)":
            f"{sum(1 for t in tops if t['estado'] in ('provisoriamente_dominado', 'dominio_consistente'))}/{n}"
            f" (consistente: {sum(1 for t in tops if t['estado'] == 'dominio_consistente')})",
        "Revisões em dia": f"{len(comp) - len(venc)}/{len(comp)} agendadas",
        "Desempenho (tentativas independentes, últimas 10)": f"{pct(media(a['pontuacao'] for a in ind[-10:]))} em {len(ind[-10:])} tentativa(s)",
        "Próximos prazos": ", ".join(f"{p} (em {(p - hoje).days} d)" for p in S["provas_futuras"][:3]) or "nenhuma prova futura registrada",
    }


# ------------------------------------------------------------------- visões
def cabecalho(hoje, ult):
    return (f"<!-- sac:hoje={hoje} ultimo_evento={ult['id']} -->\n"
            "<!-- GERADO por scripts/sac.py a partir de dados/eventos.jsonl. "
            "Não edite à mão: use o CLI e rode `render`. -->\n\n")


def tempo_total(S):
    enc = [s for s in S["sessoes"].values() if s["status"] == "encerrada"]
    return {
        "sessões encerradas": len(enc),
        "relógio decorrido (min)": round(sum(s["relogio_min"] for s in enc), 1),
        "timer ativo = relógio − pausas declaradas (min)": round(sum(s["ativo_min"] for s in enc), 1),
        "estudo efetivo declarado pelo aluno (min)": round(sum(s["efetivo"] or 0 for s in enc), 1),
        "sessões com efetivo declarado": sum(1 for s in enc if s["efetivo"] is not None),
    }


def v_estado(D, S, hoje, ult):
    cfg, nome = D.config(), D.config().get("nome", D.slug)
    SS = S["sessoes"]
    enc = [SS[i] for i in S["ordem_sessoes"] if SS[i]["status"] == "encerrada"]
    o = [f"# Estado atual — {nome}\n",
         f"Dados até o evento **{ult['id']}** ({ult['ts']}). Datas calculadas em relação a **{hoje}**.\n",
         f"## Objetivo\n{cfg.get('objetivo') or '_não informado (desconhecido)_'}\n", "## Última sessão concluída"]
    if enc:
        s = enc[-1]
        o.append(f"{s['id']} · {s['inicio']} → {s['fim']} · concluída: {s['concluida']}\n\n- Resumo: {s['resumo']}\n"
                 f"- Demonstrado: {s['demonstrado'] or '—'}\n- Próximo (registrado no encerramento): {s['proximo']}\n")
    else:
        o.append("_Nenhuma sessão encerrada ainda._\n")
    if S["aberta"]:
        s = SS[S["aberta"]]
        o.append(f"> **Sessão aberta:** {s['id']} desde {s['inicio']} — {s['objetivo']}\n")
    ab = [s for s in SS.values() if s["status"] == "abandonada"]
    if ab:
        o.append(f"> {len(ab)} sessão(ões) abandonada(s) sem encerramento formal: {', '.join(s['id'] for s in ab)}. Dados parciais.\n")
    o.append("## Em andamento")
    emand = [t for t in S["topicos"].values() if t["estado"] in ("em_estudo", "compreensao_inicial", "em_consolidacao", "revisao_necessaria")]
    o.append("\n".join(f"- {t['id']} — {ESTADOS[t['estado']]}" for t in emand) or "_Nenhum tópico em andamento._")
    dem = [a for a in S["tentativas"] if independente(a) and a["pontuacao"] >= cfg["limiar_dominio"]]
    o.append("\n## Último ponto efetivamente demonstrado")
    o.append(f"{dem[-1]['topico']} — {dem[-1]['tipo']}, {pct(dem[-1]['pontuacao'])} em {dem[-1]['_data']} ({dem[-1]['id']})\n"
             if dem else "_Nenhuma demonstração independente ≥ limiar registrada._\n")
    o.append("## Próxima ação")
    o.append(f"- Sugerida pelo cálculo: {sugerir_proxima(S, hoje)}")
    o.append(f"- Registrada pelo agente no último encerramento: {enc[-1]['proximo'] if enc else '—'}\n")
    o.append("## Dúvidas e pendências abertas")
    pend = [p for p in S["pendencias"].values() if p["aberta"]]
    o.append("\n".join(f"- {p['pendencia']} [{p['categoria']}] {p['texto']}" for p in pend) or "_Nenhuma._")
    o.append("\n## Revisões")
    venc = sorted([t for t in S["topicos"].values() if t["proxima"] and t["proxima"] <= hoje], key=lambda t: t["proxima"])
    prox = sorted([t for t in S["topicos"].values() if t["proxima"] and hoje < t["proxima"] <= hoje + timedelta(days=7)], key=lambda t: t["proxima"])
    o.append("Vencidas/hoje: " + (", ".join(f"{t['id']} ({t['proxima']})" for t in venc) or "nenhuma"))
    o.append("Próximos 7 dias: " + (", ".join(f"{t['id']} ({t['proxima']})" for t in prox) or "nenhuma") + "\n")
    o.append("## Tempo acumulado (rótulos distintos, nunca somados entre si)")
    o.append("\n".join(f"- {k}: {v}" for k, v in tempo_total(S).items()) + "\n")
    o.append("## Indicadores (separados de propósito; não existe porcentagem única)")
    o.append("\n".join(f"- {k}: {v}" for k, v in indicadores(S, hoje).items()) + "\n")
    cl, evd = calcular_risco(S, hoje)
    o.append(f"## Risco de cronograma: {RISCO_ROTULO[cl]}")
    o.append("\n".join(f"- {e}" for e in evd) + "\n")
    conf = []
    if ab:
        conf.append("há sessões abandonadas (tempo e resultados podem estar incompletos)")
    if not S["datas"]:
        conf.append("nenhuma data acadêmica registrada")
    if not S["fontes"]:
        conf.append("nenhuma fonte registrada no manifesto")
    o.append("## Confiança das informações")
    o.append(("Reduzida: " + "; ".join(conf)) if conf else "Sem ressalvas estruturais detectadas (isso não valida o conteúdo acadêmico).")
    return "\n".join(o) + "\n"


def v_dominio(D, S, hoje, ult):
    linhas = []
    for t in sorted(S["topicos"].values(), key=lambda t: t["ordem"]):
        ind = [a for a in t["tentativas"] if independente(a)]
        linhas.append([t["id"], "sim" if t["critico"] else "não", ESTADOS[t["estado"]],
                       f"{len(ind)}/{len(t['tentativas'])}", pct(media(a["pontuacao"] for a in ind[-3:])),
                       t["tentativas"][-1]["_data"] if t["tentativas"] else "—",
                       (str(t["proxima"]) + (" (limitada por prova)" if t["limitada_por_prova"] else "")) if t["proxima"] else "—",
                       ", ".join(t["prereqs"]) or "—", "; ".join(t["motivos"])])
    return ("# Domínio por tópico\n\nEstados são evidências internas, não nota acadêmica.\n\n" +
            tabela(["Tópico", "Crítico", "Estado", "Indep./total", "Média últimas 3 indep.", "Última evidência",
                    "Próxima revisão", "Pré-requisitos", "Motivos"], linhas))


def v_revisoes(D, S, hoje, ult):
    L = []
    for t in S["topicos"].values():
        if not t["proxima"]:
            continue
        dias = (t["proxima"] - hoje).days
        sit = "VENCIDA" if dias < 0 else ("hoje" if dias == 0 else f"em {dias} d")
        L.append((not t["critico"], t["proxima"], [t["id"], t["proxima"], sit, "sim" if t["critico"] else "não",
                                                   ESTADOS[t["estado"]], f"passo {t['passo'] + 1}/{len(D.config()['escada_dias'])}"]))
    L.sort(key=lambda x: (x[1], x[0]))
    return ("# Revisões pendentes\n\nOrdem: data devida; crítico primeiro em empate. "
            "Agendamento calculado por código (escada em config.json), teto antes de provas.\n\n" +
            tabela(["Tópico", "Devida em", "Situação", "Crítico", "Estado", "Passo da escada"], [x[2] for x in L]))


def v_sessoes(D, S, hoje, ult):
    L = []
    for i in S["ordem_sessoes"]:
        s = S["sessoes"][i]
        rel = f"{s['relogio_min']}" + (" (mínimo)" if s["status"] != "encerrada" else "")
        L.append([s["id"], s["inicio"], s["fim"] or "—", s["status"], rel,
                  s["ativo_min"] if s["ativo_min"] is not None else "desconhecido",
                  s["efetivo"] if s["efetivo"] is not None else "não declarado", s["objetivo"],
                  ", ".join(s["topicos"]) or "—", s["concluida"] or "—", s["resumo"] or "—", s["proximo"] or "—"])
    return ("# Índice de sessões\n\nRelógio = início→fim. Ativo = relógio − pausas declaradas. "
            "Efetivo = informado pelo aluno. Sessão abandonada: fim = último registro confiável.\n\n" +
            tabela(["ID", "Início", "Fim", "Status", "Relógio (min)", "Ativo (min)", "Efetivo (min)", "Objetivo",
                    "Tópicos", "Concluída", "Resumo", "Próximo"], L))


def v_tentativas(D, S, hoje, ult):
    L = [[a["id"], a["ts"], a.get("sessao") or "—", a["topico"], a.get("questao") or "—", a["tipo"],
          "sim" if independente(a) else "não", pct(a["pontuacao"]), a.get("confianca") or "—",
          a.get("erro") or "—", a.get("nota") or "—"] for a in S["tentativas"]]
    return "# Histórico de tentativas\n\nAppend-only: nada é apagado.\n\n" + tabela(
        ["Evento", "Quando", "Sessão", "Tópico", "Questão", "Tipo", "Independente", "Pontuação", "Confiança (1-5)", "Erro", "Nota"], L)


def v_banco(D, S, hoje, ult):
    L = []
    for q in S["questoes"].values():
        n = [a for a in S["tentativas"] if a.get("questao") == q["questao"]]
        L.append([q["questao"], q["topico"], q["formato"], q["dificuldade"], q["objetivo"], q["enunciado"],
                  q.get("fonte") or "sem fonte (conhecimento geral)", q.get("erros_alvo") or "—", len(n)])
    return ("# Banco de questões\n\nGabaritos e critérios ficam só em eventos.jsonl. Para consultar após a "
            "tentativa: `sac.py questao gabarito <ID>`.\n\n" +
            tabela(["ID", "Tópico", "Formato", "Dif.", "Objetivo", "Enunciado", "Fonte", "Erros-alvo", "Tentativas"], L))


def v_erros(D, S, hoje, ult):
    L = [[a["_data"], a["topico"], a.get("questao") or "—", a["erro"], pct(a["pontuacao"]), a.get("nota") or "—"]
         for a in S["tentativas"] if a.get("erro")]
    cont = {}
    for a in S["tentativas"]:
        if a.get("erro"):
            cont[(a["topico"], a["erro"])] = cont.get((a["topico"], a["erro"]), 0) + 1
    rec = [[k[0], k[1], v] for k, v in sorted(cont.items(), key=lambda x: -x[1]) if v >= 2]
    return ("# Catálogo de erros\n\nCausas são hipóteses do agente, não fatos, salvo confirmação do aluno.\n\n"
            "## Erros recorrentes (≥2 do mesmo tipo no mesmo tópico)\n" + tabela(["Tópico", "Tipo de erro", "Ocorrências"], rec) +
            "\n## Todos os erros registrados\n" + tabela(["Data", "Tópico", "Questão", "Erro", "Pontuação", "Nota"], L))


def v_dificuldades(D, S, hoje, ult):
    fracos = [[t["id"], ESTADOS[t["estado"]], pct(media(a["pontuacao"] for a in t["tentativas"] if independente(a)))]
              for t in S["topicos"].values() if t["estado"] == "revisao_necessaria" or
              (t["tentativas"] and (media(a["pontuacao"] for a in t["tentativas"] if independente(a)) or 1) < 0.6)]
    cfg = D.config()
    calib = [[a["id"], a["topico"], a["confianca"], pct(a["pontuacao"])]
             for a in S["tentativas"] if a.get("confianca") and a["confianca"] >= cfg["confianca_alta"]
             and a["pontuacao"] <= cfg["desempenho_baixo"]]
    prer = []
    for t in S["topicos"].values():
        if t["estado"] in ("em_estudo", "compreensao_inicial", "em_consolidacao"):
            for p in t["prereqs"]:
                pt = S["topicos"].get(p)
                if pt and pt["estado"] not in ("provisoriamente_dominado", "dominio_consistente", "em_consolidacao"):
                    prer.append([t["id"], p, ESTADOS[pt["estado"]]])
    return ("# Dificuldades recorrentes\n\n## Tópicos com desempenho baixo ou em revisão necessária\n" +
            tabela(["Tópico", "Estado", "Média indep."], fracos) +
            "\n## Confiança alta com desempenho baixo (calibração)\n" + tabela(["Evento", "Tópico", "Confiança", "Pontuação"], calib) +
            "\n## Pré-requisitos frágeis sob tópicos em andamento\n" + tabela(["Tópico", "Pré-requisito", "Estado do pré-requisito"], prer))


def v_evolucao(D, S, hoje, ult):
    sem = {}
    for a in S["tentativas"]:
        if independente(a):
            y, w, _ = a["_data"].isocalendar()
            sem.setdefault(f"{y}-W{w:02d}", []).append(a["pontuacao"])
    L = [[k, len(v), pct(media(v))] for k, v in sorted(sem.items())]
    return ("# Histórico de evolução\n\nMédia de tentativas independentes por semana ISO. "
            "Tendência não implica causa (método de estudo, dificuldade do conteúdo e acaso se misturam).\n\n" +
            tabela(["Semana", "Tentativas indep.", "Média"], L))


def v_datas(D, S, hoje, ult):
    L = [[d["titulo"], d["tipo"], d["data"], d["origem"], d.get("fonte") or "—", d.get("nota") or "—"]
         for d in sorted(S["datas"].values(), key=lambda d: d["data"])]
    return "# Calendário acadêmico\n\nToda data tem origem: oficial, confirmada_estudante, estimada ou desconhecida.\n\n" + tabela(
        ["Evento", "Tipo", "Data", "Origem", "Fonte", "Nota"], L)


def v_fontes(D, S, hoje, ult):
    L = [[f["fonte"], f["caminho"], f.get("tipo") or "—", f"v{f['versao']}", f["sha256"][:12], f["bytes"],
          f["paginas"] if f.get("paginas") is not None else "desconhecido (não verificado)",
          f.get("assuntos") or "—", f.get("nota") or "—"] for f in S["fontes"].values()]
    return "# Manifesto de fontes\n\nPáginas só aparecem quando verificadas por ferramenta.\n\n" + tabela(
        ["ID", "Arquivo", "Tipo", "Versão", "SHA-256", "Bytes", "Páginas", "Assuntos", "Nota"], L)


def v_pendencias(D, S, hoje, ult):
    L = [[p["pendencia"], p["categoria"], "aberta" if p["aberta"] else "resolvida", p["texto"], p.get("resolucao") or "—"]
         for p in S["pendencias"].values()]
    return "# Pendências e conflitos\n\n" + tabela(["ID", "Categoria", "Situação", "Texto", "Resolução"], L)


def v_cronograma(D, S, hoje, ult):
    cl, ev = calcular_risco(S, hoje)
    L = [[t["id"], t["previsto_ate"] or "—", t["previsto_origem"] or "—", ESTADOS[t["estado"]]]
         for t in sorted(S["topicos"].values(), key=lambda t: t["ordem"])]
    return (f"# Análise de cronograma\n\n**Classificação: {RISCO_ROTULO[cl]}**\n\nEvidências:\n" +
            "\n".join(f"- {e}" for e in ev) +
            "\n\nRegras: atraso confirmado = prazo vencido com tópico declarado não iniciado; atraso provável = "
            "tópico com prazo vencido ainda fraco e prova em ≤14 dias; atenção = prazo vencido fraco/sem dado ou ≥3 revisões "
            "vencidas. Tópico sem prazo vencido nunca conta como atraso.\n\n" +
            tabela(["Tópico", "Previsto até", "Origem do prazo", "Estado"], L))


def visoes(D, S, hoje, ult):
    cab = cabecalho(hoje, ult)
    f = {"04_MEMORIA_DO_ALUNO/estado_atual.md": v_estado, "04_MEMORIA_DO_ALUNO/dominio_por_topico.md": v_dominio,
         "04_MEMORIA_DO_ALUNO/revisoes_pendentes.md": v_revisoes, "04_MEMORIA_DO_ALUNO/catalogo_de_erros.md": v_erros,
         "04_MEMORIA_DO_ALUNO/dificuldades_recorrentes.md": v_dificuldades,
         "04_MEMORIA_DO_ALUNO/historico_de_evolucao.md": v_evolucao, "05_SESSOES/indice_de_sessoes.md": v_sessoes,
         "06_AVALIACOES/historico_de_tentativas.md": v_tentativas, "06_AVALIACOES/banco_de_questoes.md": v_banco,
         "02_MAPA_DA_DISCIPLINA/calendario_academico.md": v_datas, "01_FONTES/manifesto_de_fontes.md": v_fontes,
         "09_VALIDACAO/pendencias_e_conflitos.md": v_pendencias, "07_PLANEJAMENTO/analise_de_cronograma.md": v_cronograma}
    return {rel: cab + fn(D, S, hoje, ult) for rel, fn in f.items()}


# ------------------------------------------------------------------- comandos
def pos_gravacao(D, ev, extra=""):
    print(f"[verificado] gravado {ev['id']} ({ev['evento']}) em {ev['ts']}{extra}")
    try:
        D.renderizar()
        print("[verificado] visões Markdown atualizadas")
    except ErroGravacao as e:
        print(f"ATENÇÃO: evento gravado, mas as visões falharam: {e}\n"
              "Corrija e rode `render`. Não declare as visões como atualizadas.", file=sys.stderr)
        raise


def exigir_sessao(S):
    if not S["aberta"]:
        raise ErroSAC("não há sessão aberta. Use: sac.py sessao iniciar --objetivo \"...\"")
    return S["aberta"]


def cmd_nova(a):
    slug = checar_id(a.slug, "slug")
    d = DISC_DIR / slug
    if (d / "config.json").exists():
        raise ErroSAC(f"disciplina '{slug}' já existe")
    for sub in ["00_ORIENTACAO", "01_FONTES", "02_MAPA_DA_DISCIPLINA", "03_CONHECIMENTO/topicos", "04_MEMORIA_DO_ALUNO",
                "05_SESSOES", "06_AVALIACOES", "07_PLANEJAMENTO", "08_RELATORIOS", "09_VALIDACAO", "dados"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    cfg = {"nome": a.nome, "objetivo": a.objetivo or "", "idioma": "pt-BR", **CFG_PADRAO}
    escrever_verificado(d / "config.json", json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    stubs = {
        "00_ORIENTACAO/preferencias_de_estudo.md": "# Preferências de estudo\n\nSó registre o que o aluno disse. Origem de cada item entre parênteses.\n\n- Horas semanais disponíveis: _desconhecido_\n- Melhores horários: _desconhecido_\n- Formatos preferidos: _desconhecido_\n",
        "02_MAPA_DA_DISCIPLINA/ementa.md": "# Ementa\n\n_Pendente de ingestão. Copie unidades e tópicos com a fonte (arquivo e página verificados)._\n",
        "02_MAPA_DA_DISCIPLINA/mapa_conceitual.md": "# Mapa conceitual\n\n_Pendente de ingestão._\n",
        "02_MAPA_DA_DISCIPLINA/pre_requisitos.md": "# Pré-requisitos\n\n_Pendente. Mantenha em sincronia com `--prereq` dos tópicos cadastrados._\n",
        "03_CONHECIMENTO/indice_de_conteudos.md": "# Índice de conteúdos\n\n_Liste aqui onde está cada tópico/nota elaborada, sem resumos extensos._\n",
        "04_MEMORIA_DO_ALUNO/perfil_de_aprendizagem.md": "# Perfil de aprendizagem\n\nSeparar: **observações do aluno**, **resultados objetivos**, **inferências do agente** (com grau de confiança).\n\n## Observações do aluno\n_Nenhuma._\n\n## Resultados objetivos\n_Ver dominio_por_topico.md._\n\n## Inferências do agente\n_Nenhuma._\n",
        "06_AVALIACOES/rubricas_de_correcao.md": "# Rubricas de correção\n\nPontuação 0–1 por tentativa.\n\n- 1,0: correto, bem justificado, independente.\n- 0,8: correto, justificativa incompleta.\n- 0,5–0,7: parcialmente correto; ideia central presente.\n- 0,2–0,4: ideia central ausente ou confusão de conceitos.\n- 0: sem resposta útil.\n\nRubricas específicas por tópico: acrescentar abaixo.\n",
        "07_PLANEJAMENTO/plano_de_estudos.md": "# Plano de estudos\n\n_Provisório. Registre origem das datas (oficial, confirmada, estimada) e a disponibilidade semanal informada pelo aluno._\n",
        "07_PLANEJAMENTO/metas_semanais.md": "# Metas semanais\n\n_Metas observáveis e verificáveis._\n",
    }
    for rel, txt in stubs.items():
        escrever_verificado(d / rel, txt)
    D = Disc(slug)
    D.renderizar()
    print(f"[verificado] disciplina '{slug}' criada em {d}")


def cmd_briefing(a, D):
    S, evs = D.estado()
    hoje = agora().date()
    print(f"RELÓGIO: {agora().isoformat()} (fonte: relógio do sistema)")
    if not evs:
        print("SEM HISTÓRICO: inicie pelo diagnóstico/ingestão; não finja continuidade.")
    if S["aberta"]:
        s = S["sessoes"][S["aberta"]]
        print(f"SESSÃO ABERTA ANTERIOR: {s['id']} desde {s['inicio']} (último registro {s['ultimo']}). "
              "`sessao iniciar` a marcará como abandonada; decida antes se quer `sessao encerrar`.")
    print()
    print(v_estado(D, S, hoje, evs[-1] if evs else {"id": "E000000", "ts": "—"}))
    rel = fontes_status(D)
    print("## Mudanças em fontes")
    print(rel or "Nenhuma (arquivos em 01_FONTES coincidem com o manifesto).")


def cmd_sessao(a, D):
    S, _ = D.estado()
    if a.acao == "iniciar":
        extra = ""
        if S["aberta"]:
            s = S["sessoes"][S["aberta"]]
            D.anexar("sessao_abandonada", sessao=s["id"], ultimo_registro=s["ultimo"])
            extra = f" · sessão anterior {s['id']} marcada como abandonada (fim = {s['ultimo']})"
        sid = f"S{len(S['ordem_sessoes']) + 1:04d}"
        ev = D.anexar("sessao_inicio", sessao=sid, objetivo=a.objetivo)
        pos_gravacao(D, ev, f" · sessão {sid}{extra}")
        return
    sid = exigir_sessao(S)
    s = S["sessoes"][sid]
    if a.acao == "pausar":
        if s["pausas"] and s["pausas"][-1][1] is None:
            raise ErroSAC("a sessão já está pausada")
        ev = D.anexar("sessao_pausa", sessao=sid, nota=a.nota)
    elif a.acao == "retomar":
        if not s["pausas"] or s["pausas"][-1][1] is not None:
            raise ErroSAC("a sessão não está pausada")
        ev = D.anexar("sessao_retomada", sessao=sid)
    elif a.acao == "checkpoint":
        ev = D.anexar("sessao_checkpoint", sessao=sid, nota=a.nota, topicos=a.topico or [])
    elif a.acao == "encerrar":
        ev = D.anexar("sessao_fim", sessao=sid, resumo=a.resumo, proximo=a.proximo, demonstrado=a.demonstrado,
                      concluida=a.concluida, topicos=a.topico or [], minutos_efetivos=a.minutos_efetivos)
    pos_gravacao(D, ev, f" · sessão {sid}")
    if a.acao == "encerrar":
        S2, _ = D.estado()
        s2 = S2["sessoes"][sid]
        print(f"Relógio: {s2['relogio_min']} min · timer ativo (relógio − pausas declaradas): {s2['ativo_min']} min · "
              f"efetivo declarado: {s2['efetivo'] if s2['efetivo'] is not None else 'não informado'}")
        print(f"Retomada: {sugerir_proxima(S2, agora().date())}")


def cmd_topico(a, D):
    S, _ = D.estado()
    if a.acao == "add":
        checar_id(a.id, "id do tópico")
        for p in a.prereq or []:
            if p not in S["topicos"] and p != a.id:
                raise ErroSAC(f"pré-requisito '{p}' não cadastrado (cadastre-o antes)")
        if a.previsto_ate:
            iso_data(a.previsto_ate, "previsto-ate")
            if not a.previsto_origem:
                raise ErroSAC("informe --previsto-origem (oficial|confirmada_estudante|estimada)")
        ev = D.anexar("topico", topico=a.id, nome=a.nome, critico=True if a.critico else None, prereqs=a.prereq,
                      fonte=a.fonte, previsto_ate=a.previsto_ate, previsto_origem=a.previsto_origem)
    else:
        if a.id not in S["topicos"]:
            raise ErroSAC(f"tópico '{a.id}' não existe")
        ev = D.anexar("marca", topico=a.id, estado=a.estado, nota=a.nota, sessao=S["aberta"])
    pos_gravacao(D, ev)


def cmd_questao(a, D):
    S, _ = D.estado()
    if a.acao == "add":
        if a.topico not in S["topicos"]:
            raise ErroSAC(f"tópico '{a.topico}' não existe")
        qid = a.id or f"Q{len(S['questoes']) + 1:04d}"
        if qid in S["questoes"]:
            raise ErroSAC(f"questão {qid} já existe (não sobrescreva; crie nova versão com outro ID)")
        ev = D.anexar("questao", questao=qid, topico=a.topico, formato=a.formato, dificuldade=a.dificuldade,
                      objetivo=a.objetivo, enunciado=a.enunciado, gabarito=a.gabarito, criterios=a.criterios,
                      raciocinio=a.raciocinio, fonte=a.fonte, erros_alvo=a.erros_alvo)
        pos_gravacao(D, ev, f" · {qid}")
        return
    q = S["questoes"].get(a.id)
    if not q:
        raise ErroSAC(f"questão '{a.id}' não existe")
    if a.acao == "ver":
        print(f"[{q['questao']}] ({q['formato']}, dificuldade {q['dificuldade']}, tópico {q['topico']})\n{q['enunciado']}")
    else:
        print(f"GABARITO de {q['questao']} — só use após o aluno tentar.\nResposta esperada: {q['gabarito']}\n"
              f"Critérios: {q['criterios']}\nRaciocínio: {q.get('raciocinio') or '—'}\nFonte: {q.get('fonte') or 'conhecimento geral'}")


def cmd_tentativa(a, D):
    S, _ = D.estado()
    if a.topico not in S["topicos"]:
        raise ErroSAC(f"tópico '{a.topico}' não existe")
    if a.questao:
        q = S["questoes"].get(a.questao)
        if not q:
            raise ErroSAC(f"questão '{a.questao}' não existe")
        if q["topico"] != a.topico:
            raise ErroSAC(f"questão {a.questao} pertence ao tópico '{q['topico']}', não '{a.topico}'")
    if not 0 <= a.pontuacao <= 1:
        raise ErroSAC("pontuação deve estar entre 0 e 1")
    if a.confianca is not None and not 1 <= a.confianca <= 5:
        raise ErroSAC("confiança deve estar entre 1 e 5")
    ev = D.anexar("tentativa", sessao=S["aberta"], topico=a.topico, questao=a.questao, tipo=a.tipo,
                  pontuacao=a.pontuacao, confianca=a.confianca, erro=a.erro, independente=False if a.com_ajuda else None,
                  resposta=a.resposta, nota=a.nota, tempo_seg=a.tempo_seg)
    pos_gravacao(D, ev)
    S2, _ = D.estado()
    t = S2["topicos"][a.topico]
    print(f"Tópico {a.topico}: estado '{ESTADOS[t['estado']]}' · próxima revisão {t['proxima']} "
          f"(passo {t['passo'] + 1}/{len(D.config()['escada_dias'])}{', limitada por prova' if t['limitada_por_prova'] else ''})")
    print("Motivos: " + "; ".join(t["motivos"]))
    if a.pontuacao < D.config()["limiar_dominio"] and not a.erro:
        print("AVISO: pontuação abaixo do limiar sem --erro; classifique o erro quando houver evidência.")
    if a.tipo == "reconhecimento":
        print("Nota: reconhecimento não conta como recuperação independente.")
    if not S["aberta"]:
        print("AVISO: não há sessão aberta; a tentativa foi gravada sem vínculo com sessão (fica fora do tempo e dos "
              "tópicos da sessão). Abra uma com `sessao iniciar --objetivo \"...\"`.")
    if not a.questao:
        print("AVISO: sem --questao: esta tentativa não conta como questão distinta para o domínio. "
              "Cadastre a questão (`questao add`) e cite o ID.")


def cmd_data(a, D):
    iso_data(a.data)
    if a.origem not in ORIGENS_DATA:
        raise ErroSAC(f"origem deve ser: {', '.join(ORIGENS_DATA)}")
    S, _ = D.estado()
    ant = S["datas"].get(a.titulo.lower())
    ev = D.anexar("data", data_id=ant["data_id"] if ant else f"D{len(S['datas']) + 1:03d}", titulo=a.titulo,
                  tipo=a.tipo, data=a.data, origem=a.origem, fonte=a.fonte, nota=a.nota)
    pos_gravacao(D, ev, " · atualização" if ant else "")


def paginas_pdf(p):
    if p.suffix.lower() != ".pdf":
        return None
    try:
        r = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, timeout=60)
        m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
        return int(m.group(1)) if m else None
    except (OSError, subprocess.SubprocessError):
        return None


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fontes_status(D):
    S, _ = D.estado()
    base = D.dir / "01_FONTES"
    reg = {f["caminho"]: f for f in S["fontes"].values()}
    vistos, out = set(), []
    for p in sorted(base.rglob("*")):
        if p.is_file() and not p.name.startswith(".") and p.name != "manifesto_de_fontes.md":
            rel = p.relative_to(D.dir).as_posix()
            vistos.add(rel)
            if rel not in reg:
                out.append(f"- NOVO (não registrado): {rel}")
            elif sha(p) != reg[rel]["sha256"]:
                out.append(f"- ALTERADO desde o registro: {rel}")
    out += [f"- AUSENTE: {r}" for r in reg if r not in vistos]
    return "\n".join(out)


def cmd_fonte(a, D):
    if a.acao == "verificar":
        print(fontes_status(D) or "Fontes coincidem com o manifesto.")
        return
    p = (D.dir / a.caminho).resolve()
    if D.dir.resolve() not in p.parents or not p.is_file():
        raise ErroSAC("caminho deve ser um arquivo dentro da pasta da disciplina")
    rel = p.relative_to(D.dir.resolve()).as_posix()
    S, _ = D.estado()
    ant = next((f for f in S["fontes"].values() if f["caminho"] == rel), None)
    fid = ant["fonte"] if ant else f"F{len(S['fontes']) + 1:03d}"
    pag = paginas_pdf(p)
    ev = D.anexar("fonte", fonte=fid, caminho=rel, sha256=sha(p), bytes=p.stat().st_size, paginas=pag,
                  tipo=a.tipo, assuntos=a.assuntos, nota=a.nota, versao=(ant["versao"] + 1) if ant else 1)
    pos_gravacao(D, ev, f" · {fid}, páginas: {pag if pag is not None else 'não verificadas'}")


def cmd_pendencia(a, D):
    S, _ = D.estado()
    if a.acao == "add":
        pid = f"P{len(S['pendencias']) + 1:03d}"
        ev = D.anexar("pendencia", pendencia=pid, categoria=a.categoria, texto=a.texto)
    else:
        if a.id not in S["pendencias"]:
            raise ErroSAC(f"pendência {a.id} não existe")
        ev = D.anexar("pendencia_resolvida", pendencia=a.id, nota=a.nota)
    pos_gravacao(D, ev)


def cmd_revisoes(a, D):
    S, _ = D.estado()
    hoje = agora().date()
    print(v_revisoes(D, S, hoje, {"id": "-", "ts": "-"}).split("\n\n", 1)[1])
    print("Sugestão:", sugerir_proxima(S, hoje))


def cmd_risco(a, D):
    S, _ = D.estado()
    cl, ev = calcular_risco(S, agora().date())
    print(f"Risco: {RISCO_ROTULO[cl]}\n" + "\n".join(f"- {e}" for e in ev))


def cmd_render(a, D):
    for r in D.renderizar():
        print("[verificado]", r)


def cmd_relatorio(a, D):
    hoje = agora().date()
    S, evs = D.estado()
    ult = evs[-1] if evs else {"id": "E000000", "ts": "—"}
    for nome, ini in (("relatorio_semanal.md", hoje - timedelta(days=7)), ("relatorio_de_desempenho.md", None)):
        tent = [x for x in S["tentativas"] if ini is None or x["_data"] >= ini]
        ind = [x for x in tent if independente(x)]
        por_tipo = {}
        for x in ind:
            por_tipo.setdefault(x["tipo"], []).append(x["pontuacao"])
        sess = [s for s in S["sessoes"].values() if ini is None or data_de(s["inicio"]) >= ini]
        cl, evd = calcular_risco(S, hoje)
        txt = (cabecalho(hoje, ult) + f"# {'Relatório semanal' if ini else 'Relatório de desempenho'} — {D.config().get('nome', D.slug)}\n\n"
               f"Período: {ini or 'início'} → {hoje}. Dados até {ult['id']}.\n\n## Sessões\n" +
               tabela(["ID", "Status", "Relógio (min)", "Ativo (min)", "Efetivo declarado (min)", "Tópicos"],
                      [[s["id"], s["status"], s["relogio_min"], s["ativo_min"] if s["ativo_min"] is not None else "desconhecido",
                        s["efetivo"] if s["efetivo"] is not None else "não declarado", ", ".join(s["topicos"]) or "—"] for s in sess]) +
               f"\n## Tentativas ({len(tent)}; independentes: {len(ind)})\n" +
               tabela(["Tipo", "N", "Média"], [[k, len(v), pct(media(v))] for k, v in sorted(por_tipo.items())]) +
               "\n## Estado dos tópicos\n" + tabela(["Tópico", "Estado", "Próxima revisão"],
                                                   [[t["id"], ESTADOS[t["estado"]], t["proxima"] or "—"] for t in S["topicos"].values()]) +
               "\n## Indicadores\n" + "\n".join(f"- {k}: {v}" for k, v in indicadores(S, hoje).items()) +
               f"\n\n## Risco: {RISCO_ROTULO[cl]}\n" + "\n".join(f"- {e}" for e in evd) +
               "\n\n## Limitações\nTendências são descritivas; este relatório não atribui melhora a nenhum método. "
               "Tempo efetivo só aparece quando o aluno o declarou.\n")
        escrever_verificado(D.dir / "08_RELATORIOS" / nome, txt)
        print("[verificado] 08_RELATORIOS/" + nome)


def cmd_validar(a, D):
    erros, avisos = [], []
    try:
        evs = D.eventos()
        cfg = D.config()
    except (ErroSAC, ErroGravacao) as e:
        erros.append(str(e))
        evs, cfg = [], None
    if cfg:
        for i, ev in enumerate(evs):
            if ev.get("id") != f"E{i + 1:06d}":
                erros.append(f"id fora de sequência na posição {i + 1}: {ev.get('id')}")
            if i and ev.get("ts", "") < evs[i - 1].get("ts", ""):
                avisos.append(f"{ev.get('id')}: timestamp anterior ao evento precedente")
        hoje = agora().date()
        S = calcular(evs, cfg, hoje)
        erros += S["problemas"]
        for q in S["questoes"].values():
            for k in ("enunciado", "gabarito", "criterios", "objetivo"):
                if not q.get(k):
                    erros.append(f"questão {q['questao']} sem '{k}'")
        for d in S["datas"].values():
            if d["origem"] not in ORIGENS_DATA:
                erros.append(f"data '{d['titulo']}' com origem inválida")
        if S["aberta"]:
            s = S["sessoes"][S["aberta"]]
            h = (agora() - datetime.fromisoformat(s["ultimo"])).total_seconds() / 3600
            if h > cfg["horas_sessao_obsoleta"]:
                avisos.append(f"sessão {s['id']} aberta, sem atividade há {h:.1f} h: encerre ou deixe ser marcada como abandonada")
        ult = evs[-1] if evs else {"id": "E000000", "ts": "—"}
        for rel in visoes(D, S, hoje, ult):
            p = D.dir / rel
            if not p.is_file():
                erros.append(f"visão ausente: {rel} (rode render)")
                continue
            m = re.search(r"sac:hoje=(\S+) ultimo_evento=(\S+)", p.read_text(encoding="utf-8")[:300])
            if not m:
                erros.append(f"visão sem cabeçalho sac: {rel}")
            elif m.group(2) != ult["id"]:
                erros.append(f"visão desatualizada: {rel} (no evento {m.group(2)}, log em {ult['id']}). Rode render")
            else:
                esperado = visoes(D, calcular(evs, cfg, date.fromisoformat(m.group(1))), date.fromisoformat(m.group(1)), ult)[rel]
                if p.read_text(encoding="utf-8") != esperado:
                    avisos.append(f"visão divergente do log (editada à mão?): {rel}")
        sem_sessao = [t["id"] for t in S["tentativas"] if not t.get("sessao")]
        if sem_sessao:
            avisos.append(f"{len(sem_sessao)} tentativa(s) sem sessão vinculada: "
                          + ", ".join(sem_sessao[:5]) + ("…" if len(sem_sessao) > 5 else ""))
        fs = fontes_status(D)
        if fs:
            avisos.append("fontes:\n" + fs)
        ab = [p["pendencia"] for p in S["pendencias"].values() if p["aberta"]]
        if ab:
            avisos.append(f"{len(ab)} pendência(s) aberta(s): {', '.join(ab)}")
    for e in erros:
        print("ERRO:", e)
    for w in avisos:
        print("AVISO:", w)
    print(f"Resultado: {len(erros)} erro(s), {len(avisos)} aviso(s).")
    if a.registrar and cfg:
        p = D.dir / "09_VALIDACAO" / "log_de_validacao.md"
        ant = p.read_text(encoding="utf-8") if p.exists() else "# Log de validação\n"
        bloco = f"\n## {agora().isoformat()}\n- Erros: {len(erros)} · Avisos: {len(avisos)}\n" + \
                "".join(f"- ERRO: {e}\n" for e in erros) + "".join(f"- AVISO: {w.splitlines()[0]}\n" for w in avisos)
        escrever_verificado(p, ant + bloco)
        print("[verificado] registrado em 09_VALIDACAO/log_de_validacao.md")
    return 1 if erros else 0


# ------------------------------------------------------------------------ CLI
# ------------------------------------------------------------------ guia (o que fazer agora)
CLI_BASE = "python3 scripts/sac.py"


def listar_disciplinas():
    return sorted(p.parent.name for p in DISC_DIR.glob("*/config.json"))


def _opc(titulo, porque, dizer, comando=None, acao=None, form=False):
    """Uma opção do guia: o que é, por quê, a frase para o agente, o comando equivalente e a ação do painel."""
    return {"titulo": titulo, "porque": porque, "dizer": dizer, "comando": comando, "acao": acao, "form": form}


def _cmd(slug, multi, resto):
    return f"{CLI_BASE}{' -d ' + slug if multi else ''} {resto}"


def _opcoes_sempre(slug, multi):
    c = lambda r: _cmd(slug, multi, r)
    return [
        _opc("Ver minha situação", "Resumo de tópicos, revisões, risco e mudanças em fontes.", "Como estou?", c("briefing"), "briefing"),
        _opc("O que revisar hoje", "Fila de revisão espaçada e a próxima ação sugerida.", "Revisão de hoje.", c("revisoes"), "revisoes"),
        _opc("Risco de atraso no cronograma", "Classificação com as evidências usadas.", "Qual meu risco de atraso?", c("risco"), "risco"),
        _opc("Gerar relatório semanal", "Cria os relatórios em 08_RELATORIOS/.", "Gere o relatório semanal.", c("relatorio"), "relatorio"),
        _opc("Conferir se está tudo íntegro", "Valida o log, as visões, as fontes e as pendências.", "Valide tudo.", c("validar"), "validar"),
        _opc("Informar data de prova ou entrega", "Sem datas o risco não pode ser calculado.",
             "A prova X é dia DD/MM/AAAA (origem: oficial, confirmada por mim ou estimada).",
             c('data --titulo "1ª VA" --data AAAA-MM-DD --origem oficial'), "data_registrar", True),
        _opc("Fazer backup", "O histórico inteiro está em disciplinas/<slug>/dados/eventos.jsonl.", "Lembre-me de fazer backup.",
             "copie a pasta disciplinas/ para outro lugar (ou use git)"),
    ]


def montar_guia(slug=None):
    """Monta o guia como dado (usado pelo texto, pelo --json e pelo painel). Só lê; nunca grava."""
    discs = listar_disciplinas()
    hoje = agora().date()
    out = {"disciplinas": discs, "disciplina": None, "hoje": hoje.isoformat(), "resumo": {},
           "topicos": [], "opcoes": [], "sempre": []}
    slug = slug or os.environ.get("SAC_DISC") or (discs[0] if len(discs) == 1 else None)
    if slug:
        checar_id(slug, "slug")
        if slug not in discs:
            raise ErroSAC(f"disciplina '{slug}' não existe. Existentes: {', '.join(discs) or 'nenhuma'}")
    nova = _opc("Criar uma disciplina", "Cada matéria é uma disciplina separada.",
                "Crie a disciplina <nome da matéria> (com um apelido curto, ex.: calc1).",
                f'{CLI_BASE} nova calc1 --nome "Cálculo I"', "nova", True)
    if not discs:
        out["opcoes"] = [dict(nova, titulo="Criar sua primeira disciplina", porque="Ainda não há nenhuma disciplina.")]
    elif not slug:
        out["opcoes"] = [_opc(f"Trabalhar na disciplina '{d}'", "Há mais de uma disciplina; escolha uma.",
                              f"Vamos trabalhar na disciplina {d}.", f"{CLI_BASE} -d {d} guia") for d in discs] + [nova]
    else:
        D, multi = Disc(slug), len(discs) > 1
        with trava_disciplina(D):
            S, evs = D.estado()
            fs = fontes_status(D)
        out["disciplina"] = slug
        c = lambda r: _cmd(slug, multi, r)
        linhas = fs.splitlines() if fs else []
        novas = [l for l in linhas if "NOVO" in l or "ALTERADO" in l]
        ausentes = [l for l in linhas if "AUSENTE" in l]
        venc = [t for t in S["topicos"].values() if t["proxima"] and t["proxima"] <= hoje]
        classe, _ = calcular_risco(S, hoje)
        pend = [q for q in S["pendencias"].values() if q["aberta"]]
        ops = []
        if not S["topicos"] and not S["fontes"] and not novas:
            ops.append(_opc("Colocar os materiais da disciplina", "Ainda não há material nem tópicos.",
                            "Coloquei os materiais em 01_FONTES: faça a ingestão.",
                            f"copie os arquivos para disciplinas/{slug}/01_FONTES/ e peça a ingestão ao agente"))
        if novas:
            ops.append(_opc(f"Processar {len(novas)} arquivo(s) novo(s) ou alterado(s)", "; ".join(l.lstrip("- ") for l in novas[:3]),
                            "Tem material novo em 01_FONTES: faça a ingestão e me diga o que mudou nos tópicos.",
                            c("fonte verificar"), "fonte_verificar"))
        if ausentes:
            ops.append(_opc(f"{len(ausentes)} arquivo(s) registrado(s) sumiram da pasta", "; ".join(l.lstrip("- ") for l in ausentes[:3]),
                            "Há fontes ausentes em 01_FONTES: investigue e registre uma pendência.", c("fonte verificar"), "fonte_verificar"))
        if S["aberta"]:
            ss = S["sessoes"][S["aberta"]]
            ops.append(_opc("Continuar a sessão em andamento", f"{ss['id']} aberta desde {ss['inicio'][:16]}: {ss.get('objetivo') or 'sem objetivo'}",
                            "Vamos continuar a sessão."))
            ops.append(_opc("Encerrar a sessão", "Registra o que foi demonstrado e o ponto de retomada.", "Encerrar sessão.",
                            c('sessao encerrar --resumo "..." --proximo "..." --concluida parcial'), "sessao_encerrar", True))
        if venc:
            ops.append(_opc(f"Fazer as {len(venc)} revisão(ões) vencida(s)", "Recuperar sem consultar vale mais que reler.",
                            "Revisão de hoje.", c("revisoes"), "revisoes"))
        if not S["aberta"] and S["topicos"]:
            ops.append(_opc("Começar uma sessão de estudo", sugerir_proxima(S, hoje),
                            "Vamos retomar." if evs else "Vamos estudar.", c('sessao iniciar --objetivo "..."'), "sessao_iniciar", True))
        if classe in ("atraso_confirmado", "atraso_provavel", "atencao_necessaria"):
            ops.append(_opc(f"Risco de cronograma: {RISCO_ROTULO[classe]}", "Veja as evidências e ajuste o plano.",
                            "Qual meu risco de atraso?", c("risco"), "risco"))
        if pend:
            ops.append(_opc(f"{len(pend)} pendência(s) aberta(s)", "; ".join(q["texto"][:60] + ("…" if len(q["texto"]) > 60 else "") for q in pend[:2]),
                            "Mostre as pendências abertas e me ajude a resolvê-las.", c("validar"), "validar"))
        if S["topicos"] and not S["datas"]:
            ops.append(_opc("Informar datas de provas e entregas", "Sem datas, o risco de cronograma não é calculado.",
                            "A prova X é dia DD/MM/AAAA (origem: oficial, confirmada por mim ou estimada).",
                            c('data --titulo "1ª VA" --data AAAA-MM-DD --origem oficial'), "data_registrar", True))
        out["opcoes"] = ops[:5]
        out["sempre"] = _opcoes_sempre(slug, multi)
        out["topicos"] = [{"id": t["id"], "nome": t["nome"], "estado": ESTADOS[t["estado"]]}
                          for t in sorted(S["topicos"].values(), key=lambda t: t["ordem"])]
        out["resumo"] = {"topicos": len(S["topicos"]), "revisoes_vencidas": len(venc), "risco": RISCO_ROTULO[classe],
                         "sessao_aberta": S["aberta"], "pendencias": len(pend), "fontes_pendentes": len(novas) + len(ausentes)}
    for n, o in enumerate(out["opcoes"] + out["sempre"], 1):
        o["n"] = n
    return out


def imprimir_guia(g):
    if g["disciplina"]:
        r = g["resumo"]
        print(f"GUIA — disciplina '{g['disciplina']}' · {g['hoje']}")
        print(f"Situação: {r['topicos']} tópico(s) · {r['revisoes_vencidas']} revisão(ões) vencida(s) · risco: {r['risco']} · "
              f"sessão: {r['sessao_aberta'] or 'nenhuma aberta'} · {r['pendencias']} pendência(s) · {r['fontes_pendentes']} fonte(s) a processar")
    else:
        print(f"GUIA · {g['hoje']}")

    def bloco(titulo, ops):
        if not ops:
            return
        print(f"\n{titulo}")
        for o in ops:
            print(f"\n {o['n']}. {o['titulo']}\n    Por quê: {o['porque']}\n    Diga ao agente: “{o['dizer']}”")
            if o["comando"]:
                print(f"    Comando equivalente: {o['comando']}")
    bloco("O QUE FAZER AGORA (escolha pelo número):", g["opcoes"])
    bloco("SEMPRE DISPONÍVEL:", g["sempre"])
    print("\nPainel com botões (sem digitar comandos): " + f"{CLI_BASE} painel" + " — ou dê duplo clique em Abrir-Painel.")
    print("No Windows, troque python3 por python (ou py).")


def cmd_guia(a):
    g = montar_guia(a.disc)
    if a.json:
        print(json.dumps(g, ensure_ascii=False, indent=2))
    else:
        imprimir_guia(g)
    return 0


def cmd_painel(a):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sac_painel
    return sac_painel.servir(a.porta, not a.sem_navegador)


class Parser(argparse.ArgumentParser):
    """Erro de uso sai com 1 (como ErroSAC). O código 2 fica reservado a FALHA DE GRAVAÇÃO."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"ERRO: {message}", file=sys.stderr)
        sys.exit(1)


def construir():
    p = Parser(prog="sac.py", description="CLI do Sistema de Aprendizagem Contínua")
    p.add_argument("-d", "--disc", help="slug da disciplina (omita se houver só uma)")
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("nova", help="cria uma disciplina")
    n.add_argument("slug"); n.add_argument("--nome", required=True); n.add_argument("--objetivo")
    sub.add_parser("briefing", help="abertura de sessão: estado, revisões, risco, mudanças em fontes")
    s = sub.add_parser("sessao"); ss = s.add_subparsers(dest="acao", required=True)
    i = ss.add_parser("iniciar"); i.add_argument("--objetivo", required=True)
    pa = ss.add_parser("pausar"); pa.add_argument("--nota")
    ss.add_parser("retomar")
    c = ss.add_parser("checkpoint"); c.add_argument("--nota", required=True); c.add_argument("--topico", action="append")
    e = ss.add_parser("encerrar")
    e.add_argument("--resumo", required=True); e.add_argument("--proximo", required=True)
    e.add_argument("--concluida", required=True, choices=["sim", "parcial", "nao"])
    e.add_argument("--demonstrado"); e.add_argument("--topico", action="append")
    e.add_argument("--minutos-efetivos", type=float, help="tempo de estudo efetivo informado pelo aluno")
    t = sub.add_parser("topico"); ts = t.add_subparsers(dest="acao", required=True)
    ta = ts.add_parser("add"); ta.add_argument("id"); ta.add_argument("--nome"); ta.add_argument("--critico", action="store_true")
    ta.add_argument("--prereq", action="append"); ta.add_argument("--fonte"); ta.add_argument("--previsto-ate"); ta.add_argument("--previsto-origem", choices=ORIGENS_DATA)
    tm = ts.add_parser("marcar"); tm.add_argument("id"); tm.add_argument("--estado", required=True, choices=["nao_iniciado", "em_estudo"]); tm.add_argument("--nota")
    q = sub.add_parser("questao"); qs = q.add_subparsers(dest="acao", required=True)
    qa = qs.add_parser("add"); qa.add_argument("--id"); qa.add_argument("--topico", required=True)
    qa.add_argument("--formato", required=True, choices=FORMATOS); qa.add_argument("--dificuldade", required=True, type=int, choices=range(1, 6))
    qa.add_argument("--objetivo", required=True); qa.add_argument("--enunciado", required=True); qa.add_argument("--gabarito", required=True)
    qa.add_argument("--criterios", required=True); qa.add_argument("--raciocinio"); qa.add_argument("--fonte"); qa.add_argument("--erros-alvo")
    for nm in ("ver", "gabarito"):
        qs.add_parser(nm).add_argument("id")
    r = sub.add_parser("tentativa", help="registra evidência; o código recalcula estado e revisão")
    r.add_argument("--topico", required=True); r.add_argument("--questao"); r.add_argument("--tipo", required=True, choices=TIPOS_TENTATIVA)
    r.add_argument("--pontuacao", required=True, type=float); r.add_argument("--confianca", type=int)
    r.add_argument("--erro", choices=TIPOS_ERRO); r.add_argument("--com-ajuda", action="store_true")
    r.add_argument("--resposta"); r.add_argument("--nota"); r.add_argument("--tempo-seg", type=int)
    d = sub.add_parser("data"); d.add_argument("--titulo", required=True); d.add_argument("--data", required=True)
    d.add_argument("--origem", required=True, choices=ORIGENS_DATA); d.add_argument("--tipo", default="prova", choices=TIPOS_DATA)
    d.add_argument("--fonte"); d.add_argument("--nota")
    f = sub.add_parser("fonte"); fs = f.add_subparsers(dest="acao", required=True)
    fr = fs.add_parser("registrar"); fr.add_argument("caminho"); fr.add_argument("--tipo"); fr.add_argument("--assuntos"); fr.add_argument("--nota")
    fs.add_parser("verificar")
    pe = sub.add_parser("pendencia"); ps = pe.add_subparsers(dest="acao", required=True)
    pad = ps.add_parser("add"); pad.add_argument("--categoria", required=True, choices=TIPOS_PENDENCIA); pad.add_argument("--texto", required=True)
    pr = ps.add_parser("resolver"); pr.add_argument("id"); pr.add_argument("--nota")
    sub.add_parser("revisoes"); sub.add_parser("risco"); sub.add_parser("render"); sub.add_parser("relatorio")
    v = sub.add_parser("validar"); v.add_argument("--registrar", action="store_true")
    g = sub.add_parser("guia", help="o que fazer agora: opções numeradas, frase para o agente e comando equivalente")
    g.add_argument("--json", action="store_true", help="saída em JSON (para agentes e para o painel)")
    pn = sub.add_parser("painel", help="abre um painel local com botões (127.0.0.1), sem digitar comandos")
    pn.add_argument("--porta", type=int, default=0, help="porta local (0 = automática)")
    pn.add_argument("--sem-navegador", action="store_true", help="só imprime o endereço")
    return p


def main(argv=None):
    for fluxo in (sys.stdout, sys.stderr):  # consoles Windows usam cp1252 e quebram com → ≥ −
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = construir().parse_args(argv)
    try:
        if args.cmd == "nova":
            cmd_nova(args)
            return 0
        if args.cmd == "guia":
            return cmd_guia(args)
        if args.cmd == "painel":
            return cmd_painel(args)
        D = resolver_disc(args.disc)
        fn = {"briefing": cmd_briefing, "sessao": cmd_sessao, "topico": cmd_topico, "questao": cmd_questao,
              "tentativa": cmd_tentativa, "data": cmd_data, "fonte": cmd_fonte, "pendencia": cmd_pendencia,
              "revisoes": cmd_revisoes, "risco": cmd_risco, "render": cmd_render, "relatorio": cmd_relatorio,
              "validar": cmd_validar}[args.cmd]
        with trava_disciplina(D):
            return fn(args, D) or 0
    except ErroSAC as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    except ErroGravacao as e:
        print(f"FALHA DE GRAVAÇÃO: {e}\nNÃO declare que foi salvo. Informe o aluno e forneça o conteúdo para salvar manualmente.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
