# Comece aqui

Você **não precisa decorar comandos**. Há três jeitos de usar o SAC, do mais fácil ao mais manual.

## 1. Painel com botões (sem digitar nada)

- **Windows:** dê duplo clique em `Abrir-Painel.bat`.
- **macOS:** dê duplo clique em `Abrir-Painel.command`. **Linux:** `./Abrir-Painel.command`.

Abre uma página no seu navegador, só neste computador. Ela mostra **o que fazer agora** e tem botões para
situação, revisões, risco, relatório, validação, iniciar/encerrar sessão, registrar datas e criar disciplinas.
Cada cartão traz a **frase para colar no agente** e o **comando equivalente**.
Se o painel não abrir, falta o Python: instale em python.org, marcando "Add python.exe to PATH".

## 2. Conversa com o agente

Abra esta pasta no seu agente (Antigravity, Claude Code etc.) e diga **"oi"** ou **"menu"**.
O agente roda o guia e mostra **opções para escolher** (clicáveis, quando a ferramenta permite, ou numeradas:
responda só com o número). Ele faz o resto: ingestão, perguntas, correção e registro.

## 3. Guia no terminal (quando quiser ver tudo)

```
python3 scripts/sac.py guia
```
No Windows, use `python` ou `py` no lugar de `python3`. O guia lista as opções numeradas, a frase para dizer
ao agente e o comando equivalente de cada uma.

## Primeira vez, em 5 passos

1. Abra o painel (ou diga "oi" ao agente).
2. **Criar disciplina:** botão "Criar disciplina" (ou: "Crie a disciplina Cálculo I").
3. Coloque os arquivos da matéria em `disciplinas/<apelido>/01_FONTES/`.
4. Diga ao agente: **"Faça a ingestão dos materiais."** Ele cadastra fontes e tópicos e mostra um relatório.
5. Diga **"Vamos estudar"**. Responda às perguntas **antes** de ver o gabarito. No fim: **"Encerrar sessão."**

Chegou material novo do professor? Coloque na mesma pasta e diga "Tem material novo". O sistema detecta arquivos novos,
alterados e ausentes sozinho.

## Colinha de comandos (só se precisar; o painel e o agente já fazem isso)

| Quero | Comando |
|---|---|
| Ver o que fazer agora | `python3 scripts/sac.py guia` |
| Abrir o painel | `python3 scripts/sac.py painel` |
| Minha situação | `python3 scripts/sac.py briefing` |
| O que revisar | `python3 scripts/sac.py revisoes` |
| Risco de atraso | `python3 scripts/sac.py risco` |
| Relatório semanal | `python3 scripts/sac.py relatorio` |
| Conferir integridade | `python3 scripts/sac.py validar` |
| Materiais novos? | `python3 scripts/sac.py fonte verificar` |
| Criar disciplina | `python3 scripts/sac.py nova calc1 --nome "Cálculo I"` |

Com mais de uma disciplina, acrescente `-d <apelido>` logo depois de `sac.py`.
Faça backup da pasta `disciplinas/`: o seu histórico inteiro está lá.
