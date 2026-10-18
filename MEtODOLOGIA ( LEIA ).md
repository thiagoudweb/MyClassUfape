# Sistema de Aprendizagem Contínua
## Arquitetura e especificação funcional do harness acadêmico

## 1. Visão geral

O Sistema de Aprendizagem Contínua (SAC) é um harness acadêmico para organizar e acompanhar o estudo de uma disciplina ao longo do tempo. Ele integra materiais fornecidos pelo estudante, pesquisa complementar, planejamento acadêmico, memória persistente, avaliação de aprendizagem e acompanhamento de desempenho.

O sistema não se limita a responder perguntas ou produzir resumos. Sua função é manter uma representação organizada da disciplina e do percurso de aprendizagem do estudante, identificar lacunas de conhecimento e orientar a próxima atividade de estudo com base em evidências.

### Objetivos centrais

- Usar os materiais acadêmicos fornecidos como base principal do estudo.
- Organizar PDFs, ementa, bibliografia, exercícios e avaliações.
- Relacionar os tópicos estudados à estrutura e ao cronograma da disciplina.
- Manter memória persistente em arquivos Markdown.
- Registrar sessões, progresso, dificuldades, erros e revisões.
- Gerar explicações, analogias, resumos, mapas mentais, esquemas, flashcards, quizzes e exercícios.
- Acompanhar a retenção e a capacidade de aplicar o conhecimento.
- Detectar lacunas, riscos de atraso e necessidades de replanejamento.
- Retomar o estudo do ponto correto após uma interrupção.
- Validar informações acadêmicas, avaliações e atualizações da memória.

O resultado esperado é uma aprendizagem estruturada, contínua, verificável e adaptada ao desempenho real do estudante.

## 2. Princípios de funcionamento

### 2.1. Materiais da disciplina como fonte principal

Os documentos fornecidos pelo estudante constituem a referência primária para compreender o conteúdo, a terminologia, a abordagem e as exigências da disciplina.

A hierarquia de fontes considera:

1. Instruções, enunciados e critérios oficiais da disciplina.
2. Ementa, cronograma e materiais indicados pelo professor.
3. PDFs, livros, slides, listas, exercícios e provas fornecidos.
4. Fontes externas confiáveis usadas para aprofundamento, esclarecimento ou atualização.
5. Conhecimento geral do modelo, com verificação quando necessário.

A hierarquia não elimina a necessidade de detectar erros, desatualizações ou contradições. Divergências entre fontes devem ser registradas e explicadas.

O sistema distingue informações confirmadas, inferências, hipóteses provisórias e informações desconhecidas. Não inventa referências, páginas, datas, resultados, duração de sessões ou progresso acadêmico.

### 2.2. Aprendizagem verificável

Ler um resumo, receber uma explicação ou passar tempo em um tópico não constitui, por si só, evidência de domínio.

O domínio é acompanhado por meio de recuperação independente, explicação com as próprias palavras, aplicação em exercícios, transferência para problemas novos e retenção ao longo do tempo.

### 2.3. Continuidade e rastreabilidade

As mudanças importantes no estado de aprendizagem são registradas com evidências rastreáveis. O histórico de avaliações e erros é preservado para permitir análises longitudinais.

O sistema distingue observações diretas, resultados objetivos e inferências. Informações incertas permanecem identificadas como tais.

## 3. Arquitetura de diretórios e arquivos

A estrutura abaixo separa fontes acadêmicas, conhecimento elaborado, memória do estudante, sessões, avaliações, planejamento e validação.

```text
/
├── CLAUDE.md
├── 00_ORIENTACAO/
│   ├── protocolo_operacional.md
│   └── preferencias_de_estudo.md
├── 01_FONTES/
│   ├── PDFs originais
│   ├── bibliografia
│   ├── provas e exercícios
│   └── manifesto_de_fontes.md
├── 02_MAPA_DA_DISCIPLINA/
│   ├── ementa.md
│   ├── mapa_conceitual.md
│   ├── pre_requisitos.md
│   └── calendario_academico.md
├── 03_CONHECIMENTO/
│   ├── indice_de_conteudos.md
│   └── topicos/
│       └── arquivos individuais por tópico
├── 04_MEMORIA_DO_ALUNO/
│   ├── perfil_de_aprendizagem.md
│   ├── estado_atual.md
│   ├── dominio_por_topico.md
│   ├── dificuldades_recorrentes.md
│   ├── catalogo_de_erros.md
│   ├── revisoes_pendentes.md
│   └── historico_de_evolucao.md
├── 05_SESSOES/
│   ├── indice_de_sessoes.md
│   └── registros individuais por sessão
├── 06_AVALIACOES/
│   ├── banco_de_questoes.md
│   ├── historico_de_tentativas.md
│   └── rubricas_de_correcao.md
├── 07_PLANEJAMENTO/
│   ├── plano_de_estudos.md
│   ├── metas_semanais.md
│   └── analise_de_cronograma.md
├── 08_RELATORIOS/
│   ├── relatorio_semanal.md
│   └── relatorio_de_desempenho.md
└── 09_VALIDACAO/
    ├── log_de_validacao.md
    └── pendencias_e_conflitos.md
```

A estrutura pode ser adaptada às capacidades do ambiente, evitando arquivos redundantes e duplicação desnecessária de informações.

### 3.1. Arquivos centrais

**`CLAUDE.md`**  
Contém a descrição operacional do sistema, regras permanentes, hierarquia de fontes, protocolo de sessão, padrões de atualização e referências aos arquivos centrais.

**`estado_atual.md`**  
É o ponto de entrada para a continuidade do estudo. Registra a disciplina, objetivo atual, última sessão, tópico em andamento, último ponto demonstrado, próxima ação, dúvidas abertas, revisões pendentes, tempo acumulado quando mensurável, horário da atualização e pendências operacionais.

**`dominio_por_topico.md`**  
Registra o estado de cada tópico, seus pré-requisitos, tentativas de avaliação, desempenho, erros, evidências de domínio e próxima revisão.

**`catalogo_de_erros.md`**  
Mantém um histórico dos erros significativos, seu contexto, causa provável, correção, exercício de recuperação e resultado da nova tentativa.

**`revisoes_pendentes.md`**  
Mantém uma fila de revisões priorizada pelo risco de esquecimento, importância acadêmica, dificuldade observada e proximidade de avaliações.

**`indice_de_conteudos.md`**  
Permite localizar materiais e conhecimentos elaborados sem inserir resumos extensos nos arquivos de estado global.

### 3.2. Integridade da memória

- Consultar os arquivos pertinentes antes de afirmar conhecer o histórico.
- Registrar a origem das informações acadêmicas importantes.
- Atualizar estado e índices após sessões relevantes.
- Preservar tentativas anteriores e resultados históricos.
- Evitar estados contraditórios sem explicação.
- Usar datas ISO (`AAAA-MM-DD`) e timestamps com fuso horário quando disponíveis.
- Distinguir observações, resultados e inferências.
- Confirmar a gravação antes de considerar uma alteração persistida.
- Manter histórico suficiente para reconstruir decisões importantes.
- Evitar registrar dados pessoais desnecessários.
- Nunca tratar a existência de uma anotação como prova de domínio.

Quando o ambiente não permitir gravar arquivos, a limitação deve ser explícita e o conteúdo atualizado deve ser disponibilizado para salvamento.

## 4. Ingestão e organização de materiais

A ingestão transforma os documentos originais em uma base de conhecimento organizada, rastreável e vinculada à ementa.

### 4.1. Inventário

Para cada arquivo, identificar nome, formato, tipo de documento, disciplina, possíveis duplicatas, versão, estado de processamento e eventuais problemas de leitura.

A disponibilização de um PDF não significa que todo o seu conteúdo foi extraído corretamente.

### 4.2. Extração e validação

Extrair texto e, quando necessário, examinar tabelas, fórmulas, gráficos, figuras, legendas e páginas digitalizadas. Quando a extração textual for insuficiente, usar leitura visual ou OCR, se disponível.

As limitações de leitura que possam afetar a interpretação devem ser registradas.

### 4.3. Manifesto de fontes

Cada documento recebe um identificador e um registro com:

- Nome do arquivo e tipo de documento.
- Função acadêmica.
- Data ou versão, quando conhecida.
- Número de páginas, quando verificável.
- Assuntos abordados.
- Localização dos assuntos por página ou seção.
- Confiabilidade e limitações conhecidas.
- Relações com os tópicos da ementa.

Páginas, referências bibliográficas e outros metadados não devem ser inventados.

### 4.4. Mapeamento conceitual

O conteúdo é organizado em tópicos, subtópicos, definições, fórmulas, argumentos, exemplos, exercícios e relações entre conceitos.

O mapa identifica pré-requisitos, conceitos fundamentais, intermediários e avançados, aplicações e temas transversais. Quando útil, os tópicos são representados em uma árvore hierárquica e em um grafo de dependências.

### 4.5. Vinculação à ementa

Cada tópico extraído é associado aos itens da ementa e classificado como:

- Correspondência explícita.
- Correspondência provável.
- Conteúdo complementar.
- Conteúdo ainda não localizado.
- Divergência a investigar.

A cobertura da disciplina só é considerada completa após a conferência de todos os itens da ementa.

### 4.6. Relatório de ingestão

O processo gera um relatório com arquivos processados, tópicos identificados, cobertura estimada da ementa, problemas de leitura, conflitos, pendências e próximos passos.

## 5. Ementa, calendário e progresso acadêmico

A ementa fornece a estrutura oficial do conteúdo, mas não é necessariamente um calendário completo.

O sistema extrai unidades, tópicos, objetivos de aprendizagem, sequência prevista, datas explícitas, avaliações, entregas, pré-requisitos e bibliografia.

Cada data recebe uma origem e uma classificação: oficial, confirmada pelo estudante, estimada ou desconhecida. Datas ausentes não são inventadas. Na ausência de calendário, pode ser criado um plano provisório claramente identificado como estimativa.

### 5.1. Indicadores separados

O acompanhamento mantém indicadores distintos para:

- Cobertura do conteúdo programático.
- Progresso de estudo.
- Domínio demonstrado.
- Revisões em dia.
- Desempenho em avaliações.
- Proximidade de prazos acadêmicos.

Um tópico estudado pode não estar dominado; um tópico dominado pode precisar de revisão. Essas situações permanecem distintas.

### 5.2. Análise de atraso

A análise considera datas oficiais, prazos restantes, conteúdo previsto, conteúdo estudado, domínio demonstrado, tempo semanal disponível, esforço estimado para concluir lacunas e margem para revisões.

O risco é classificado como:

- Sob controle.
- Atenção necessária.
- Atraso provável.
- Atraso confirmado.

Cada classificação deve ser acompanhada das evidências que a sustentam. O estudante não é considerado atrasado apenas por não dominar um tópico que ainda não estava previsto para conclusão.

Quando houver risco, o plano é reorganizado considerando pré-requisitos, relevância acadêmica, avaliações próximas e carga de trabalho realista.

## 6. Gestão de sessões e continuidade

O sistema mantém um estado persistente da sessão para retomar o estudo sem reiniciar o processo do zero.

### 6.1. Recuperação no início

No início de uma sessão, são consultados:

1. `estado_atual.md`.
2. `dominio_por_topico.md`.
3. `revisoes_pendentes.md`.
4. Registro da última sessão.
5. Calendário e plano de estudos.
6. Alterações relevantes nos materiais ou no cronograma.

O sistema recupera o ponto em que o estudante parou, as dúvidas abertas e a próxima atividade recomendada. Quando não existe histórico, inicia-se uma configuração diagnóstica.

### 6.2. Abertura contextualizada

A abertura apresenta brevemente o último ponto estudado, o que foi demonstrado, a próxima atividade recomendada, revisões importantes e situação do cronograma quando relevante.

O estudante pode escolher entre retomar o estudo, responder perguntas de recuperação, consultar um resumo, mapa mental ou esquema, revisar pontos fracos, resolver exercícios, fazer um quiz ou ajustar o planejamento.

As opções são flexíveis e não exigem revisar todo o conteúdo a cada sessão.

### 6.3. Temporizador

Quando houver suporte técnico, o sistema permite iniciar, pausar, retomar e encerrar um temporizador, persistindo seu estado.

Cada sessão registra, quando disponível:

- Identificador da sessão.
- Data e horário de início e fim.
- Pausas e retomadas.
- Duração efetiva mensurável.
- Objetivo e tópicos abordados.
- Atividades e resultados.
- Dificuldades observadas.
- Próxima ação.

O sistema diferencia tempo de relógio decorrido, tempo com o temporizador ativo e tempo efetivamente dedicado ao estudo. Não infere tempo real de estudo apenas pelo intervalo entre mensagens.

Se o ambiente não tiver temporizador persistente, essa limitação deve ser informada e deve ser oferecido um registro manual ou mecanismo externo.

### 6.4. Encerramento e retomada

Ao encerrar uma sessão, o sistema:

1. Resume o conteúdo estudado.
2. Identifica o que foi demonstrado.
3. Registra erros e dúvidas.
4. Atualiza os indicadores de domínio.
5. Programa revisões.
6. Atualiza o plano de estudos.
7. Registra o tempo conforme as evidências disponíveis.
8. Atualiza o estado atual e o registro da sessão.
9. Confere a consistência entre os arquivos alterados.
10. Informa o ponto exato de retomada.

Se não houver encerramento formal, a última informação confiável é preservada e dados incompletos são identificados como pendentes.

## 7. Motor pedagógico adaptativo

O motor pedagógico combina técnicas de aprendizagem de acordo com o objetivo, o conteúdo, a dificuldade e o desempenho observado.

### 7.1. Diagnóstico

Para cada tópico novo, identifica conhecimento prévio, pré-requisitos consolidados, concepções equivocadas, complexidade adequada e objetivo da sessão. O diagnóstico utiliza poucas perguntas informativas e não interpreta ausência de resposta como prova de desconhecimento.

### 7.2. Recuperação ativa

Antes de reapresentar conteúdo conhecido, o sistema solicita, quando apropriado, que o estudante tente recuperá-lo sem consultar o material. Pode utilizar perguntas abertas, explicações com as próprias palavras, reconstrução de processos, recordação de fórmulas, resolução de problemas e comparação entre conceitos.

O feedback é fornecido após a tentativa.

### 7.3. Repetição espaçada

Cada tópico possui uma fila de revisão. Intervalos iniciais podem seguir uma sequência provisória — por exemplo, 1, 3, 7, 14 e 30 dias —, ajustada conforme desempenho, dificuldade, retenção e proximidade de avaliações.

Esses intervalos são pontos de partida, não regras universais. Erros, baixa confiança ou esquecimento antecipam revisões; recuperação consistente em diferentes ocasiões pode ampliar os intervalos.

### 7.4. Prática intercalada

Após uma base inicial, questões de tópicos relacionados ou procedimentos semelhantes podem ser combinadas para treinar a seleção da estratégia adequada. A intercalação não deve dificultar desnecessariamente a compreensão inicial de um conceito fundamental.

### 7.5. Progressão didática

Uma sequência típica de ensino inclui:

1. Diagnóstico do conhecimento prévio.
2. Explicação do conceito central.
3. Analogia concreta.
4. Limites da analogia.
5. Exemplo resolvido.
6. Exemplo resolvido em conjunto.
7. Exercício independente.
8. Questão de transferência.
9. Correção e feedback.
10. Registro do resultado e programação da revisão.

A sequência se adapta a conteúdos teóricos, práticos, matemáticos, históricos e argumentativos.

### 7.6. Explicações e analogias

As explicações são claras e tecnicamente precisas, organizadas em camadas: intuição, definição formal, mecanismo, exemplo real, exceções e aplicação.

Analogias conectam conceitos abstratos a situações cotidianas, processos e sistemas reais. Cada analogia esclarece um mecanismo específico e explicita onde deixa de funcionar. Comparações que introduzam erros conceituais são evitadas.

### 7.7. Exemplos e problemas

A progressão reduz gradualmente o apoio: demonstração, resolução conjunta, resolução independente e problema novo. A dificuldade cresce conforme a preparação do estudante, incluindo transferência para situações diferentes das usadas no ensino inicial.

## 8. Avaliações, quizzes e correção

As avaliações são alinhadas aos objetivos da disciplina e às fontes disponíveis.

### 8.1. Formatos

O sistema pode gerar:

- Múltipla escolha.
- Resposta curta.
- Explicação conceitual.
- Verdadeiro ou falso com justificativa.
- Associação de conceitos.
- Resolução de problemas.
- Análise de casos.
- Identificação e correção de erros.
- Questões cumulativas.
- Questões de transferência.

### 8.2. Estrutura das questões

Cada questão deve possuir identificador, tópico, objetivo avaliado, dificuldade estimada, enunciado inequívoco, resposta esperada, critérios de correção, explicação da solução, fonte quando aplicável e erros conceituais que pretende detectar.

Em múltipla escolha, os distratores devem representar equívocos plausíveis, sem ambiguidades artificiais.

### 8.3. Aplicação e feedback

Quando adequado, uma pergunta é apresentada por vez, sem revelar o gabarito antes da tentativa. O estudante pode explicar seu raciocínio.

Uma resposta incorreta é analisada para identificar a causa provável. A correção inclui o erro, sua explicação, o raciocínio correto e uma nova oportunidade de aplicação.

Cada tentativa registra a resposta, solução esperada, pontuação, critérios, tipo de erro, confiança declarada quando coletada, feedback e resultado de eventual nova tentativa.

### 8.4. Avaliações cumulativas

Avaliações periódicas combinam conteúdos antigos e novos, usando questões inéditas e problemas integradores. O desempenho imediato é separado da retenção após um intervalo.

Uma única questão repetida não é suficiente para comprovar domínio consistente.

## 9. Modelo de domínio por tópico

Os estados possíveis são:

- Não avaliado.
- Não iniciado.
- Em estudo.
- Compreensão inicial.
- Em consolidação.
- Provisoriamente dominado.
- Domínio consistente.
- Revisão necessária.

O domínio é avaliado separadamente em compreensão conceitual, recuperação independente, aplicação, transferência, retenção e consistência entre tentativas.

Cada estado deve ter critérios explícitos, resultados e data da última evidência. Um critério inicial possível é desempenho de pelo menos 80% em questões representativas, acompanhado de explicação ou aplicação. Esse limiar é ajustável e não substitui a verificação de competências essenciais em tópicos críticos.

O domínio consistente exige evidências repetidas, incluindo avaliações posteriores ao estudo inicial. Resultados contraditórios mantêm a classificação conservadora até uma avaliação complementar.

## 10. Análise de dificuldades

O perfil de dificuldades é atualizado com base em evidências como:

- Tópicos com menor desempenho.
- Erros recorrentes.
- Pré-requisitos frágeis.
- Conceitos frequentemente confundidos.
- Tempo excessivo em tarefas, quando medido.
- Divergência entre confiança e desempenho.
- Esquecimento após intervalos.
- Problemas resolvidos com ajuda, mas não de forma independente.

Cada dificuldade significativa registra evidência, interpretação provável, confiança na interpretação, intervenção recomendada, exercício de recuperação, resultado posterior e próxima revisão.

Causas psicológicas não são tratadas como fatos com base em uma única resposta. O percentual geral de acertos não substitui a análise das habilidades efetivamente avaliadas.

## 11. Pesquisa externa e aprofundamento

A pesquisa externa complementa os materiais da disciplina quando agrega valor: esclarecimento de conceitos, verificação de informações desatualizadas, exemplos, resolução de divergências, aprofundamento e aplicações interdisciplinares.

As fontes priorizadas incluem artigos científicos e revisões sistemáticas, livros acadêmicos, documentação oficial, instituições de pesquisa e fontes primárias pertinentes.

Quando possível, cada referência registra título, autoria, data, instituição ou publicação, link e a afirmação sustentada. O sistema diferencia conteúdo exigido pela disciplina de aprofundamento opcional e não afirma ter consultado fontes às quais não teve acesso.

Conflitos entre materiais didáticos e fontes externas são explicados e mantidos rastreáveis.

## 12. Geração de materiais de estudo

O formato é escolhido de acordo com o objetivo pedagógico.

### Resumos
Sintetizam conceitos essenciais, relações causais, definições, exemplos, exceções e referências, sem confundir síntese com transcrição.

### Mapas mentais
Organizam conceitos centrais, ramos, subtemas e conexões. Podem ser produzidos em Markdown ou em formato compatível com ferramentas de visualização.

### Esquemas e tabelas comparativas
Representam processos, classificações, diferenças conceituais, fórmulas e sequências.

### Flashcards
Avaliam unidades de conhecimento bem definidas, com respostas verificáveis e contexto suficiente.

### Listas de exercícios
São organizadas por objetivo, pré-requisito e dificuldade, com soluções comentadas e critérios de correção.

### Guias de revisão
Priorizam conteúdo frágil, esquecido ou necessário em breve, evitando distribuir o tempo igualmente quando as evidências indicam necessidades diferentes.

## 13. Planejamento adaptativo

O plano concilia objetivos acadêmicos, calendário oficial, disponibilidade semanal, dificuldade dos tópicos, pré-requisitos, revisões pendentes, desempenho recente, avaliações futuras e margem de segurança.

Quando a disponibilidade muda, o plano é reorganizado. As prioridades consideram relevância acadêmica, dependências conceituais, risco de esquecimento e proximidade de avaliações.

Objetivos amplos são divididos em entregas observáveis e verificáveis. A revisão semanal compara plano e execução, identifica desvios e propõe ajustes realistas, sem culpabilizar o estudante.

## 14. Relatórios de desempenho

Relatórios periódicos incluem:

- Conteúdo estudado e objetivos concluídos.
- Tópicos dominados e em consolidação.
- Evolução nas avaliações.
- Desempenho por tipo de questão.
- Dificuldades recorrentes.
- Revisões vencidas.
- Tempo de estudo, quando medido.
- Progresso em relação à ementa.
- Situação do cronograma.
- Principais riscos e próximas prioridades.

As comparações longitudinais usam métricas consistentes. Tendências são diferenciadas de causalidade: uma melhora observada não é atribuída a um método específico sem evidências suficientes. Não são produzidos dados, gráficos ou indicadores de falsa precisão.

## 15. Validação e controle de qualidade

### 15.1. Validação acadêmica

- A afirmação corresponde à fonte citada?
- A página ou seção indicada existe?
- A explicação preserva o significado do conceito?
- Fórmulas e cálculos foram conferidos?
- Há divergências entre fontes?
- Fatos e inferências estão diferenciados?

### 15.2. Validação pedagógica

- A questão avalia o objetivo proposto?
- O gabarito corresponde ao enunciado?
- Os critérios de correção são explícitos?
- A dificuldade é adequada?
- O feedback mostra como corrigir o erro?
- O domínio atribuído possui evidências suficientes?

### 15.3. Validação operacional

- A sessão foi registrada?
- As revisões foram atualizadas?
- O estado atual corresponde ao histórico?
- As datas possuem origem identificada?
- O tempo registrado é verificável?
- Os arquivos relacionados permanecem consistentes?

Falhas, correções e pendências são registradas em `log_de_validacao.md` ou `pendencias_e_conflitos.md`. Quando uma validação não puder ser concluída, a incerteza permanece explícita.

## 16. Modos operacionais

O sistema oferece modos flexíveis, acionáveis por linguagem natural:

- **Retomar:** recuperar o estado e continuar.
- **Diagnóstico:** avaliar o conhecimento atual.
- **Ensinar:** explicar um tópico progressivamente.
- **Quiz:** avaliar sem revelar as respostas antecipadamente.
- **Revisão:** recuperar conteúdos estudados.
- **Mapa mental:** organizar conceitos e conexões.
- **Resumo:** sintetizar o conteúdo com precisão.
- **Exercícios:** praticar por dificuldade.
- **Simulado:** realizar avaliação cumulativa.
- **Desempenho:** analisar resultados e dificuldades.
- **Planejamento:** ajustar metas e cronograma.
- **Auditoria:** verificar materiais, memórias e consistência.
- **Encerrar sessão:** consolidar registros e definir a retomada.

Os modos são atalhos, não comandos obrigatórios. O sistema também compreende solicitações em linguagem natural e adapta sua execução.

## 17. Critérios de qualidade do harness

O sistema é avaliado por sua capacidade de:

1. Recuperar corretamente o ponto de continuidade.
2. Localizar e citar os materiais utilizados.
3. Identificar lacunas reais de conhecimento.
4. Gerar questões válidas e feedback útil.
5. Acompanhar a evolução da recuperação e da aplicação do conhecimento.
6. Programar revisões coerentes.
7. Manter um cronograma acadêmico confiável.
8. Preservar a integridade das memórias.
9. Evitar alegações de progresso sem evidências.
10. Operar com transparência diante de limitações técnicas.

Esses critérios são requisitos verificáveis, não capacidades presumidas.

## 18. Requisitos de implementação e testes

A implementação depende das ferramentas e permissões do ambiente.

### Inspeção
Identificar ferramentas, permissões, arquivos, meios de leitura de PDFs, mecanismos de timestamp, gravação persistente, temporizador e automação.

### Fundação
Criar os diretórios, arquivos centrais, modelos de memória e sessão, padrões de data e regras de atualização.

### Ingestão acadêmica
Indexar materiais, ler a ementa, construir o mapa da disciplina, vincular tópicos a fontes e registrar lacunas.

### Motor de aprendizagem
Implementar protocolos de ensino, avaliações, critérios de domínio, feedback e revisão espaçada.

### Validação operacional
Testar o início de uma sessão, registro, encerramento e retomada. Verificar a recuperação correta do estado, dificuldades, revisões e planejamento. Testar também respostas incorretas, arquivos incompletos, ausência de datas e falhas de gravação.

### Entrega e manutenção
Documentar os componentes implementados, testes realizados, resultados, limitações e dependências externas. Capacidades indisponíveis devem ser identificadas, sem simulação de funcionamento.

A estrutura deve ser construída em etapas pequenas, preservando os arquivos existentes e validando cada etapa antes de avançar.

## 19. Princípio orientador

O harness deve priorizar aprendizagem verificável, memória consistente, fontes rastreáveis e continuidade confiável. O progresso precisa ser demonstrado, o planejamento fundamentado e as limitações explícitas.

Seu valor está em sustentar uma compreensão profunda, duradoura e aplicável da disciplina ao longo do tempo.
