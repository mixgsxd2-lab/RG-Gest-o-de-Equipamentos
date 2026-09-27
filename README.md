# RG Manutenção — Hospital Rio Grande

Software de **Gestão de Manutenção Geral** do Hospital Rio Grande (RG): plataforma web responsiva
(desktop e celular) que controla todo o ciclo da manutenção:

**abertura do chamado → recebimento → execução → materiais/custos → fechamento → histórico → indicadores**

> ⚠️ **DEMONSTRAÇÃO** — a instalação padrão carrega somente **dados fictícios** (nenhuma informação real
> de pacientes, colaboradores ou fornecedores), sinalizados de forma discreta no menu lateral e na tela
> de login. Com `DEMO_MODE=0` esses indicadores e o acesso rápido desaparecem.

## Como executar

Requisitos: Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Acesse **http://localhost:5000**. Na primeira execução o banco SQLite é criado em `instance/` e
populado com os dados de demonstração.

Para recriar o banco do zero: `flask --app run init-db --reset` (ou apague a pasta `instance/`).

### Acessos de demonstração (senha `123456`)

| Usuário     | Perfil                |
|-------------|-----------------------|
| `admin`     | Administrador         |
| `gestor`    | Gestor de Manutenção  |
| `operador`  | Operador/Técnico      |
| `usuario`   | Solicitante           |
| `estoque`   | Estoque               |
| `diretoria` | Diretoria             |

Há também técnicos (`tecnico.eletrica`, `tecnico.clima`, `tecnico.gases`, …) e solicitantes de vários
setores (`ps.enfermagem`, `cc.coordenacao`, `hemodialise`, …), todos com a mesma senha.

## Módulos

| Módulo | O que faz |
|---|---|
| **Dashboard** | Chamados abertos/em andamento/finalizados, SLA, tempo médio de atendimento, produtividade, custos, status dos ativos, preventivas, estoque, desempenho de fornecedores; gráficos por setor, período e tipo |
| **Chamados** | Abertura para um setor de manutenção com solicitante, responsável (quem recebeu) e operador (quem aceitou/executou), tipo, prioridade, criticidade, local, ativo, descrição, fotos/anexos, status e SLA |
| **Execução e fechamento** | Início/término, apontamento de horas, diagnóstico, o que foi feito, causa da falha, peças do estoque (baixa automática), custo de terceiros, fotos, observações, satisfação e histórico completo de todas as ações |
| **Inventário / Ativos** | Patrimônio, categoria, setor/local, fabricante/modelo, vida útil, depreciação linear, custos e histórico de manutenção |
| **Preventivas** | Calendário mensal, planos periódicos (preventiva, preditiva, inspeção, calibração), situação (atrasada/próxima/programada) e geração de OS |
| **Monitoramento / IoT** | Sensores de energia, água, gases medicinais, temperatura e vibração; leituras, faixas e alertas; ranking de risco preditivo |
| **Equipes e técnicos** | Especialidades, técnicos próprios e terceirizados, distribuição de demandas e produtividade |
| **Fornecedores e contratos** | Cadastro, contratos com SLA e vigência, índice de desempenho de terceiros |
| **Estoque** | Peças e produtos, entradas (custo médio), saídas, ajustes, estoque mínimo e consumo por chamado |
| **Custos** | Materiais, mão de obra, terceiros, contratos e investimentos (livro único de custos) |
| **Indicadores e BI** | Pareto de falhas, MTBF/MTTR, depreciação, apoio à decisão e exportação CSV/JSON |
| **Usuários e acessos** | Perfis, matriz de permissões e integrações de identidade |

Fluxo do chamado: **Aberto → Recebido → Aceito → Em execução → Aguardando material/terceiro → Finalizado → Encerrado**
(com cancelamento e reabertura). SLA de solução: Urgente 4 h, Alta 8 h, Média 24 h, Baixa 72 h; Emergencial 2 h.

## Arquitetura

```
run.py                   inicia o servidor (cria e popula o banco de demonstração)
app/
  __init__.py            fábrica da aplicação Flask + comando `init-db`
  config.py              configuração via variáveis de ambiente
  models.py              modelo de dados (SQLAlchemy)
  constants.py           domínios: perfis, tipos, prioridades, status…
  auth.py                sessão, perfis e matriz de permissões (RBAC)
  auth_providers.py      provedores: local, Active Directory, Microsoft 365, Google Workspace
  services/              regras de negócio (fluxo do chamado, indicadores, alertas, preditiva)
  api/                   API REST JSON (/api/...)
  seed.py                dados fictícios de demonstração
  templates/index.html   página única (SPA)
  static/                CSS, JavaScript (módulos ES) e Chart.js local
tests/                   testes automatizados da API (pytest)
```

- **Backend:** Python + Flask + Flask-SQLAlchemy. Toda a lógica e os dados ficam no servidor (nada de
  `localStorage` como banco — ele guarda apenas a preferência de tema).
- **Frontend:** HTML, CSS e JavaScript puro, sem etapa de build; layout responsivo (web e celular).
- **Identidade visual:** baseada na marca do Hospital Rio Grande — azul-celeste `#92BFE9` com navy
  institucional, logotipos oficiais em `app/static/img/brand/` (aplicados como máscara, assumindo a cor
  de cada tema), títulos em sans estendida (Unbounded), rótulos em serifa espaçada como em
  "H O S P I T A L" (Cormorant Garamond) e textos em Manrope — fontes OFL hospedadas localmente em
  `app/static/fonts/`. **Modo claro e escuro** com alternador no topo e na tela de login (segue o
  sistema operacional por padrão).
- **API REST** documentada pelos próprios módulos em `app/api/` — a mesma API atende a interface web,
  futuros aplicativos móveis e integrações.

## Preparado para expansão

| Tema | Como |
|---|---|
| Banco de produção | `DATABASE_URL=postgresql+psycopg://usuario:senha@host/rg_manutencao` (ou SQL Server) |
| Active Directory / Microsoft 365 / Google Workspace | `app/auth_providers.py` (usuários têm `auth_provider` e `external_id`; mapeamento de grupos → perfis). Ative com `AD_ENABLED`, `M365_ENABLED`, `GOOGLE_ENABLED` |
| IoT (energia, água, gases) | `POST /api/iot/readings` com cabeçalho `X-API-Key` (`IOT_API_KEY`) |
| BI / Big Data | `GET /api/intelligence/export/<conjunto>.csv` ou `.json` (chamados, ativos, custos, movimentos_estoque, apontamentos, ml_features) |
| Machine Learning | `app/services/predictive.py`: variáveis por ativo e modelo baseline substituível por um modelo treinado |

Variáveis úteis: `SECRET_KEY` (obrigatório trocar em produção), `DEMO_MODE=0` (desliga dados e aviso de
demonstração), `UPLOAD_FOLDER`, `PORT`, `HOST`.

## Testes

```bash
python -m pytest -q
```

Os testes cobrem login dos perfis, dashboard, visibilidade por perfil, o fluxo completo do chamado
(com anexos, materiais, horas, espera, finalização, custos e histórico), estoque, preventivas,
inteligência/exportação, ingestão IoT e administração de usuários.

---
Chart.js (MIT) e as fontes (SIL OFL) estão incluídos no projeto para funcionar sem internet.
