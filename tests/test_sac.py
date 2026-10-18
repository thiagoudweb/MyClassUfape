"""Testes de aceitação do harness (Fase 5 da especificação).

Rodar:  python3 -m unittest discover -s tests -v
Usa SAC_ROOT temporário e SAC_NOW para simular o relógio. Nada toca em disciplinas reais.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "scripts" / "sac.py"


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.d = self.root / "disciplinas" / "calc1"
        self.run_ok("nova", "calc1", "--nome", "Cálculo I", "--objetivo", "Aprovar")

    def run_cli(self, *args, now=None):
        env = {**os.environ, "SAC_ROOT": str(self.root)}
        env.pop("SAC_NOW", None)
        if now:
            env["SAC_NOW"] = now + ":00-03:00" if now.count(":") == 1 else now
        r = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, env=env)
        return r.returncode, r.stdout, r.stderr

    def run_ok(self, *args, now=None):
        c, o, e = self.run_cli(*args, now=now)
        self.assertEqual(c, 0, f"{args}\nSTDOUT:{o}\nSTDERR:{e}")
        return o

    def eventos(self):
        if not (self.d / "dados" / "eventos.jsonl").exists():
            return []
        return [json.loads(l) for l in (self.d / "dados" / "eventos.jsonl").read_text(encoding="utf-8").splitlines() if l]

    def topico(self, tid, *extra):
        self.run_ok("topico", "add", tid, "--nome", tid, *extra)

    def questao(self, qid, topico="t1"):
        self.run_ok("questao", "add", "--id", qid, "--topico", topico, "--formato", "resposta_curta", "--dificuldade", "2",
                    "--objetivo", "obj", "--enunciado", f"Enunciado {qid}", "--gabarito", f"GABARITO-SECRETO-{qid}",
                    "--criterios", "crit")

    def tent(self, dia, score, tipo="recuperacao", q=None, topico="t1", extra=()):
        args = ["tentativa", "--topico", topico, "--tipo", tipo, "--pontuacao", str(score), *extra]
        if q:
            args += ["--questao", q]
        return self.run_ok(*args, now=f"2026-10-{dia:02d}T10:00")

    def estado_view(self, nome="dominio_por_topico.md"):
        return (self.d / "04_MEMORIA_DO_ALUNO" / nome).read_text(encoding="utf-8")


class TestInicioESessao(Base):
    def test_sem_historico_nao_finge_continuidade(self):
        out = self.run_ok("briefing", now="2026-10-17T09:00")
        self.assertIn("SEM HISTÓRICO", out)
        self.assertIn("Nenhuma sessão encerrada", out)

    def test_duracoes_distintas_e_pausas(self):
        self.run_ok("sessao", "iniciar", "--objetivo", "x", now="2026-10-17T10:00")
        self.run_ok("sessao", "pausar", now="2026-10-17T10:10")
        self.run_ok("sessao", "retomar", now="2026-10-17T10:20")
        out = self.run_ok("sessao", "encerrar", "--resumo", "r", "--proximo", "p", "--concluida", "parcial", now="2026-10-17T10:40")
        self.assertIn("Relógio: 40.0", out)
        self.assertIn("timer ativo (relógio − pausas declaradas): 30.0", out)
        self.assertIn("efetivo declarado: não informado", out)  # nunca estimado sozinho

    def test_efetivo_so_quando_declarado(self):
        self.run_ok("sessao", "iniciar", "--objetivo", "x", now="2026-10-17T10:00")
        self.run_ok("sessao", "encerrar", "--resumo", "r", "--proximo", "p", "--concluida", "sim",
                    "--minutos-efetivos", "25", now="2026-10-17T11:00")
        self.assertIn("estudo efetivo declarado pelo aluno (min): 25.0", self.estado_view("estado_atual.md"))

    def test_sessao_abandonada_preserva_ultimo_registro(self):
        self.topico("t1")
        self.run_ok("sessao", "iniciar", "--objetivo", "a", now="2026-10-17T10:00")
        self.run_ok("sessao", "checkpoint", "--nota", "visto limites", "--topico", "t1", now="2026-10-17T10:25")
        self.run_ok("sessao", "iniciar", "--objetivo", "b", now="2026-10-18T09:00")
        idx = (self.d / "05_SESSOES" / "indice_de_sessoes.md").read_text(encoding="utf-8")
        self.assertIn("abandonada", idx)
        from datetime import datetime
        esperado = datetime.fromisoformat("2026-10-17T10:25:00-03:00").astimezone().isoformat()  # fuso do sistema
        self.assertIn(esperado, idx)  # fim = último registro confiável
        self.assertIn("desconhecido", idx)  # tempo ativo não inventado
        self.assertIn("(mínimo)", idx)

    def test_encerrar_sem_sessao_falha(self):
        c, _, e = self.run_cli("sessao", "encerrar", "--resumo", "r", "--proximo", "p", "--concluida", "sim")
        self.assertEqual(c, 1)
        self.assertIn("não há sessão aberta", e)

    def test_retomada_apos_encerrar(self):
        self.topico("t1")
        self.run_ok("sessao", "iniciar", "--objetivo", "a", now="2026-10-17T10:00")
        self.tent(17, 0.9)
        self.run_ok("sessao", "encerrar", "--resumo", "limites ok", "--proximo", "aplicar limites", "--concluida", "parcial",
                    now="2026-10-17T10:30")
        out = self.run_ok("briefing", now="2026-10-18T08:00")
        self.assertIn("Resumo: limites ok", out)
        self.assertIn("aplicar limites", out)


class TestRevisaoEspacada(Base):
    def setUp(self):
        super().setUp()
        self.topico("t1")
        for q in ("Q1", "Q2", "Q3"):
            self.questao(q)

    def proxima(self):
        linha = [l for l in self.estado_view().splitlines() if l.startswith("| t1 ")][0]
        return linha.split("|")[7].strip().split(" ")[0]

    def test_escada_avanca_so_quando_devida(self):
        self.tent(1, 0.9, q="Q1")
        self.assertEqual(self.proxima(), "2026-10-02")  # +1
        self.tent(2, 0.9, q="Q2")
        self.assertEqual(self.proxima(), "2026-10-05")  # +3 (revisão na data devida)
        self.tent(3, 0.9, q="Q3")  # antecipada: não avança o passo
        self.assertEqual(self.proxima(), "2026-10-06")  # mesmo passo (+3) a partir de 03
        self.tent(6, 0.9, q="Q1")  # devida: avança para +7
        self.assertEqual(self.proxima(), "2026-10-13")

    def test_erro_volta_ao_inicio_da_escada(self):
        self.tent(1, 0.9, q="Q1")
        self.tent(2, 0.9, q="Q2")
        self.tent(5, 0.2, q="Q3", extra=["--erro", "esquecimento"])
        self.assertEqual(self.proxima(), "2026-10-06")  # +1 após esquecer

    def test_reconhecimento_nao_avanca_nem_conta_como_independente(self):
        self.tent(1, 0.9, "reconhecimento", q="Q1")
        v = self.estado_view()
        self.assertIn("Em estudo", v)
        self.assertNotIn("Provisoriamente", v)
        self.tent(2, 0.9, "recuperacao", q="Q2", topico="t1", extra=["--com-ajuda"])
        self.assertIn("Em estudo", self.estado_view())  # com ajuda também não conta

    def test_revisao_vencida_vira_revisao_necessaria(self):
        self.tent(1, 0.9, q="Q1")
        self.tent(2, 0.9, "explicacao", q="Q2")
        self.tent(5, 0.9, "aplicacao", q="Q3")
        self.assertIn("Provisoriamente dominado", self.estado_view())
        out = self.run_ok("revisoes", now="2026-10-20T10:00")  # devida desde 12
        self.assertIn("VENCIDA", out)
        self.run_ok("render", now="2026-10-30T10:00")
        self.assertIn("Revisão necessária", self.estado_view())

    def test_teto_antes_da_prova(self):
        self.run_ok("data", "--titulo", "AB1", "--data", "2026-10-06", "--origem", "oficial")
        self.tent(1, 0.9, q="Q1")
        self.tent(2, 0.9, q="Q2")  # escada pediria 10-05
        self.assertEqual(self.proxima(), "2026-10-04")  # prova 10-06 − margem 2
        self.assertIn("limitada por prova", self.estado_view())


class TestDominio(Base):
    def setUp(self):
        super().setUp()
        self.topico("t1")
        for q in ("Q1", "Q2", "Q3"):
            self.questao(q)

    def test_exige_tarefa_de_explicacao_ou_aplicacao(self):
        self.topico("t1")
        for i, q in enumerate(("Q1", "Q2", "Q3"), 1):
            self.tent(i, 0.95, "recuperacao", q=q)
        self.assertNotIn("Provisoriamente", self.estado_view())
        self.assertIn("falta explicação/aplicação", self.estado_view())

    def test_exige_mais_de_uma_questao(self):
        self.topico("t1")
        self.tent(1, 0.95, "recuperacao", q="Q1")
        self.tent(2, 0.95, "explicacao", q="Q1")
        self.tent(3, 0.95, "aplicacao", q="Q1")
        self.assertNotIn("Provisoriamente", self.estado_view())
        self.assertIn("única questão", self.estado_view())

    def test_topico_critico_exige_minimo_essencial(self):
        self.topico("t1", "--critico")
        self.tent(1, 0.95, "recuperacao", q="Q1")
        self.tent(2, 0.99, "explicacao", q="Q2")
        self.tent(3, 0.45, "aplicacao", q="Q3")  # média 0,80 mas um essencial falhou
        self.assertNotIn("Provisoriamente", self.estado_view())
        self.assertIn("crítico", self.estado_view())

    def test_provisorio_depois_consistente_apos_intervalo(self):
        self.topico("t1")
        self.tent(1, 0.9, "recuperacao", q="Q1")
        self.tent(2, 0.9, "explicacao", q="Q2")
        self.tent(3, 0.9, "aplicacao", q="Q3")
        self.assertIn("Provisoriamente dominado", self.estado_view())
        self.tent(12, 0.9, "aplicacao", q="Q2")  # >=7 dias depois
        self.assertIn("Domínio consistente", self.estado_view())

    def test_estudar_nao_e_dominar(self):
        self.topico("t1")
        self.run_ok("topico", "marcar", "t1", "--estado", "em_estudo")
        self.assertIn("Em estudo", self.estado_view())
        self.assertNotIn("dominado", self.estado_view().lower().replace("provisoriamente dominado:", ""))

    def test_sem_evidencia_e_nao_avaliado(self):
        self.topico("t1")
        self.assertIn("Não avaliado", self.estado_view())


class TestCronograma(Base):
    def test_sem_datas_nao_inventa(self):
        self.topico("t1")
        out = self.run_ok("risco")
        self.assertIn("Indeterminado", out)

    def test_topico_nao_vencido_nao_e_atraso(self):
        self.topico("t1", "--previsto-ate", "2026-12-01", "--previsto-origem", "oficial")
        out = self.run_ok("risco", now="2026-10-17T10:00")
        self.assertIn("Sob controle", out)

    def test_atraso_confirmado_precisa_de_declaracao(self):
        self.topico("t1", "--previsto-ate", "2026-10-01", "--previsto-origem", "estimada")
        self.assertIn("Atenção necessária", self.run_ok("risco", now="2026-10-17T10:00"))  # sem dado ≠ atraso
        self.run_ok("topico", "marcar", "t1", "--estado", "nao_iniciado", now="2026-10-17T10:00")
        self.assertIn("Atraso confirmado", self.run_ok("risco", now="2026-10-17T10:00"))

    def test_data_exige_origem_valida(self):
        n = len(self.eventos())
        c, _, _ = self.run_cli("data", "--titulo", "AB1", "--data", "2026-11-05", "--origem", "chutei")
        self.assertNotEqual(c, 0)
        c, _, e = self.run_cli("data", "--titulo", "AB1", "--data", "05/11/2026", "--origem", "oficial")
        self.assertEqual(c, 1)
        self.assertIn("inválida", e)
        self.assertEqual(len(self.eventos()), n)


class TestIntegridade(Base):
    def setUp(self):
        super().setUp()
        self.topico("t1")
        self.questao("Q1")
        self.tent(1, 0.9, q="Q1")

    def test_validar_limpo(self):
        c, o, _ = self.run_cli("validar", now="2026-10-01T12:00")
        self.assertEqual(c, 0, o)
        self.assertIn("0 erro(s)", o)

    def test_view_desatualizada_e_detectada(self):
        log = self.d / "dados" / "eventos.jsonl"
        ev = self.eventos()[-1]
        nova = dict(ev, id=f"E{len(self.eventos()) + 1:06d}", evento="pendencia", pendencia="P001", categoria="duvida", texto="x")
        with open(log, "a", encoding="utf-8") as f:  # evento gravado "por fora": views não renderizadas
            f.write(json.dumps(nova, ensure_ascii=False) + "\n")
        c, o, _ = self.run_cli("validar", now="2026-10-01T12:00")
        self.assertEqual(c, 1)
        self.assertIn("desatualizada", o)
        self.run_ok("render", now="2026-10-01T12:00")
        self.assertEqual(self.run_cli("validar", now="2026-10-01T12:00")[0], 0)

    def test_view_editada_a_mao_gera_aviso(self):
        p = self.d / "04_MEMORIA_DO_ALUNO" / "dominio_por_topico.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nDOMINEI TUDO\n", encoding="utf-8")
        c, o, _ = self.run_cli("validar", now="2026-10-01T12:00")
        self.assertIn("editada à mão", o)

    def test_view_ausente_e_erro(self):
        (self.d / "04_MEMORIA_DO_ALUNO" / "estado_atual.md").unlink()
        c, o, _ = self.run_cli("validar", now="2026-10-01T12:00")
        self.assertEqual(c, 1)
        self.assertIn("visão ausente", o)

    def test_log_corrompido_e_detectado(self):
        with open(self.d / "dados" / "eventos.jsonl", "a", encoding="utf-8") as f:
            f.write("{isto não é json\n")
        c, o, _ = self.run_cli("validar")
        self.assertEqual(c, 1)
        self.assertIn("corrompida", o)

    def test_falha_de_gravacao_do_log_nao_finge_sucesso(self):
        log = self.d / "dados" / "eventos.jsonl"
        log.rename(self.d / "dados" / "backup.jsonl")
        log.mkdir()  # gravar vai falhar
        c, o, e = self.run_cli("topico", "add", "t2")
        self.assertEqual(c, 2)
        self.assertIn("NÃO declare que foi salvo", e)
        self.assertNotIn("[verificado]", o)

    def test_falha_ao_gravar_visao_e_reportada(self):
        v = self.d / "04_MEMORIA_DO_ALUNO" / "estado_atual.md"
        v.unlink()
        v.mkdir()
        c, o, e = self.run_cli("topico", "add", "t2")
        self.assertEqual(c, 2)
        self.assertIn("evento gravado, mas as visões falharam", e)

    def test_historico_e_append_only(self):
        antes = (self.d / "dados" / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
        self.tent(2, 0.3, q="Q1", extra=["--erro", "lacuna_conceitual"])
        depois = (self.d / "dados" / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(depois[:len(antes)], antes)
        self.assertEqual(len(depois), len(antes) + 1)

    def test_gabarito_nao_vaza_nas_visoes(self):
        for p in self.d.rglob("*.md"):
            self.assertNotIn("GABARITO-SECRETO", p.read_text(encoding="utf-8"), p.name)
        self.assertIn("GABARITO-SECRETO-Q1", self.run_ok("questao", "gabarito", "Q1"))
        self.assertNotIn("GABARITO", self.run_ok("questao", "ver", "Q1"))

    def test_render_idempotente(self):
        self.run_ok("render", now="2026-10-01T12:00")
        a = {p.name: p.read_text(encoding="utf-8") for p in self.d.rglob("*.md")}
        self.run_ok("render", now="2026-10-01T12:00")
        b = {p.name: p.read_text(encoding="utf-8") for p in self.d.rglob("*.md")}
        self.assertEqual(a, b)

    def test_tentativa_valida_referencias(self):
        self.topico("t2")
        c, _, e = self.run_cli("tentativa", "--topico", "t2", "--questao", "Q1", "--tipo", "recuperacao", "--pontuacao", "1")
        self.assertEqual(c, 1)
        self.assertIn("pertence ao tópico", e)
        c, _, e = self.run_cli("tentativa", "--topico", "nada", "--tipo", "recuperacao", "--pontuacao", "1")
        self.assertEqual(c, 1)
        c, _, e = self.run_cli("tentativa", "--topico", "t1", "--tipo", "recuperacao", "--pontuacao", "1.5")
        self.assertEqual(c, 1)

    def test_questao_nao_sobrescreve(self):
        c, _, e = self.run_cli("questao", "add", "--id", "Q1", "--topico", "t1", "--formato", "resposta_curta", "--dificuldade", "1",
                               "--objetivo", "o", "--enunciado", "e", "--gabarito", "g", "--criterios", "c")
        self.assertEqual(c, 1)
        self.assertIn("já existe", e)


class TestFontes(Base):
    def test_paginas_nunca_inventadas(self):
        f = self.d / "01_FONTES" / "notas.txt"
        f.write_text("conteúdo", encoding="utf-8")
        self.run_ok("fonte", "registrar", "01_FONTES/notas.txt", "--tipo", "anotação")
        self.assertIn("desconhecido (não verificado)", (self.d / "01_FONTES" / "manifesto_de_fontes.md").read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("pdfinfo"), "pdfinfo ausente")
    def test_paginas_verificadas_em_pdf(self):
        pdf = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
               b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R/Size 4>>\n%%EOF\n")
        (self.d / "01_FONTES" / "a.pdf").write_bytes(pdf)
        out = self.run_ok("fonte", "registrar", "01_FONTES/a.pdf")
        self.assertIn("páginas: 1", out)

    def test_detecta_novo_alterado_ausente(self):
        f = self.d / "01_FONTES" / "a.txt"
        f.write_text("v1", encoding="utf-8")
        self.assertIn("NOVO", self.run_ok("fonte", "verificar"))
        self.run_ok("fonte", "registrar", "01_FONTES/a.txt")
        self.assertIn("coincidem", self.run_ok("fonte", "verificar"))
        f.write_text("v2", encoding="utf-8")
        self.assertIn("ALTERADO", self.run_ok("fonte", "verificar"))
        f.unlink()
        self.assertIn("AUSENTE", self.run_ok("fonte", "verificar"))

    def test_rejeita_caminho_fora_da_disciplina(self):
        c, _, e = self.run_cli("fonte", "registrar", "../../../etc/hostname")
        self.assertEqual(c, 1)


class TestMultiplasDisciplinas(Base):
    def test_exige_escolha_quando_ha_varias(self):
        self.run_ok("nova", "fis1", "--nome", "Física I")
        c, _, e = self.run_cli("briefing")
        self.assertEqual(c, 1)
        self.assertIn("-d", e)
        self.run_ok("-d", "fis1", "briefing")

    def test_slug_malicioso_rejeitado(self):
        c, _, e = self.run_cli("nova", "../fora", "--nome", "x")
        self.assertEqual(c, 1)
        self.assertFalse((self.root.parent / "fora").exists())


class TestCorrecoes(Base):
    """Regressões das correções feitas após a simulação de uso com alunos."""

    def setUp(self):
        super().setUp()
        self.topico("t1")
        for q in ("Q1", "Q2", "Q3"):
            self.questao(q)

    # --- 1. escrita simultânea ---------------------------------------------------------
    def test_escrita_simultanea_nao_duplica_ids(self):
        env = {**os.environ, "SAC_ROOT": str(self.root), "SAC_NOW": "2026-10-17T10:00:00-03:00"}
        n0 = len(self.eventos())
        procs = [subprocess.Popen([sys.executable, str(CLI), "pendencia", "add", "--categoria", "duvida",
                                   "--texto", f"p{i}"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True) for i in range(12)]
        saidas = [(p.communicate(), p.returncode) for p in procs]
        self.assertTrue(all(c == 0 for _, c in saidas), saidas)
        evs = self.eventos()
        self.assertEqual(len(evs), n0 + 12)
        self.assertEqual([e["id"] for e in evs], [f"E{i:06d}" for i in range(1, len(evs) + 1)])
        pend = [e["pendencia"] for e in evs if e["evento"] == "pendencia"]
        self.assertEqual(len(pend), len(set(pend)))  # P001..P012 sem colisão
        c, o, _ = self.run_cli("validar", now="2026-10-17T10:00")
        self.assertEqual(c, 0, o)

    # --- 2. próxima ação considera prazo, risco e pré-requisito ---------------------------
    def test_sugestao_prioriza_prazo_vencido(self):
        self.topico("a", "--nome", "a")  # primeiro cadastrado, sem prazo
        self.topico("b", "--previsto-ate", "2026-10-10", "--previsto-origem", "estimada")
        self.run_ok("topico", "marcar", "b", "--estado", "nao_iniciado")
        out = self.run_ok("revisoes", now="2026-10-17T10:00")
        self.assertIn("Começar 'b'", out)
        self.assertIn("prazo vencido em 2026-10-10", out)
        self.assertNotIn("Diagnóstico inicial de 'a'", out)

    def test_sugestao_comeca_pelo_prereq_sem_evidencia(self):
        self.topico("base")
        self.topico("topo", "--prereq", "base", "--previsto-ate", "2026-10-10", "--previsto-origem", "oficial")
        out = self.run_ok("revisoes", now="2026-10-17T10:00")
        self.assertIn("comece pelo pré-requisito 'base'", out)

    def test_sugestao_novo_prefere_menor_prazo(self):
        self.topico("sem_prazo", "--nome", "sem")
        self.topico("com_prazo", "--previsto-ate", "2026-12-01", "--previsto-origem", "estimada")
        for t in ("t1",):
            self.run_ok("topico", "marcar", t, "--estado", "nao_iniciado")
        out = self.run_ok("revisoes", now="2026-10-17T10:00")
        self.assertIn("'com_prazo'", out.split("Sugestão:")[1])

    # --- 3. códigos de saída ------------------------------------------------------------
    def test_erro_de_uso_sai_com_1_e_nao_com_2(self):
        n = len(self.eventos())
        c, _, e = self.run_cli("data", "--titulo", "X", "--data", "2026-11-05", "--origem", "chutei")
        self.assertEqual(c, 1)
        self.assertIn("ERRO:", e)
        c, _, _ = self.run_cli("comando-inexistente")
        self.assertEqual(c, 1)
        self.assertEqual(len(self.eventos()), n)

    # --- 4. tentativa sem sessão ----------------------------------------------------------
    def test_tentativa_sem_sessao_avisa_e_validar_sinaliza(self):
        out = self.tent(17, 0.9, q="Q1")
        self.assertIn("AVISO: não há sessão aberta", out)
        c, o, _ = self.run_cli("validar", now="2026-10-17T12:00")
        self.assertIn("sem sessão vinculada", o)
        self.assertEqual(c, 0)  # aviso, não erro: a evidência não é descartada

    def test_tentativa_com_sessao_nao_avisa(self):
        self.run_ok("sessao", "iniciar", "--objetivo", "x", now="2026-10-17T09:00")
        out = self.tent(17, 0.9, q="Q1")
        self.assertNotIn("não há sessão aberta", out)
        c, o, _ = self.run_cli("validar", now="2026-10-17T12:00")
        self.assertNotIn("sem sessão vinculada", o)

    # --- 5. calibração inclui exatamente 50% ----------------------------------------------
    def test_calibracao_confianca_alta_com_50_por_cento(self):
        self.tent(17, 0.5, q="Q1", extra=["--confianca", "4", "--erro", "confusao_conceitos"])
        v = self.estado_view("dificuldades_recorrentes.md")
        secao = v.split("calibração")[1]
        self.assertIn("t1", secao)
        self.assertNotIn("_Sem registros._", secao.split("##")[0])

    def test_calibracao_nao_marca_confianca_baixa(self):
        self.tent(17, 0.3, q="Q1", extra=["--confianca", "2", "--erro", "esquecimento"])
        secao = self.estado_view("dificuldades_recorrentes.md").split("calibração")[1].split("##")[0]
        self.assertIn("_Sem registros._", secao)

    # --- 6. questões distintas = CADASTRADAS ----------------------------------------------
    def test_tentativas_avulsas_nao_bastam_para_dominio(self):
        self.tent(1, 0.95, "recuperacao")
        self.tent(2, 0.95, "explicacao")
        self.tent(3, 0.95, "aplicacao")  # sem --questao: antes contava como 3 "questões" distintas
        v = self.estado_view()
        self.assertNotIn("Provisoriamente", v)
        self.assertIn("sem questões cadastradas distintas", v)

    def test_tentativa_sem_questao_avisa(self):
        self.assertIn("sem --questao", self.tent(1, 0.9, "recuperacao"))

    def test_duas_questoes_cadastradas_bastam(self):
        self.tent(1, 0.9, "recuperacao", q="Q1")
        self.tent(2, 0.9, "explicacao", q="Q2")
        self.tent(3, 0.9, "aplicacao", q="Q2")
        self.assertIn("Provisoriamente dominado", self.estado_view())

    def test_limiar_de_questoes_e_configuravel(self):
        cfg = self.d / "config.json"
        c = json.loads(cfg.read_text(encoding="utf-8"))
        c["min_questoes_distintas"] = 3
        cfg.write_text(json.dumps(c), encoding="utf-8")
        self.tent(1, 0.9, "recuperacao", q="Q1")
        self.tent(2, 0.9, "explicacao", q="Q2")
        self.tent(3, 0.9, "aplicacao", q="Q2")
        self.assertNotIn("Provisoriamente", self.estado_view())

    # --- log corrompido orienta a recuperação -----------------------------------------------
    def test_log_corrompido_orienta_recuperacao(self):
        with open(self.d / "dados" / "eventos.jsonl", "a", encoding="utf-8") as f:
            f.write("{lixo\n")
        c, _, e = self.run_cli("briefing")
        self.assertEqual(c, 1)
        self.assertIn("Restaure seu backup", e)


class TestGuia(Base):
    """`guia`: o que fazer agora, sem o estudante precisar lembrar comandos."""

    def guia(self, *extra, now="2026-10-17T10:00"):
        return json.loads(self.run_ok(*extra, "guia", "--json", now=now))

    def titulos(self, g):
        return [o["titulo"] for o in g["opcoes"]]

    def test_disciplina_vazia_pede_materiais(self):
        g = self.guia()
        self.assertTrue(self.titulos(g)[0].startswith("Colocar os materiais"))

    def test_sem_nenhuma_disciplina_oferece_criar(self):
        vazio = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, vazio, ignore_errors=True)
        env = {**os.environ, "SAC_ROOT": str(vazio)}
        env.pop("SAC_NOW", None)
        r = subprocess.run([sys.executable, str(CLI), "guia", "--json"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        g = json.loads(r.stdout)
        self.assertEqual(g["opcoes"][0]["acao"], "nova")
        self.assertIsNone(g["disciplina"])

    def test_fonte_nova_vira_opcao(self):
        (self.d / "01_FONTES" / "slides.pdf").write_bytes(b"conteudo")
        g = self.guia()
        self.assertTrue(any(t.startswith("Processar 1 arquivo") for t in self.titulos(g)), self.titulos(g))
        self.assertEqual(g["resumo"]["fontes_pendentes"], 1)

    def test_sessao_aberta_oferece_continuar_e_encerrar(self):
        self.topico("t1")
        self.run_ok("sessao", "iniciar", "--objetivo", "estudar", now="2026-10-17T09:00")
        t = self.titulos(self.guia())
        self.assertIn("Continuar a sessão em andamento", t)
        self.assertIn("Encerrar a sessão", t)
        self.assertNotIn("Começar uma sessão de estudo", t)

    def test_revisao_vencida_vem_antes_de_nova_sessao(self):
        self.topico("t1")
        self.questao("Q1")
        self.tent(10, 0.9, q="Q1")
        t = self.titulos(self.guia(now="2026-10-12T10:00"))
        i_rev = next(i for i, x in enumerate(t) if x.startswith("Fazer as 1 revisão"))
        i_ses = t.index("Começar uma sessão de estudo")
        self.assertLess(i_rev, i_ses)

    def test_numeracao_e_campos_completos(self):
        self.topico("t1")
        g = self.guia()
        todas = g["opcoes"] + g["sempre"]
        self.assertEqual([o["n"] for o in todas], list(range(1, len(todas) + 1)))
        for o in todas:
            self.assertTrue(o["titulo"] and o["dizer"], o)
            self.assertTrue(o["comando"] or o["acao"] or o["titulo"].startswith(("Continuar", "Colocar")), o)

    def test_texto_mostra_frase_e_comando_equivalente(self):
        self.topico("t1")
        out = self.run_ok("guia", now="2026-10-17T10:00")
        self.assertIn("Diga ao agente:", out)
        self.assertIn("Comando equivalente:", out)
        self.assertIn("Abrir-Painel", out)

    def test_varias_disciplinas_sem_d_lista_as_opcoes(self):
        self.run_ok("nova", "fis1", "--nome", "Física I")
        g = self.guia()
        t = " ".join(self.titulos(g))
        self.assertIn("calc1", t)
        self.assertIn("fis1", t)
        self.assertIsNone(g["disciplina"])
        self.assertIn("-d fis1", self.guia("-d", "fis1")["sempre"][0]["comando"])

    def test_guia_nao_grava_nada(self):
        self.topico("t1")
        n = len(self.eventos())
        self.run_ok("guia", now="2026-10-17T10:00")
        self.guia()
        self.assertEqual(len(self.eventos()), n)

    def test_disciplina_inexistente_da_erro(self):
        c, _, e = self.run_cli("-d", "naoexiste", "guia")
        self.assertEqual(c, 1)
        self.assertIn("não existe", e)

    def test_atalhos_de_duplo_clique_existem(self):
        raiz = CLI.parent.parent
        bat = (raiz / "Abrir-Painel.bat").read_bytes()
        self.assertIn(b"\r\n", bat)  # CRLF para o cmd do Windows
        self.assertIn(b"sac.py painel", bat)
        cmd = raiz / "Abrir-Painel.command"
        self.assertIn("sac.py painel", cmd.read_text(encoding="utf-8"))
        if os.name == "posix":
            self.assertTrue(os.access(cmd, os.X_OK))
        self.assertTrue((raiz / "COMECE-AQUI.md").exists())
        self.assertTrue((raiz / ".agents" / "skills" / "sac-guia" / "SKILL.md").exists())


class TestPainel(Base):
    """Painel local: botões sobre o CLI, com defesas contra uso indevido."""

    def setUp(self):
        super().setUp()
        import http.client
        import importlib.util
        import threading
        from unittest import mock
        self.http = http.client
        spec = importlib.util.spec_from_file_location("sac_painel", CLI.parent / "sac_painel.py")
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        env = {"SAC_ROOT": str(self.root)}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("SAC_NOW", None)
        self.srv = self.mod.criar_servidor(0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.porta = self.srv.server_port
        self.token = self.srv.token

    def req(self, metodo, caminho, corpo=None, token=True, headers=None):
        h = {"X-SAC-Token": self.token} if token is True else ({"X-SAC-Token": token} if token else {})
        h.update(headers or {})
        if corpo is not None:
            h["Content-Type"] = "application/json"
        c = self.http.HTTPConnection("127.0.0.1", self.porta, timeout=60)
        c.request(metodo, caminho, body=json.dumps(corpo) if corpo is not None else None, headers=h)
        r = c.getresponse()
        dados = r.read().decode("utf-8")
        c.close()
        return r.status, dados

    def run_acao(self, acao, params=None, disciplina="calc1", **kw):
        st, d = self.req("POST", "/api/run", {"acao": acao, "params": params or {}, "disciplina": disciplina}, **kw)
        return st, json.loads(d)

    def test_pagina_exige_token(self):
        st, _ = self.req("GET", "/", token=False)
        self.assertEqual(st, 403)
        st, _ = self.req("GET", "/?t=errado", token=False)
        self.assertEqual(st, 403)
        st, html = self.req("GET", f"/?t={self.token}", token=False)
        self.assertEqual(st, 200)
        self.assertIn("SAC — Painel", html)
        self.assertIn(self.token, html)

    def test_api_exige_token(self):
        self.assertEqual(self.req("GET", "/api/guia?d=calc1", token=False)[0], 403)
        self.assertEqual(self.req("GET", "/api/guia?d=calc1", token="errado")[0], 403)
        self.assertEqual(self.req("POST", "/api/run", {"acao": "briefing"}, token=False)[0], 403)

    def test_host_e_origin_de_fora_sao_barrados(self):
        self.assertEqual(self.req("GET", "/api/guia?d=calc1", headers={"Host": "evil.example"})[0], 403)
        st, _ = self.req("POST", "/api/run", {"acao": "briefing", "disciplina": "calc1"},
                         headers={"Origin": "http://evil.example"})
        self.assertEqual(st, 403)

    def test_guia_via_api(self):
        st, d = self.req("GET", "/api/guia?d=calc1")
        self.assertEqual(st, 200)
        g = json.loads(d)
        self.assertEqual(g["disciplina"], "calc1")
        self.assertTrue(g["opcoes"])

    def test_botao_briefing_executa_o_cli(self):
        st, r = self.run_acao("briefing")
        self.assertEqual(st, 200)
        self.assertEqual(r["codigo"], 0)
        self.assertIn("RELÓGIO", r["saida"])
        self.assertIn("sac.py -d calc1 briefing", r["comando"])  # ensina o comando equivalente

    def test_formulario_grava_com_verificacao(self):
        st, r = self.run_acao("sessao_iniciar", {"objetivo": "Estudar limites"})
        self.assertEqual((st, r["codigo"]), (200, 0), r)
        self.assertIn("[verificado]", r["saida"])
        self.assertEqual([e["evento"] for e in self.eventos()][-1], "sessao_inicio")
        st, r = self.run_acao("sessao_encerrar", {"resumo": "ok", "proximo": "x", "concluida": "parcial"})
        self.assertEqual(r["codigo"], 0, r)

    def test_erro_do_cli_volta_com_codigo_1_e_nao_grava(self):
        n = len(self.eventos())
        st, r = self.run_acao("data_registrar", {"titulo": "VA", "data": "31/11/2026", "origem": "oficial"})
        self.assertEqual((st, r["codigo"]), (200, 1))
        self.assertIn("ERRO", r["erro"])
        self.assertEqual(len(self.eventos()), n)

    def test_acao_desconhecida_e_campo_faltando_sao_400(self):
        self.assertEqual(self.req("POST", "/api/run", {"acao": "rm_rf"})[0], 400)
        self.assertEqual(self.req("POST", "/api/run", {"acao": "sessao_iniciar", "params": {}, "disciplina": "calc1"})[0], 400)
        self.assertEqual(self.req("POST", "/api/run", {"acao": "briefing", "disciplina": "../etc"})[0], 400)
        self.assertEqual(self.req("POST", "/api/run", {"acao": "topico_marcar", "params": {"topico": "--x", "estado": "em_estudo"},
                                                       "disciplina": "calc1"})[0], 400)

    def test_valor_comecando_com_hifens_nao_vira_opcao(self):
        st, r = self.run_acao("sessao_iniciar", {"objetivo": "--bomba"})
        self.assertEqual(r["codigo"], 0, r)
        self.assertEqual([e for e in self.eventos() if e["evento"] == "sessao_inicio"][-1]["objetivo"], "--bomba")

    def test_texto_com_shell_nao_e_executado(self):
        marca = self.root / "pwn"
        st, r = self.run_acao("sessao_iniciar", {"objetivo": f"x; touch {marca} && echo $(id)"})
        self.assertEqual(r["codigo"], 0, r)
        self.assertFalse(marca.exists())

    def test_criar_disciplina_pelo_painel(self):
        st, r = self.run_acao("nova", {"slug": "fis1", "nome": "Física I"}, disciplina="")
        self.assertEqual((st, r["codigo"]), (200, 0), r)
        self.assertTrue((self.root / "disciplinas" / "fis1" / "config.json").exists())


if __name__ == "__main__":
    unittest.main()
