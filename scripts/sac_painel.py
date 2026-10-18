#!/usr/bin/env python3
"""Painel local do SAC: botões e formulários sobre o CLI, para quem não quer decorar comandos.

Princípios de segurança (o painel roda comandos no seu computador):
- escuta só em 127.0.0.1 (nunca na rede);
- exige um token aleatório, gerado a cada execução, em toda chamada;
- confere o cabeçalho Host (contra DNS rebinding) e o Origin (contra páginas de outros sites);
- só executa uma lista fixa de ações; os valores vão ao CLI como argumentos (sem shell) no formato
  --opcao=valor, então um texto começando com "--" nunca vira opção.
Toda regra, validação, trava de escrita e gravação verificada continuam sendo as do sac.py.
Só biblioteca padrão.
"""
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CLI = Path(__file__).resolve().with_name("sac.py")
TIMEOUT = 90
LIMITE_CORPO = 64 * 1024
RE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


# ------------------------------------------------------------------ ações permitidas
class Invalido(Exception):
    pass


def _txt(p, chave, obrigatorio=False):
    v = str(p.get(chave) or "").strip()
    if obrigatorio and not v:
        raise Invalido(f"campo obrigatório: {chave}")
    if len(v) > 4000:
        raise Invalido(f"campo muito longo: {chave}")
    return v


def _id(p, chave, obrigatorio=True):
    v = _txt(p, chave, obrigatorio)
    if v and not RE_ID.match(v):
        raise Invalido(f"valor inválido em {chave}")
    return v


def _flags(p, *pares):
    """pares: (chave, flag, obrigatorio). Gera --flag=valor (nunca separa o valor do flag)."""
    out = []
    for chave, flag, obrig in pares:
        v = _txt(p, chave, obrig)
        if v:
            out.append(f"--{flag}={v}")
    return out


ACOES = {
    "briefing": lambda p: ["briefing"],
    "revisoes": lambda p: ["revisoes"],
    "risco": lambda p: ["risco"],
    "relatorio": lambda p: ["relatorio"],
    "render": lambda p: ["render"],
    "validar": lambda p: ["validar"],
    "validar_registrar": lambda p: ["validar", "--registrar"],
    "fonte_verificar": lambda p: ["fonte", "verificar"],
    "sessao_iniciar": lambda p: ["sessao", "iniciar"] + _flags(p, ("objetivo", "objetivo", True)),
    "sessao_pausar": lambda p: ["sessao", "pausar"] + _flags(p, ("nota", "nota", False)),
    "sessao_retomar": lambda p: ["sessao", "retomar"],
    "sessao_encerrar": lambda p: ["sessao", "encerrar"] + _flags(
        p, ("resumo", "resumo", True), ("proximo", "proximo", True), ("concluida", "concluida", True),
        ("demonstrado", "demonstrado", False), ("minutos_efetivos", "minutos-efetivos", False))
        + ([f"--topico={_id(p, 'topico', False)}"] if _id(p, "topico", False) else []),
    "topico_marcar": lambda p: ["topico", "marcar", _id(p, "topico")] + _flags(p, ("estado", "estado", True), ("nota", "nota", False)),
    "data_registrar": lambda p: ["data"] + _flags(p, ("titulo", "titulo", True), ("data", "data", True),
                                                   ("origem", "origem", True), ("tipo", "tipo", False)),
    "pendencia_add": lambda p: ["pendencia", "add"] + _flags(p, ("categoria", "categoria", True), ("texto", "texto", True)),
    "pendencia_resolver": lambda p: ["pendencia", "resolver", _id(p, "id")] + _flags(p, ("nota", "nota", False)),
    "nova": lambda p: ["nova", _id(p, "slug")] + _flags(p, ("nome", "nome", True), ("objetivo", "objetivo", False)),
}
SEM_DISCIPLINA = {"nova"}


def _mostrar(argv):
    return " ".join(f'"{a}"' if re.search(r"\s", a) else a for a in argv)


def _rodar(argv, disciplina=None):
    cmd = [sys.executable, str(CLI)] + (["-d", disciplina] if disciplina else []) + argv
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return {"codigo": 2, "saida": "", "erro": f"tempo esgotado ({TIMEOUT} s). Nada garante que foi salvo.", "comando": ""}
    return {"codigo": r.returncode, "saida": r.stdout, "erro": r.stderr,
            "comando": "python3 scripts/sac.py " + (f"-d {disciplina} " if disciplina else "") + _mostrar(argv)}


def executar(acao, params, disciplina=None):
    if acao not in ACOES:
        raise Invalido(f"ação desconhecida: {acao}")
    if disciplina and not RE_ID.match(disciplina):
        raise Invalido("disciplina inválida")
    argv = ACOES[acao](params or {})
    return _rodar(argv, None if acao in SEM_DISCIPLINA else disciplina)


def guia(disciplina=None):
    if disciplina and not RE_ID.match(disciplina):
        raise Invalido("disciplina inválida")
    r = _rodar(["guia", "--json"], disciplina)
    if r["codigo"] != 0:
        return {"erro": (r["erro"] or r["saida"]).strip()}
    return json.loads(r["saida"])


# ------------------------------------------------------------------ servidor
class Handler(BaseHTTPRequestHandler):
    server_version = "SACPainel"

    def log_message(self, *a):  # silencioso: o terminal fica limpo
        pass

    def _enviar(self, codigo, corpo, tipo="application/json; charset=utf-8"):
        b = corpo if isinstance(corpo, bytes) else corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                         "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(b)

    def _erro(self, codigo, msg):
        self._enviar(codigo, json.dumps({"erro": msg}, ensure_ascii=False))

    def _origem_ok(self):
        porta = self.server.server_port
        if self.headers.get("Host", "") not in (f"127.0.0.1:{porta}", f"localhost:{porta}"):
            return False
        org = self.headers.get("Origin")
        return org is None or org in (f"http://127.0.0.1:{porta}", f"http://localhost:{porta}")

    def _token_ok(self, t):
        return bool(t) and secrets.compare_digest(t, self.server.token)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if not self._origem_ok():
            return self._erro(403, "origem não permitida")
        if u.path == "/":
            if not self._token_ok((q.get("t") or [""])[0]):
                return self._erro(403, "abra o endereço completo impresso no terminal (com ?t=...)")
            return self._enviar(200, PAGINA.replace("__TOKEN__", self.server.token), "text/html; charset=utf-8")
        if u.path == "/api/guia":
            if not self._token_ok(self.headers.get("X-SAC-Token", "")):
                return self._erro(403, "token inválido")
            try:
                return self._enviar(200, json.dumps(guia((q.get("d") or [None])[0]), ensure_ascii=False))
            except Invalido as e:
                return self._erro(400, str(e))
        return self._erro(404, "não encontrado")

    def do_POST(self):
        if not self._origem_ok():
            return self._erro(403, "origem não permitida")
        if self.path != "/api/run":
            return self._erro(404, "não encontrado")
        if not self._token_ok(self.headers.get("X-SAC-Token", "")):
            return self._erro(403, "token inválido")
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > LIMITE_CORPO:
                return self._erro(400, "corpo inválido")
            d = json.loads(self.rfile.read(n).decode("utf-8"))
            r = executar(d.get("acao"), d.get("params"), d.get("disciplina") or None)
        except (Invalido, ValueError, AttributeError, TypeError) as e:
            return self._erro(400, str(e) or "requisição inválida")
        self._enviar(200, json.dumps(r, ensure_ascii=False))


def criar_servidor(porta=0):
    srv = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
    srv.token = secrets.token_urlsafe(24)
    return srv


def servir(porta=0, abrir=True):
    srv = criar_servidor(porta)
    url = f"http://127.0.0.1:{srv.server_port}/?t={srv.token}"
    print("Painel do SAC rodando só neste computador.")
    print(f"Endereço: {url}")
    print("Para encerrar, feche esta janela ou aperte Ctrl+C.")
    if abrir:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nPainel encerrado.")
    finally:
        srv.server_close()
    return 0


# ------------------------------------------------------------------ página
PAGINA = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAC — Painel</title>
<style>
:root{--bg:#f6f6f3;--card:#fff;--tx:#1c1c1a;--mut:#6a6a64;--bd:#deded8;--ac:#2f5fd0;--act:#fff;--ok:#1d7a3c;--er:#b3261e;--code:#eeeee9}
@media (prefers-color-scheme:dark){:root{--bg:#151515;--card:#1f1f1e;--tx:#ecece8;--mut:#a3a39c;--bd:#343430;--ac:#7aa2ff;--act:#101010;--ok:#6fd08c;--er:#ff8a80;--code:#2a2a27}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:920px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:1.4rem;margin:0 0 4px} h2{font-size:1.05rem;margin:28px 0 10px}
.mut{color:var(--mut);font-size:.92rem}
.card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;margin:10px 0}
.card h3{margin:0 0 2px;font-size:1rem}
.row{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;align-items:center}
button,select,input{font:inherit;border-radius:8px;border:1px solid var(--bd);padding:8px 12px;background:var(--card);color:var(--tx)}
button{cursor:pointer} button:hover{border-color:var(--ac)}
button.p{background:var(--ac);color:var(--act);border-color:var(--ac);font-weight:600}
code,pre{background:var(--code);border-radius:6px;font:.85rem ui-monospace,Menlo,Consolas,monospace}
code{padding:2px 6px;word-break:break-all} pre{padding:12px;overflow:auto;white-space:pre-wrap;margin:8px 0 0}
details{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 16px;margin:8px 0}
summary{cursor:pointer;font-weight:600}
label{display:block;margin:10px 0 2px;font-size:.9rem}
input,select{width:100%} .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px}
.ok{color:var(--ok)} .er{color:var(--er)} .tag{display:inline-block;border:1px solid var(--bd);border-radius:999px;padding:1px 10px;font-size:.85rem;margin:2px 6px 2px 0}
</style></head><body><main>
<h1>SAC — Painel</h1>
<p class="mut">Botões para organizar o estudo sem digitar comandos. O estudo em si (perguntas, explicações, correção) acontece no seu agente: use “Copiar frase” e cole lá.</p>
<div id="topo" class="row"></div>
<div id="resumo" class="mut"></div>
<h2>O que fazer agora</h2><div id="opcoes"></div>
<h2>Sempre disponível</h2><div id="sempre"></div>
<h2>Registrar e organizar</h2><div id="forms"></div>
<h2>Resultado</h2>
<div class="card"><div id="cmd" class="mut">Nada executado ainda.</div><pre id="saida" hidden></pre></div>
</main>
<script>
const TOKEN="__TOKEN__";
let G=null, DISC="";
const $=id=>document.getElementById(id);
const FORMS={
 sessao_iniciar:{t:"Iniciar sessão de estudo",c:[{n:"objetivo",l:"Objetivo desta sessão",req:1}]},
 sessao_encerrar:{t:"Encerrar sessão",c:[{n:"resumo",l:"O que foi feito",req:1},{n:"proximo",l:"Próximo passo",req:1},
   {n:"concluida",l:"Objetivo concluído?",sel:[["parcial","Parcialmente"],["sim","Sim, demonstrado"],["nao","Não"]]},
   {n:"demonstrado",l:"O que eu demonstrei saber (opcional)"},{n:"minutos_efetivos",l:"Minutos de estudo efetivo (opcional)",tipo:"number"}]},
 sessao_pausar:{t:"Pausar sessão",c:[{n:"nota",l:"Motivo (opcional)"}]},
 topico_marcar:{t:"Declarar situação de um tópico",c:[{n:"topico",l:"Tópico",topicos:1,req:1},
   {n:"estado",l:"Situação",sel:[["nao_iniciado","Ainda não comecei"],["em_estudo","Estou estudando"]]}]},
 data_registrar:{t:"Registrar data de prova ou entrega",c:[{n:"titulo",l:"Título (ex.: 1ª VA)",req:1},{n:"data",l:"Data",tipo:"date",req:1},
   {n:"origem",l:"De onde vem a data?",sel:[["oficial","Oficial"],["confirmada_estudante","Confirmei eu mesmo"],["estimada","Estimada"],["desconhecida","Desconhecida"]]},
   {n:"tipo",l:"Tipo",sel:[["prova","Prova"],["entrega","Entrega"],["outro","Outro"]]}]},
 pendencia_add:{t:"Anotar dúvida ou pendência",c:[{n:"categoria",l:"Tipo",sel:[["duvida","Dúvida"],["conflito","Conflito entre fontes"],["fonte","Problema de fonte"],["operacional","Operacional"]]},{n:"texto",l:"O que anotar",req:1}]},
 nova:{t:"Criar disciplina",c:[{n:"slug",l:"Apelido curto, sem espaços (ex.: calc1)",req:1},{n:"nome",l:"Nome da disciplina",req:1},{n:"objetivo",l:"Objetivo (opcional)"}]}
};
const DIRETOS=[["briefing","Situação"],["revisoes","Revisões"],["risco","Risco"],["relatorio","Relatório semanal"],["validar","Validar tudo"],
 ["validar_registrar","Validar e registrar"],["fonte_verificar","Verificar fontes"],["render","Atualizar visões"],["sessao_retomar","Retomar sessão"]];

async function api(path,opts={}){
  const r=await fetch(path,{...opts,headers:{"X-SAC-Token":TOKEN,"Content-Type":"application/json"}});
  return r.json();
}
function el(tag,attrs={},...kids){
  const e=document.createElement(tag);
  for(const[k,v]of Object.entries(attrs)){ if(k==="class")e.className=v; else if(k.startsWith("on"))e[k]=v; else e.setAttribute(k,v); }
  for(const c of kids)e.append(c.nodeType?c:document.createTextNode(c));
  return e;
}
async function copiar(txt,btn){
  try{await navigator.clipboard.writeText(txt);}catch(e){const t=el("textarea");t.value=txt;document.body.append(t);t.select();document.execCommand("copy");t.remove();}
  const o=btn.textContent;btn.textContent="Copiado!";setTimeout(()=>btn.textContent=o,1200);
}
async function executar(acao,params={}){
  $("cmd").textContent="Executando…";$("saida").hidden=true;
  const r=await api("/api/run",{method:"POST",body:JSON.stringify({acao,params,disciplina:DISC})});
  if(r.erro&&r.codigo===undefined){$("cmd").replaceChildren(el("span",{class:"er"},"Não executado: "+r.erro));return;}
  const bom=r.codigo===0;
  $("cmd").replaceChildren(el("span",{class:bom?"ok":"er"},bom?"Concluído. ":(r.codigo===2?"FALHA DE GRAVAÇÃO: nada foi salvo. ":"Erro: nada foi gravado. ")),
    "Comando equivalente: ",el("code",{},r.comando||"—"));
  const t=((r.saida||"")+(r.erro?"\n"+r.erro:"")).trim()||"(sem saída)";
  $("saida").textContent=t;$("saida").hidden=false;
  $("saida").scrollIntoView({behavior:"smooth",block:"nearest"});
  carregar();
}
function abrirForm(nome){const d=$("f-"+nome);if(d){d.open=true;d.scrollIntoView({behavior:"smooth",block:"center"});const i=d.querySelector("input,select");if(i)i.focus();}}
function cartao(o){
  const c=el("div",{class:"card"},el("h3",{},o.n+". "+o.titulo),el("div",{class:"mut"},o.porque||""));
  const row=el("div",{class:"row"});
  if(o.acao){row.append(el("button",{class:"p",onclick:()=>o.form?abrirForm(o.acao):executar(o.acao)},o.form?"Preencher":"Executar"));}
  const b=el("button",{},"Copiar frase para o agente");b.onclick=()=>copiar(o.dizer,b);row.append(b);
  c.append(row,el("div",{class:"mut",style:"margin-top:8px"},"Frase: “"+o.dizer+"”"));
  if(o.comando)c.append(el("div",{class:"mut"},"Comando equivalente: ",el("code",{},o.comando)));
  return c;
}
function montarForms(){
  const box=$("forms");box.replaceChildren();
  const linha=el("div",{class:"row"});
  for(const[a,t]of DIRETOS)linha.append(el("button",{onclick:()=>executar(a)},t));
  box.append(linha);
  for(const[nome,f]of Object.entries(FORMS)){
    if(nome==="topico_marcar"&&!(G&&G.topicos.length))continue;
    const d=el("details",{id:"f-"+nome},el("summary",{},f.t));
    const g=el("div",{class:"grid"});
    for(const c of f.c){
      let inp;
      if(c.sel){inp=el("select",{name:c.n});for(const[v,l]of c.sel)inp.append(el("option",{value:v},l));}
      else if(c.topicos){inp=el("select",{name:c.n});for(const t of(G?G.topicos:[]))inp.append(el("option",{value:t.id},t.id+" — "+t.estado));}
      else inp=el("input",{name:c.n,type:c.tipo||"text"});
      g.append(el("div",{},el("label",{},c.l+(c.req?" *":"")),inp));
    }
    const b=el("button",{class:"p",style:"margin-top:12px"},"Confirmar");
    b.onclick=()=>{const p={};d.querySelectorAll("[name]").forEach(i=>p[i.name]=i.value);executar(nome,p);};
    d.append(g,b);box.append(d);
  }
}
async function carregar(){
  const g=await api("/api/guia?d="+encodeURIComponent(DISC));
  if(g.erro){$("resumo").textContent=g.erro;return;}
  G=g;
  const topo=$("topo");topo.replaceChildren();
  if(g.disciplinas.length>1){
    const s=el("select",{style:"max-width:260px"},el("option",{value:""},"Escolha a disciplina…"));
    for(const d of g.disciplinas){const o=el("option",{value:d},d);if(d===g.disciplina)o.selected=true;s.append(o);}
    s.onchange=()=>{DISC=s.value;carregar();};topo.append(s);
  }else if(g.disciplina)DISC=g.disciplina;
  if(g.disciplina&&!DISC)DISC=g.disciplina;
  const r=g.resumo||{};
  $("resumo").replaceChildren(...(g.disciplina?[
    el("span",{class:"tag"},r.topicos+" tópico(s)"),el("span",{class:"tag"},r.revisoes_vencidas+" revisão(ões) vencida(s)"),
    el("span",{class:"tag"},"risco: "+r.risco),el("span",{class:"tag"},r.sessao_aberta?"sessão aberta: "+r.sessao_aberta:"sem sessão aberta"),
    el("span",{class:"tag"},r.pendencias+" pendência(s)"),el("span",{class:"tag"},r.fontes_pendentes+" fonte(s) a processar")]:[document.createTextNode("Hoje: "+g.hoje)]));
  $("opcoes").replaceChildren(...g.opcoes.map(cartao));
  $("sempre").replaceChildren(...g.sempre.map(cartao));
  montarForms();
}
carregar();
</script></body></html>
"""

if __name__ == "__main__":
    sys.exit(servir())
