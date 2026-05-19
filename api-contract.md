# Giordine API — Contrato de Interface

> Arquivo mantido pelo agente de backend.
> Atualizar sempre que adicionar, remover ou alterar endpoint, campo ou comportamento.
> Última atualização: Sessão 3 — Módulo de Tarefas (Mini-fatias 1A+1B+2+3 — MVP FIB completo).

---

## Autenticação

Todos os endpoints protegidos exigem header:
```
Authorization: Bearer <access_token>
```

Access token expira em **60 minutos**. Refresh token expira em **7 dias**.

### Erros de autenticação padrão
| Status | Situação |
|---|---|
| 401 | Token inválido, expirado ou ausente |
| 403 | Usuário sem permissão (ex: aluno tentando rota admin, acesso bloqueado) |

---

## Rotas de Auth — `/auth`

### `POST /auth/login`
Pública — não requer token.

**Request:**
```json
{ "username": "string", "senha": "string" }
```

**Response 200:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer"
}
```

**Erros:**
- `401` credenciais inválidas ou usuário inativo
- `403` acesso bloqueado — exibir mensagem: *"Entre em contato com seu professor"*

---

### `POST /auth/refresh`
Pública — não requer token.

**Request:**
```json
{ "refresh_token": "string" }
```

**Response 200:** mesmo shape de `TokenResponse` acima.

**Erros:** `401` token inválido ou expirado.

---

### `POST /auth/logout`
Pública no backend (mas enviar o refresh token do usuário logado).

**Request:**
```json
{ "refresh_token": "string" }
```

**Response 200:** `{ "message": "logged out" }`

---

### `GET /auth/me`
Requer token. Retorna dados do usuário logado + badge de comunicados.

**Response 200:**
```json
{
  "id": 1,
  "nome": "string",
  "username": "string",
  "email": "string",
  "role": "aluno" | "professor" | "admin",
  "nivel": "básico" | "básico_2" | "básico_3" | "intermediário" | ... | null,
  "foto_url": "string" | null,
  "idioma_portal": "pt" | "en",
  "acesso_liberado": true,
  "comunicados_nao_lidos": 0
}
```

> `comunicados_nao_lidos` só é calculado para role `aluno`. Para outros roles, retorna 0.

---

## Rotas Admin — `/admin`
Todos os endpoints abaixo exigem role `admin`.

### `GET /admin/dashboard`
```json
{
  "total_alunos_ativos": 0,
  "total_turmas_ativas": 0,
  "total_professores": 0,
  "comunicados_mes": 0,
  "ultimos_alunos": [
    { "id": 1, "nome": "", "username": "", "nivel": null, "criado_em": "datetime" }
  ],
  "comunicados_recentes": [
    { "id": 1, "titulo": "", "criado_em": "datetime", "turma_id": null }
  ],
  "acessos_bloqueados": [
    { "id": 1, "nome": "", "username": "", "nivel": null }
  ]
}
```

---

### `GET /admin/alunos`
```json
[
  {
    "id": 1,
    "nome": "",
    "username": "",
    "email": "",
    "nivel": null,
    "acesso_liberado": true,
    "turma_atual": { "id": 1, "nome": "", "nivel": "" } | null
  }
]
```

### `POST /admin/alunos`
```json
// Request
{ "nome": "", "email": "", "username": "", "nivel": "básico" | null }

// Response 201
{
  "id": 1,
  "nome": "",
  "username": "",
  "email": "",
  "nivel": null,
  "senha_temporaria": "auto-gerada"  // exibir uma única vez ao admin
}
```

**Erros:** `409` email ou username já cadastrado.

### `PATCH /admin/alunos/{id}/acesso`
```json
// Request
{ "acesso_liberado": true | false }
// Response
{ "acesso_liberado": true | false }
```

### `PATCH /admin/alunos/{id}/nivel`
```json
// Request
{ "nivel": "string" }
// Response
{ "nivel": "string", "idioma_portal": "pt" | "en" }
```
> Nível controla idioma automaticamente: básico/básico_2/básico_3 → `pt`, demais → `en`.

### `PATCH /admin/alunos/{id}/cefr-level`
Define o nível CEFR do aluno (usado pra filtrar tarefas atribuídas por nível).
```json
// Request
{ "cefr_level": "A1" | "A2" | "B1" | "B2" | "C1" | "C2" | null }
// Response
{ "cefr_level": "B2" | null }
```
> Coexiste com `nivel` (que controla idioma_portal). Aluno sem `cefr_level` só enxerga tarefas atribuídas à sua turma.

### `PATCH /admin/alunos/{id}/turma`
```json
// Request
{ "turma_id": 1 }
// Response
{ "aluno_id": 1, "turma_id": 1 }
```

---

### `GET /admin/turmas`
```json
[
  {
    "id": 1, "nome": "", "nivel": "", "cor": "#3B82F6",
    "professor_id": null, "professor_nome": null,
    "ativo": true, "qtd_alunos": 0
  }
]
```

### `POST /admin/turmas`
```json
// Request
{ "nome": "", "nivel": "", "professor_id": null, "cor": "#3B82F6" }
// Response 201 — mesmo shape de TurmaListItem
```
> `cor` é hex 6 dígitos (#RRGGBB). Padrão: `#3B82F6`. Inválido → `422`.

### `PATCH /admin/turmas/{id}`
Atualiza qualquer campo da turma. Todos opcionais.
```json
// Request
{ "nome": null, "nivel": null, "cor": null, "professor_id": null, "ativo": null }
// Response — mesmo shape de TurmaListItem
```

### `GET /admin/turmas/{id}`
```json
{
  "id": 1, "nome": "", "nivel": "", "cor": "#3B82F6", "ativo": true,
  "professor_id": null, "professor_nome": null,
  "qtd_alunos": 0,
  "alunos": [
    { "id": 1, "nome": "", "username": "", "nivel": null, "acesso_liberado": true }
  ]
}
```

### `DELETE /admin/turmas/{id}/alunos/{aluno_id}` → `204 No Content`

### `PATCH /admin/turmas/{id}/professor`
```json
// Request
{ "professor_id": 1 }
// Response
{ "turma_id": 1, "professor_id": 1 }
```

---

### `GET /admin/professores`
```json
[{ "id": 1, "nome": "", "username": "", "email": "" }]
```

### `POST /admin/professores`
```json
// Request
{ "nome": "", "email": "", "username": "" }
// Response 201
{ "id": 1, "nome": "", "username": "", "email": "", "senha_temporaria": "auto-gerada" }
```
> Exibir `senha_temporaria` uma única vez ao admin — não armazenar no frontend.
> **Erros:** `409` email ou username já cadastrado.

---

### `GET /admin/calendario?mes=YYYY-MM`
Retorna todas as aulas de todas as turmas no mês. Apenas admin.
```json
[
  {
    "id": 1, "turma_id": 1, "turma_nome": "", "turma_cor": "#3B82F6",
    "professor_id": 1, "professor_nome": "",
    "titulo": "", "descricao": null,
    "data_hora": "datetime", "duracao_min": 60,
    "link_aula": null, "serie_id": null, "criado_em": "datetime"
  }
]
```

### `POST /admin/aulas`
Cria uma aula avulsa para qualquer turma/professor. Sem recorrência (use `/professores/aulas` para recorrência).
```json
// Request
{
  "turma_id": 1, "professor_id": 1,
  "titulo": "", "descricao": null,
  "data_hora": "datetime", "duracao_min": 60, "link_aula": null
}
// Response 201 — AulaAdminItem
```

### `PATCH /admin/aulas/{id}`
```json
// Request — todos opcionais
{ "turma_id": null, "professor_id": null, "titulo": null,
  "descricao": null, "data_hora": null, "duracao_min": null, "link_aula": null }
// Response — AulaAdminItem
```

### `DELETE /admin/aulas/{id}` → `204 No Content`

### `DELETE /admin/aulas/serie/{serie_id}` → `204 No Content`
Remove todas as aulas de uma série recorrente.

---

### `GET /admin/comunicados`
```json
[
  {
    "id": 1, "autor_id": 1, "titulo": "", "mensagem": "",
    "turma_id": null, "enviado_email": false, "criado_em": "datetime"
  }
]
```

### `POST /admin/comunicados`
```json
// Request
{ "titulo": "", "mensagem": "", "turma_id": null }
// Response 201 — mesmo shape de ComunicadoListItem
```

### `DELETE /admin/comunicados/{id}` → `204 No Content`

---

## Rotas Professores — `/professores`
Exigem role `professor` ou `admin`. Professor acessa apenas suas turmas; admin acessa tudo.

### `GET /professores/turmas`
Turmas atribuídas ao professor logado.
```json
[{ "id": 1, "nome": "", "nivel": "", "cor": "#3B82F6", "qtd_alunos": 0 }]
```

### `GET /professores/calendario?mes=YYYY-MM`
Aulas das turmas do professor no mês. Admin vê todas.
```json
[
  {
    "id": 1, "turma_id": 1, "turma_nome": "", "turma_cor": "#3B82F6",
    "professor_id": 1, "professor_nome": "",
    "titulo": "", "descricao": null,
    "data_hora": "datetime", "duracao_min": 60,
    "link_aula": null, "serie_id": null
  }
]
```
> Agrupar por `turma_cor` no calendário visual. Aulas da mesma série compartilham `serie_id`.

### `POST /professores/aulas`
Cria aula(s) para uma turma do professor. Suporta recorrência.
```json
// Request
{
  "turma_id": 1,
  "titulo": "Aula de Inglês",
  "descricao": null,
  "data_hora": "2024-08-05T10:00:00Z",
  "duracao_min": 60,
  "link_aula": null,
  "recorrencia": {
    "dias_semana": [0, 4],
    "ate": "2024-12-20"
  }
}
```
> `dias_semana`: 0=seg, 1=ter, 2=qua, 3=qui, 4=sex, 5=sáb, 6=dom
> `recorrencia: null` → cria 1 aula. Com recorrência → gera todas as ocorrências até `ate` (máx. 365 dias).

```json
// Response 201
{
  "criadas": 20,
  "serie_id": "uuid" | null,
  "aulas": [ /* lista de AulaCalendarioItem */ ]
}
```
**Erros:** `403` turma não pertence ao professor. `404` turma inativa ou inexistente. `400` nenhuma data gerada.

### `PATCH /professores/aulas/{id}`
Edita uma aula. Se `data_hora` mudar → cria comunicado automático para a turma.
```json
// Request — todos opcionais
{ "titulo": null, "descricao": null, "data_hora": null, "duracao_min": null, "link_aula": null }
// Response — AulaCalendarioItem
```
> **Auto-comunicado ao reagendar:** título `"Aula reagendada: {titulo}"`, mensagem com novo horário.

### `DELETE /professores/aulas/{id}` → `204 No Content`
> **Auto-comunicado ao cancelar:** título `"Aula cancelada: {titulo}"`, mensagem com horário original.

### `DELETE /professores/aulas/serie/{serie_id}` → `204 No Content`
> **Auto-comunicado:** um por turma afetada, série cancelada.

---

## Módulo Social — `/social`
Acessível por qualquer usuário autenticado (aluno, professor, admin).
Permissões são verificadas por endpoint.

### Chat Individual (DM)

#### `GET /social/conversas`
Lista todas as conversas DM do usuário logado.
```json
{
  "conversas": [
    {
      "usuario_id": 1,
      "nome": "",
      "foto_url": null,
      "nao_lidas": 2,
      "ultima_mensagem": "Oi professor!",
      "ultima_mensagem_em": "datetime"
    }
  ]
}
```

#### `GET /social/mensagens?usuario_id={id}`
Histórico de DMs com um usuário. Marca automaticamente as mensagens recebidas como lidas.
```json
[
  {
    "id": 1,
    "remetente_id": 1, "remetente_nome": "",
    "destinatario_id": 2,
    "turma_id": null,
    "conteudo": "",
    "lida": true,
    "criado_em": "datetime"
  }
]
```
> **Permissões:** aluno só pode conversar com professor da sua turma e admin. Professor com alunos das suas turmas e admin. Admin com qualquer um.
> **Erros:** `403` sem permissão.

#### `POST /social/mensagens`
Envia um DM.
```json
// Request
{ "destinatario_id": 2, "conteudo": "Olá!" }
// Response 201 — MensagemItem
```
**Erros:** `400` enviar para si mesmo. `403` sem permissão.

#### `POST /social/mensagens/{id}/lida` → `204 No Content`
Marca mensagem como lida (somente o destinatário pode fazer isso).

---

### Chat de Grupo (Turma)

#### `GET /social/turmas/{turma_id}/chat`
Chat de grupo da turma.
```json
{
  "turma_id": 1,
  "turma_nome": "",
  "turma_cor": "#3B82F6",
  "mensagens": [ /* lista de MensagemItem — turma_id preenchido, destinatario_id null */ ]
}
```
> **Permissões:** aluno da turma, professor da turma, admin.
> **Erros:** `403` sem permissão. `404` turma não existe.

#### `POST /social/turmas/{turma_id}/chat`
Envia mensagem no chat de grupo.
```json
// Request
{ "conteudo": "Pessoal, aula confirmada amanhã!" }
// Response 201 — MensagemItem
```

---

## Rotas /me — perfil do usuário logado (qualquer role)
Endpoints role-agnósticos para edição de perfil. Funcionam para `aluno`, `professor` e `admin`.
Coexistem com `/alunos/*` — o aluno pode usar qualquer um dos dois.

### `GET /me/check-username?username=foo`
```json
{ "disponivel": true | false }
```

### `PATCH /me/perfil`
Todos os campos opcionais. Atualiza apenas os enviados.
```json
// Request
{ "nome": null, "username": null, "email": null }
// Response — mesmo shape de /auth/me (UsuarioResponse)
```
**Erros:** `409` username ou email já em uso.

> Sem campo `aceita_email` (específico de aluno — use `/alunos/perfil` se precisar).

### `PATCH /me/senha` → `204 No Content`
```json
// Request
{ "senha_atual": "", "nova_senha": "", "confirmar_senha": "" }
```
**Erros:** `400` senha atual incorreta, nova igual à atual, ou senhas não coincidem. Mínimo 8 caracteres.
**Side effect:** invalida todos os refresh tokens do usuário (força re-login em outros dispositivos).

### `PATCH /me/foto`
```json
// Request
{ "foto_base64": "data:image/...;base64,..." }
// Response — mesmo shape de /auth/me (UsuarioResponse)
```
Mesmos limites e comportamento de `/alunos/foto` (Cloudinary, 5 MB máx, JPEG/PNG/WebP).

> A coluna `foto_url` foi migrada para a tabela `usuarios` — agora qualquer role tem foto.
> `/alunos/foto` continua existindo e escrevendo no mesmo lugar (compatibilidade total).

---

## Rotas Aluno — `/alunos`
Todos exigem token. Qualquer role pode acessar (o próprio usuário).

### `GET /alunos/me`
```json
{
  "id": 1, "nome": "", "username": "", "email": "",
  "foto_url": null, "aceita_email": true,
  "nivel": null, "idioma_portal": "pt", "acesso_liberado": true
}
```

### `GET /alunos/check-username?username=foo`
```json
{ "disponivel": true | false }
```

### `PATCH /alunos/perfil`
Todos os campos são opcionais. Atualiza apenas os enviados.
```json
// Request
{ "nome": null, "username": null, "email": null, "aceita_email": null }
// Response — mesmo shape de /alunos/me
```
**Erros:** `409` username ou email já em uso.

### `PATCH /alunos/senha` → `204 No Content`
```json
// Request
{ "senha_atual": "", "nova_senha": "", "confirmar_senha": "" }
```
**Erros:** `400` senha atual incorreta, nova igual à atual, ou senhas não coincidem. Mínimo 8 caracteres.

### `PATCH /alunos/foto`
```json
// Request
{ "foto_base64": "data:image/...;base64,..." }
// Response — mesmo shape de /alunos/me
```
**Formatos aceitos:** `image/jpeg`, `image/png`, `image/webp`. Máximo **5 MB**.

`foto_url` na response é sempre uma URL HTTPS do Cloudinary (nunca base64).
A imagem é recortada em 400×400 px com foco no rosto automaticamente.

**Erros:**
- `400` tipo de arquivo não permitido ou imagem acima de 5 MB
- `502` falha temporária no serviço de storage (retry seguro)

### `GET /alunos/progresso`
```json
{
  "entrada_no_curso": "datetime",
  "meses_no_curso": 0,
  "nivel_atual": null,
  "historico_niveis": [{ "nivel": "", "entrada_em": "datetime" }],
  "total_aulas_presentes": 0,
  "total_faltas": 0,
  "percentual_presenca": 0.0
}
```
> ⚠️ **STUB INCOMPLETO:** `total_aulas_presentes`, `total_faltas` e `percentual_presenca` sempre retornam 0. Não renderizar esses campos como dados reais. Será implementado na Fase 8.

### `GET /alunos/comunicados`
```json
{
  "total_nao_lidos": 0,
  "comunicados": [
    {
      "id": 1, "titulo": "", "mensagem": "",
      "turma_id": null, "turma_nome": null,
      "criado_em": "datetime", "lido": false
    }
  ]
}
```

### `POST /alunos/comunicados/{id}/lido` → `204 No Content`
**Erros:** `404` comunicado não existe, `403` comunicado é de turma que o aluno não pertence.

---

## Rotas Aulas — `/aulas`

### `GET /aulas?mes=YYYY-MM`
Retorna aulas da turma do aluno no mês informado.
```json
[
  {
    "id": 1, "titulo": "", "descricao": null,
    "data_hora": "datetime", "duracao_min": 60,
    "professor_nome": null,
    "link_aula": null,
    "presenca_confirmada": false
  }
]
```
> `link_aula` pode ser link do Google Meet, Zoom ou outro. Formato não padronizado ainda.

### `POST /aulas/{id}/confirmar` → `204 No Content`

---

## Rotas Aulas Extra — `/aulas-extra`

### `GET /aulas-extra`
```json
[
  {
    "id": 1, "data_sugerida": "date",
    "motivo": "", "status": "pendente" | "aprovada" | "recusada",
    "resposta_admin": null, "criado_em": "datetime"
  }
]
```

### `POST /aulas-extra`
```json
// Request
{ "data_sugerida": "YYYY-MM-DD", "motivo": "" }
// Response 201 — mesmo shape acima
```

---

## Rotas Tarefas — `/tarefas`
Exigem role `professor` ou `admin`.
**Mini-fatia 1A:** somente CRUD do professor — sem submissão de aluno, correção, ranking ou áudio ainda.

### Tipos suportados
| `tipo` | Categoria sugerida | Auto-correção |
|---|---|---|
| `fib`   | `gramatica` / `vocabulario` | ✅ Fill-in-the-blanks (case-insensitive + multiple answers via `\|`) |
| `mc`    | `gramatica` | ✅ Multiple choice (compara `selected_letter` vs `correct_letter`) |
| `match` | `vocabulario` | ✅ Matching (compara pares left↔right vs `correct_pairs`) |
| `reading` | `leitura` | ⚠️ Parcial — só TFNG + MC; short/heads manual |
| `essay`   | `escrita` | ❌ Manual |
| `notes`   | `escuta` | ✅ Parcial — lacunas com gabarito; texto-only no MVP (sem áudio) |
| `role`    | `fala` | ❌ Manual — texto-only no MVP |
| `tsent`   | `traducao` | ❌ Manual (tradução subjetiva) |

**Schemas de `conteudo` e `respostas`** discriminados por `tipo` via Pydantic Union — payload errado retorna `422`.

**Sanitização de gabaritos**: o backend remove campos sensíveis (`answer`, `correct_letter`, `correct_pairs`, `correct`, `target_hint`) ao retornar `conteudo` ao aluno em `GET /alunos/tarefas/{id}`. O professor vê o conteúdo completo em `GET /correcoes/submissoes/{id}`.

### `POST /tarefas`
Cria tarefa em status `draft`.

```json
// Request — exemplo FIB
{
  "categoria": "gramatica",
  "tipo": "fib",
  "titulo": "Conditionals — real & unreal worlds",
  "descricao": "12 sentences. Complete with the right tense.",
  "conteudo": {
    "tipo": "fib",
    "sentences": [
      { "id": 1, "text": "If I {{1}} (have) more time, I would travel.", "answer": "had" },
      { "id": 2, "text": "She {{1}} (be) tired if she sleeps late.", "answer": "is|will be" }
    ],
    "case_insensitive": true,
    "multiple_answers": true,
    "show_hint": false
  },
  "rubrica": null,
  "data_entrega": "2026-05-25T23:59:00Z",
  "pontos_disponiveis": 80,
  "cefr_levels": ["B2"],
  "turmas_alvo": [1, 3]
}
```

**Response 201:** `TarefaDetalhe` (mesmo shape do `GET /{id}`).

**Validações:**
- `tipo` deve estar nos suportados, e bater com `conteudo.tipo` (`422` se inconsistente).
- Pelo menos um de `cefr_levels` ou `turmas_alvo` deve ser não-vazio (`422`).
- `pontos_disponiveis` > 0.
- Turmas inexistentes → `400`.

### `GET /tarefas`
Lista com filtros opcionais via query string:
- `?status=draft|published|archived`
- `?categoria=gramatica|vocabulario|leitura|escrita|escuta|fala|traducao`
- `?cefr_level=A1|A2|B1|B2|C1|C2`
- `?turma_id=3`

```json
// Response — TarefaListItem[]
[
  {
    "id": 1,
    "categoria": "gramatica",
    "tipo": "fib",
    "titulo": "",
    "descricao": null,
    "pontos_disponiveis": 80,
    "status": "draft",
    "data_entrega": "datetime" | null,
    "cefr_levels": ["B2"],
    "turmas_alvo": [1, 3],
    "criado_em": "datetime",
    "publicado_em": null
  }
]
```

### `GET /tarefas/{id}`
```json
// Response — TarefaDetalhe
{
  "id": 1,
  "categoria": "gramatica",
  "tipo": "fib",
  "titulo": "",
  "descricao": null,
  "conteudo": { /* shape específico do tipo — ver POST */ },
  "rubrica": null | [{ "criterio": "", "pontos_max": 25 }],
  "pontos_disponiveis": 80,
  "status": "draft",
  "data_entrega": "datetime" | null,
  "cefr_levels": ["B2"],
  "turmas_alvo": [1, 3],
  "criado_por": 1,
  "criado_em": "datetime",
  "publicado_em": null,
  "arquivado_em": null
}
```
**Erros:** `404` se não encontrada.

### `PATCH /tarefas/{id}`
Edita tarefa. **Só permitido em status `draft`** — retorna `409` se publicada/arquivada.

```json
// Request — todos opcionais; campos omitidos não são alterados
{
  "titulo": null,
  "descricao": null,
  "conteudo": null,
  "rubrica": null,
  "data_entrega": null,
  "pontos_disponiveis": null,
  "cefr_levels": null,
  "turmas_alvo": null
}
// Response — TarefaDetalhe
```
> `cefr_levels` e `turmas_alvo` quando enviados **substituem** a lista atual (não fazem merge).

### `POST /tarefas/{id}/publicar` → `TarefaDetalhe`
Move `draft` → `published`. Carimba `publicado_em`. Exige pelo menos 1 alvo (`cefr_level` ou `turma_alvo`).

**Erros:** `409` se já publicada/arquivada, ou se sem alvo.

### `POST /tarefas/{id}/arquivar` → `TarefaDetalhe`
Move `published` → `archived`. Carimba `arquivado_em`. Tarefa sai da listagem ativa mas histórico permanece.

**Erros:** `409` se não estava `published`.

### `DELETE /tarefas/{id}` → `204 No Content`
**Só permitido em status `draft`.** Para tarefas publicadas, use `arquivar`. Retorna `409` caso contrário.

> ⚠️ **Por design:** tarefas com submissões de alunos nunca podem ser deletadas — o caminho é `arquivar` (que preserva todo o histórico). DELETE em draft é seguro porque draft não tem submissões.

---

## Rotas Tarefas do Aluno — `/alunos/tarefas`
Exigem role `aluno` (professor/admin recebem `403`).

**Filtragem:** aluno só vê tarefas com `status=published` que tenham match com **seu `cefr_level`** OU **sua turma**. Tarefas sem submissão dele aparecem como `submission_status="pending"`.

**Gabaritos:** o campo `conteudo` é **sanitizado** antes de retornar ao aluno (remove `answer` em FIB, `correct_index` em MC, etc.).

### `GET /alunos/tarefas`
Filtros opcionais:
- `?categoria=gramatica|vocabulario|leitura|escrita|escuta|fala|traducao`

```json
// Response — TarefaAlunoListItem[]
[
  {
    "id": 1,
    "categoria": "gramatica",
    "tipo": "fib",
    "titulo": "Conditionals",
    "descricao": null,
    "pontos_disponiveis": 80,
    "data_entrega": "datetime" | null,
    "publicado_em": "datetime",
    "submissao_status": "pending" | "submitted" | "reviewed"
  }
]
```

### `GET /alunos/tarefas/{id}`
```json
{
  "id": 1,
  "categoria": "gramatica",
  "tipo": "fib",
  "titulo": "",
  "descricao": null,
  "conteudo": {
    "tipo": "fib",
    "sentences": [
      { "id": 1, "text": "If I {{1}} (have) more time..." }
      /* answer removido — gabarito */
    ],
    "case_insensitive": true,
    "multiple_answers": false,
    "show_hint": false
  },
  "rubrica": null,
  "pontos_disponiveis": 80,
  "data_entrega": "datetime" | null,
  "publicado_em": "datetime",
  "submissao_status": "pending",
  "submissao": null | { /* MinhaSubmissaoResponse — preenchido se aluno já submeteu */ }
}
```

**Erros:** `404` se tarefa não existe ou aluno não tem permissão de ver.

### `PUT /alunos/tarefas/{id}/rascunho` — autosave
Upsert do rascunho (cria se não existe, atualiza se existe). Frontend deve chamar com debounce (3–5s).

```json
// Request
{
  "respostas": { /* estrutura parcial — flexível, validação rigorosa só no submit */ },
  "progresso": { "filled": 6, "total": 12 } | null
}
// Response 200 — RascunhoResponse
{
  "tarefa_id": 1,
  "respostas": { /* ... */ },
  "progresso": { "filled": 6, "total": 12 } | null,
  "atualizado_em": "datetime"
}
```

**Erros:** `404` tarefa não acessível. `409` se já submeteu (não pode salvar rascunho depois).

### `GET /alunos/tarefas/{id}/rascunho` → `RascunhoResponse`
**Erros:** `404` se não há rascunho.

### `POST /alunos/tarefas/{id}/submissoes`
Submete a tarefa. Auto-correção objetiva é calculada (FIB), mas **status fica `submitted`** aguardando revisão do professor.

```json
// Request — exemplo FIB
{
  "respostas": {
    "tipo": "fib",
    "answers": [
      { "sentence_id": 1, "answer": "had" },
      { "sentence_id": 2, "answer": "will be" }
    ]
  },
  "tempo_gasto_seg": 480
}
```

```json
// Response 201 — MinhaSubmissaoResponse
{
  "id": 1,
  "tarefa_id": 1,
  "respostas": { /* o que foi enviado */ },
  "status": "submitted",
  "submetido_em": "datetime",
  "tempo_gasto_seg": 480,
  "atrasada": false,
  "eh_repeticao": false,
  "correcao": null
}
```

> Apaga o rascunho da tarefa automaticamente após submeter.

**Erros:**
- `404` tarefa não acessível
- `409` já submetida (uma submissão por aluno por tarefa — exceto repetições, ainda não expostas)
- `422` `respostas.tipo` não bate com `tarefa.tipo`

### `GET /alunos/tarefas/{id}/submissao` → `MinhaSubmissaoResponse`
**Erros:** `404` se aluno ainda não submeteu.

Quando `status=reviewed`, `correcao` vem populada:
```json
"correcao": {
  "score": 85,
  "grade": "B+",
  "rubrica_scores": null,
  "feedback": "Strong work — watch verb agreement in #4",
  "inline_notes": null,
  "corrigido_em": "datetime",
  "pontos_ganhos": 68
}
```

---

## Rotas Correções — `/correcoes`
Exigem role `professor` ou `admin`.
**Permissões:** admin corrige qualquer tarefa; professor só corrige submissões de tarefas que **ele criou** (`tarefa.criado_por == user.id`).

### `GET /correcoes/pendentes`
Submissões com `status=submitted` aguardando correção.
Filtros opcionais: `?tarefa_id=N`

```json
// Response — SubmissaoPendenteItem[]
[
  {
    "id": 1,
    "tarefa_id": 1,
    "tarefa_titulo": "Conditionals",
    "tarefa_tipo": "fib",
    "aluno_id": 3,
    "aluno_nome": "Lucas Ribeiro",
    "submetido_em": "datetime",
    "atrasada": false,
    "auto_score": 75
  }
]
```

> `auto_score` é a sugestão calculada automaticamente (FIB/MC) — referência para o professor.

### `GET /correcoes/submissoes/{id}` → `SubmissaoCompletaProfessor`
Detalhe completo da submissão para corrigir. **`tarefa_conteudo` vem com gabaritos** (não sanitizado — professor precisa ver).

```json
{
  "id": 1,
  "tarefa_id": 1,
  "tarefa_titulo": "Conditionals",
  "tarefa_tipo": "fib",
  "tarefa_conteudo": { /* com gabaritos */ },
  "tarefa_rubrica": null | [{ "criterio": "", "pontos_max": 25 }],
  "tarefa_pontos_disponiveis": 80,
  "aluno_id": 3,
  "aluno_nome": "Lucas Ribeiro",
  "respostas": { /* respostas do aluno */ },
  "status": "submitted" | "reviewed",
  "submetido_em": "datetime",
  "tempo_gasto_seg": 480,
  "atrasada": false,
  "eh_repeticao": false,
  "auto_score": 75,
  "correcao": null | { /* CorrecaoResponse — preenchido se já corrigida */ }
}
```

**Erros:** `404` submissão não existe. `403` sem permissão (não criou a tarefa).

### `POST /correcoes/submissoes/{id}`
Cria correção. **Transação atômica** — todos os passos ocorrem antes do mesmo commit:

1. INSERT em `correcoes`
2. UPDATE `submissoes.status` → `reviewed`
3. Calcula `pontos = round(pontos_disponiveis × score / 100)` (se `eh_repeticao=true`, vale 50%)
4. INSERT em `ganhos_pontos`
5. UPDATE `perfis_alunos.xp_total` += pontos

```json
// Request
{
  "score": 85,
  "grade": "B+",
  "rubrica_scores": null | [{ "criterio_idx": 0, "awarded": 22 }],
  "feedback": "Strong work — watch verb agreement",
  "inline_notes": null | [{ "line_num": 4, "text": "...", "correction": "..." }]
}
```

**Validações:**
- `score` entre 0 e 100 (CHECK no banco)
- `grade` em `{A+, A, A-, B+, B, B-, C+, C, C-, D, F}` ou null (CHECK no banco)
- Pydantic valida `grade` antes de chegar no banco

```json
// Response 201 — CorrecaoResponse
{
  "id": 1,
  "submissao_id": 1,
  "score": 85,
  "grade": "B+",
  "auto_score": 75,
  "rubrica_scores": null,
  "feedback": "Strong work — watch verb agreement",
  "inline_notes": null,
  "corrigido_em": "datetime",
  "pontos_ganhos": 68
}
```

**Erros:**
- `404` submissão não existe
- `403` sem permissão
- `409` submissão já corrigida
- `422` grade inválida ou score fora de 0-100

---

## Valores Válidos

### Níveis (`nivel`)
`básico` | `básico_2` | `básico_3` | `intermediário` | `intermediário_2` | `avançado`
> Lista não exaustiva — pode crescer. Sempre tratar `null` como possível.

### Níveis CEFR (`cefr_level`)
`A1` | `A2` | `B1` | `B2` | `C1` | `C2`
> Usado em `/tarefas` (atribuição) e em `perfis_alunos.cefr_level` (campo do aluno). Coexiste com `nivel` — não substitui.

### Categorias de Tarefa (`categoria`)
`gramatica` | `vocabulario` | `leitura` | `escrita` | `escuta` | `fala` | `traducao`

### Status de Tarefa (`status` em `/tarefas`)
`draft` | `published` | `archived`

### Roles (`role`)
`aluno` | `professor` | `admin`

### Status de Aula Extra (`status`)
`pendente` | `aprovada` | `recusada`

---

## Comportamentos Importantes para o Frontend

1. **Acesso bloqueado (403 no login):** exibir mensagem orientando contato via WhatsApp, não "credenciais inválidas"
2. **`foto_url`** é sempre `null` ou uma URL HTTPS — nunca base64
3. **`comunicados_nao_lidos` no `/auth/me`** é o badge do sino — atualizar após marcar como lido
4. **`idioma_portal`** deve controlar qual idioma o portal renderiza — não deixar fixo no código
5. **Token refresh:** ao receber 401 em qualquer request protegida, tentar refresh antes de redirecionar ao login
6. **`cor` de turma** é sempre hex `#RRGGBB` maiúsculo — usar diretamente como CSS color
7. **Calendário:** agrupar aulas por `turma_cor`. Aulas com mesmo `serie_id` pertencem à mesma série recorrente.
8. **Chat — polling:** não há WebSocket. Fazer refetch automático a cada 5–10s (React Query `refetchInterval`).
9. **Auto-comunicados:** cancelamento/reagendamento de aulas geram comunicados automaticamente — não duplicar notificação no frontend.
10. **`senha_temporaria`** (professores e alunos): exibir uma única vez em modal, nunca armazenar no state persistente.
11. **DM vs. Grupo:** `destinatario_id != null && turma_id == null` = DM. `turma_id != null && destinatario_id == null` = grupo.
