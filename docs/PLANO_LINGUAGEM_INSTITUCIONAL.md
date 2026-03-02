# Plano de Consolidação de Linguagem Institucional

**Hedge Control Platform — Previse Capital**

| Metadado        | Valor                                       |
| --------------- | ------------------------------------------- |
| Versão          | 1.0                                         |
| Data            | 2025-07-16                                  |
| Escopo          | Frontend UI5 — webapp/                      |
| Artefatos       | 21 controllers, 20 views, 4 arquivos i18n   |
| Total violações | **134 instâncias** em 3 categorias          |
| Autoridade      | System Constitution (systemconstitucion.md) |

---

## 1. Diagnóstico

### 1.1 Resumo Executivo

O frontend do Hedge Control Platform apresenta **134 violações de linguagem** distribuídas em três categorias sistêmicas. O sistema, que se define constitucionalmente como "institutional-grade", expõe ao usuário final verbos HTTP, caminhos de API, identificadores UUID, referências internas de blocker, e comentários de arquitetura que pertencem exclusivamente ao domínio de desenvolvimento.

Este diagnóstico revela que a camada de apresentação **não reflete o nível institucional declarado na constituição do sistema**.

### 1.2 Distribuição de Violações

| Categoria                             | Arquivos afetados | Instâncias |
| ------------------------------------- | ----------------- | ---------- |
| A — Strings hardcoded em controllers  | 6 / 21            | 34         |
| B — Strings hardcoded em views XML    | 7 / 20            | 37         |
| C — Chaves i18n com linguagem técnica | 1 arquivo (×4)    | 63 chaves  |
| **Total**                             | —                 | **134**    |

### 1.3 Causa-Raiz Sistêmica

**`BaseController._formatError()`** é a causa-raiz de maior impacto. Este método é herdado por **todos os 21 controllers** e produz mensagens de erro no formato:

```
HTTP 422: Unprocessable Entity
```

Segue o código atual (linhas 76–87):

```javascript
_formatError: function (oError) {
    if (!oError) {
        return "Unknown error";         // ← hardcoded, inglês, técnico
    }
    var sMsg = oError.message || "Request failed";  // ← hardcoded
    if (oError.status) {
        sMsg = "HTTP " + oError.status + ": " + sMsg;  // ← expõe status code
    }
    if (oError.details && typeof oError.details === "object" && oError.details.detail) {
        sMsg += "\n" + oError.details.detail;  // ← expõe detalhe técnico do backend
    }
    return sMsg;
}
```

O método `submitData()` (linha 127) também contém `"Operation completed successfully"` como fallback hardcoded.

**Impacto**: Qualquer erro em qualquer tela do sistema exibe linguagem técnica HTTP ao usuário.

### 1.4 Piores Ofensores por Controller

| Controller                 | Instâncias | Tipo dominante               |
| -------------------------- | ---------- | ---------------------------- |
| Scenario.controller.js     | 16         | Labels e botões hardcoded    |
| BaseController.js          | 4          | Mensagens de erro sistêmicas |
| Mtm.controller.js          | 4          | Validações hardcoded         |
| RfqDetail.controller.js    | 4          | Placeholders e erro          |
| MarketData.controller.js   | 3          | Mensagens de sucesso/erro    |
| LinkagesList.controller.js | 3          | Placeholders                 |

### 1.5 Piores Ofensores por View XML

| View                    | Instâncias | Tipo dominante                   |
| ----------------------- | ---------- | -------------------------------- |
| Mtm.view.xml            | 8          | Select items + placeholders UUID |
| RfqCreate.view.xml      | 7          | Select items + placeholders      |
| Pnl.view.xml            | 6          | Placeholders UUID + datas        |
| Cashflow.view.xml       | 5          | Placeholders UUID + datas        |
| OrderCreate.view.xml    | 5          | Select items + placeholders      |
| MarketData.view.xml     | 4          | Placeholders + exemplos          |
| ContractCreate.view.xml | 2          | Placeholders                     |

### 1.6 Chaves i18n com Linguagem Técnica (63 chaves)

**Subcategoria C1 — Verbos HTTP + Caminhos de API (30 chaves)**

Chaves que exibem `GET /path` ou `POST /path` como texto visível ao usuário:

| Chave                          | Valor atual                                                    |
| ------------------------------ | -------------------------------------------------------------- |
| `ordersPostSales`              | `POST /orders/sales`                                           |
| `ordersPostPurchase`           | `POST /orders/purchase`                                        |
| `ordersGetOrder`               | `GET /orders/{order_id}`                                       |
| `ordersGetMtm`                 | `GET /mtm/orders/{order_id}`                                   |
| `rfqPostCreate`                | `POST /rfqs`                                                   |
| `rfqGetDetail`                 | `GET /rfqs/{rfq_id}`                                           |
| `rfqPostQuote`                 | `POST /rfqs/{rfq_id}/quotes`                                   |
| `rfqGetRanking`                | `GET /rfqs/{rfq_id}/ranking`                                   |
| `rfqGetTradeRanking`           | `GET /rfqs/{rfq_id}/trade-ranking`                             |
| `rfqPostAward`                 | `POST /rfqs/{rfq_id}/actions/award`                            |
| `rfqPostRefresh`               | `POST /rfqs/{rfq_id}/actions/refresh`                          |
| `rfqPostReject`                | `POST /rfqs/{rfq_id}/actions/reject`                           |
| `contractsPostCreate`          | `POST /contracts/hedge`                                        |
| `contractsGetContract`         | `GET /contracts/hedge/{contract_id}`                           |
| `contractsGetMtm`              | `GET /mtm/hedge-contracts/{contract_id}`                       |
| `contractsLinkagePost`         | `POST /linkages`                                               |
| `contractsGetLinkage`          | `GET /linkages/{linkage_id}`                                   |
| `cashflowGetAnalytic`          | `GET /cashflow/analytic`                                       |
| `cashflowGetBaseline`          | `GET /cashflow/baseline/snapshots`                             |
| `cashflowPostBaseline`         | `POST /cashflow/baseline/snapshots`                            |
| `cashflowPostSettle`           | `POST /cashflow/contracts/{contract_id}/settle`                |
| `cashflowGetLedger`            | `GET /cashflow/ledger`                                         |
| `cashflowGetLedgerForContract` | `GET /cashflow/ledger/hedge-contracts/{contract_id}`           |
| `pnlGetPl`                     | `GET /pl/{entity_type}/{entity_id}`                            |
| `pnlGetSnapshot`               | `GET /pl/snapshots`                                            |
| `pnlPostSnapshot`              | `POST /pl/snapshots`                                           |
| `scenarioPostTitle`            | `POST /scenario/what-if/run (in-memory; no persistence)`       |
| `mtmGetSnapshot`               | `GET /mtm/snapshots`                                           |
| `mtmGetContractMtm`            | `GET /mtm/hedge-contracts/{contract_id}`                       |
| `mtmGetOrderMtm`               | `GET /mtm/orders/{order_id}`                                   |
| `marketDataPostTitle`          | `POST /market-data/westmetall/aluminum/cash-settlement/ingest` |

**Subcategoria C2 — Referências UUID (12 chaves)**

Chaves que expõem nomes de parâmetro com anotação `(uuid)`:

| Chave                      | Valor atual              |
| -------------------------- | ------------------------ |
| `ordersOrderId`            | `order_id (uuid)`        |
| `rfqRfqId`                 | `rfq_id (uuid)`          |
| `contractsContractId`      | `contract_id (uuid)`     |
| `contractsLinkageId`       | `linkage_id (uuid)`      |
| `cashflowSettleContractId` | `contract_id (uuid)`     |
| `cashflowSourceEventId`    | `source_event_id (uuid)` |
| `cashflowLedgerContractId` | `contract_id (uuid)`     |
| `pnlEntityId`              | `entity_id (uuid)`       |
| `mtmObjectId`              | `object_id (uuid)`       |
| `mtmContractId`            | `contract_id (uuid)`     |
| `mtmOrderId`               | `order_id (uuid)`        |
| `optionalUuid`             | `Optional UUID`          |

**Subcategoria C3 — Parâmetros técnicos expostos (11 chaves)**

| Chave                     | Valor atual                       |
| ------------------------- | --------------------------------- |
| `cashflowAsOfDate`        | `as_of_date (YYYY-MM-DD)`         |
| `contractsAsOfDate`       | `as_of_date (YYYY-MM-DD) for MTM` |
| `ordersAsOfDate`          | `as_of_date (YYYY-MM-DD) for MTM` |
| `mtmAsOfDate`             | `as_of_date (YYYY-MM-DD)`         |
| `pnlPeriodStart`          | `period_start (YYYY-MM-DD)`       |
| `pnlPeriodEnd`            | `period_end (YYYY-MM-DD)`         |
| `cashflowLedgerStart`     | `start (optional, YYYY-MM-DD)`    |
| `cashflowLedgerEnd`       | `end (optional, YYYY-MM-DD)`      |
| `cashflowSourceEventType` | `source_event_type (optional)`    |
| `pnlEntityType`           | `entity_type`                     |
| `mtmObjectType`           | `object_type`                     |

**Subcategoria C4 — Jargão interno / Notas de implementação (10 chaves)**

| Chave                   | Valor atual                                                                                | Problema                    |
| ----------------------- | ------------------------------------------------------------------------------------------ | --------------------------- |
| `responseHeader`        | `Response (as-is)`                                                                         | Qualificador técnico        |
| `errorHeader`           | `Error (deterministic)`                                                                    | Qualificador técnico        |
| `formRequestJson`       | `Request JSON`                                                                             | Nome de formato de dados    |
| `headerBadge`           | `Admin read-only (no auth configured)`                                                     | Nota de implementação       |
| `homeCardOverviewText`  | `This frontend is read-only and reflects backend authority without client-side inference.` | Arquitetura interna         |
| `homeCardBackendTitle`  | `Backend Contract`                                                                         | Conceito de desenvolvimento |
| `homeCardBackendText`   | `OpenAPI-driven. No endpoints are invented.`                                               | Nota de implementação       |
| `homeCardWorklistsText` | `Blocked by Backend B1 (worklist endpoints missing).`                                      | Blocker interno             |
| `homeCardRfqText`       | `Blocked by Backend B2 (send/evidence endpoint missing).`                                  | Blocker interno             |
| `homeCardUiText`        | `SAP Horizon theming via theming-base-content.`                                            | Detalhe de implementação    |

---

## 2. Product Voice

### 2.1 Fundamento Constitucional

A System Constitution define explicitamente:

> _"This system exists to measure, manage, hedge, value and audit commodity exposure (LME Aluminium) in a corporative, institutional-grade context."_

E estabelece as prioridades:

> _"Correctness, determinism and auditability have priority over UX, speed of delivery or convenience."_

A constituição também define a fronteira do frontend:

> _"Frontend is a presenter. Frontend renders only. Frontend does not infer or compute economics."_

### 2.2 Definição da Voz Institucional

A voz do Hedge Control Platform segue três pilares derivados da constituição:

| Pilar             | Definição                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------- |
| **Precisão**      | Todo texto descreve _exatamente_ o que o sistema faz, sem ambiguidade nem inferência.    |
| **Institucional** | A linguagem é própria de um sistema financeiro corporativo, não de um protótipo técnico. |
| **Auditável**     | Nenhum texto diz "error occurred" — todo texto é específico, rastreável, verificável.    |

### 2.3 Anti-Padrões (o que a Voz NÃO é)

| Anti-padrão                      | Exemplo atual no sistema                              |
| -------------------------------- | ----------------------------------------------------- |
| **Linguagem de API**             | `POST /orders/sales` como título de formulário        |
| **Identificadores de backend**   | `contract_id (uuid)` como placeholder                 |
| **Comentários de implementação** | `Blocked by Backend B1 (worklist endpoints missing).` |
| **Jargão de arquitetura**        | `OpenAPI-driven. No endpoints are invented.`          |
| **Status codes HTTP expostos**   | `HTTP 422: Unprocessable Entity`                      |
| **Linguagem casual/genérica**    | `Operation completed successfully`, `Unknown error`   |

### 2.4 Exemplos de Voz Correta

| Contexto             | ❌ Errado (atual)                                         | ✅ Correto (institucional)                                     |
| -------------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| Título de formulário | `POST /orders/sales`                                      | `New Sales Order`                                              |
| Placeholder de ID    | `contract_id (uuid)`                                      | `Contract Identifier`                                          |
| Mensagem de erro     | `HTTP 422: Unprocessable Entity`                          | `The order could not be processed. Verify quantity and dates.` |
| Mensagem de sucesso  | `Operation completed successfully`                        | `Sales order created successfully.`                            |
| Card informativo     | `OpenAPI-driven. No endpoints are invented.`              | `All operations are contract-governed and auditable.`          |
| Status do sistema    | `Blocked by Backend B2 (send/evidence endpoint missing).` | `Evidence submission — pending activation.`                    |
| Data label           | `as_of_date (YYYY-MM-DD)`                                 | `Reference Date`                                               |
| Cenário label        | `POST /scenario/what-if/run (in-memory; no persistence)`  | `Run What-If Scenario`                                         |

---

## 3. Modelo de Linguagem

### 3.1 Regras Gerais

| Regra   | Descrição                                                                                                                    |
| ------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **R1**  | Nenhum texto visível ao usuário pode conter verbos HTTP (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`).                           |
| **R2**  | Nenhum texto visível pode conter caminhos de API (`/orders`, `/rfqs/{id}`, etc.).                                            |
| **R3**  | Nenhum texto visível pode conter `(uuid)`, `UUID`, ou nomes de parâmetro snake_case (`contract_id`, `as_of_date`).           |
| **R4**  | Nenhum texto visível pode conter referências de blocker internos (`B1`, `B2`, `Backend missing`).                            |
| **R5**  | Códigos de status HTTP (`404`, `422`, `500`) não são expostos ao usuário final.                                              |
| **R6**  | Campos de data usam labels descritivos (`Reference Date`), não nomes de parâmetro (`as_of_date`).                            |
| **R7**  | Mensagens de erro descrevem o impacto funcional, não a causa técnica.                                                        |
| **R8**  | Mensagens de sucesso descrevem a ação concluída com especificidade (`Order created`), não genéricas (`Operation completed`). |
| **R9**  | Toda string visível ao usuário deve estar em i18n — nenhum hardcoded em controller ou view.                                  |
| **R10** | Placeholders usam exemplos no formato do domínio de negócios, não formatos técnicos.                                         |

### 3.2 Tabela Before → After (amostras representativas)

#### 3.2.1 Chaves i18n — HTTP Paths (C1)

| Chave i18n                     | ❌ Before                                                      | ✅ After (EN)                  | ✅ After (PT-BR)                 |
| ------------------------------ | -------------------------------------------------------------- | ------------------------------ | -------------------------------- |
| `ordersPostSales`              | `POST /orders/sales`                                           | `Create Sales Order`           | `Criar Ordem de Venda`           |
| `ordersPostPurchase`           | `POST /orders/purchase`                                        | `Create Purchase Order`        | `Criar Ordem de Compra`          |
| `ordersGetOrder`               | `GET /orders/{order_id}`                                       | `Lookup Order`                 | `Consultar Ordem`                |
| `ordersGetMtm`                 | `GET /mtm/orders/{order_id}`                                   | `Order Mark-to-Market`         | `Marcação a Mercado da Ordem`    |
| `rfqPostCreate`                | `POST /rfqs`                                                   | `Submit New RFQ`               | `Submeter Nova RFQ`              |
| `rfqGetDetail`                 | `GET /rfqs/{rfq_id}`                                           | `RFQ Details`                  | `Detalhes da RFQ`                |
| `rfqPostQuote`                 | `POST /rfqs/{rfq_id}/quotes`                                   | `Submit Quote`                 | `Submeter Cotação`               |
| `rfqGetRanking`                | `GET /rfqs/{rfq_id}/ranking`                                   | `Quote Ranking`                | `Classificação de Cotações`      |
| `rfqPostAward`                 | `POST /rfqs/{rfq_id}/actions/award`                            | `Award RFQ`                    | `Adjudicar RFQ`                  |
| `rfqPostRefresh`               | `POST /rfqs/{rfq_id}/actions/refresh`                          | `Refresh RFQ`                  | `Atualizar RFQ`                  |
| `rfqPostReject`                | `POST /rfqs/{rfq_id}/actions/reject`                           | `Reject RFQ`                   | `Rejeitar RFQ`                   |
| `contractsPostCreate`          | `POST /contracts/hedge`                                        | `Create Hedge Contract`        | `Criar Contrato de Hedge`        |
| `contractsGetContract`         | `GET /contracts/hedge/{contract_id}`                           | `Contract Details`             | `Detalhes do Contrato`           |
| `contractsGetMtm`              | `GET /mtm/hedge-contracts/{contract_id}`                       | `Contract Mark-to-Market`      | `Marcação a Mercado do Contrato` |
| `contractsLinkagePost`         | `POST /linkages`                                               | `Create Linkage`               | `Criar Vínculo`                  |
| `contractsGetLinkage`          | `GET /linkages/{linkage_id}`                                   | `Linkage Details`              | `Detalhes do Vínculo`            |
| `cashflowGetAnalytic`          | `GET /cashflow/analytic`                                       | `Analytic Cashflow`            | `Fluxo de Caixa Analítico`       |
| `cashflowGetBaseline`          | `GET /cashflow/baseline/snapshots`                             | `Baseline Snapshots`           | `Snapshots de Baseline`          |
| `cashflowPostBaseline`         | `POST /cashflow/baseline/snapshots`                            | `Create Baseline Snapshot`     | `Criar Snapshot de Baseline`     |
| `cashflowPostSettle`           | `POST /cashflow/contracts/{contract_id}/settle`                | `Settle Contract`              | `Liquidar Contrato`              |
| `cashflowGetLedger`            | `GET /cashflow/ledger`                                         | `Cashflow Ledger`              | `Razão de Fluxo de Caixa`        |
| `cashflowGetLedgerForContract` | `GET /cashflow/ledger/hedge-contracts/{contract_id}`           | `Contract Ledger Entries`      | `Lançamentos do Contrato`        |
| `pnlGetPl`                     | `GET /pl/{entity_type}/{entity_id}`                            | `P&L Report`                   | `Relatório de P&L`               |
| `pnlGetSnapshot`               | `GET /pl/snapshots`                                            | `P&L Snapshots`                | `Snapshots de P&L`               |
| `pnlPostSnapshot`              | `POST /pl/snapshots`                                           | `Create P&L Snapshot`          | `Criar Snapshot de P&L`          |
| `scenarioPostTitle`            | `POST /scenario/what-if/run (in-memory; no persistence)`       | `Run What-If Scenario`         | `Executar Cenário What-If`       |
| `mtmGetSnapshot`               | `GET /mtm/snapshots`                                           | `MTM Snapshots`                | `Snapshots de MTM`               |
| `mtmGetContractMtm`            | `GET /mtm/hedge-contracts/{contract_id}`                       | `Contract MTM`                 | `MTM do Contrato`                |
| `mtmGetOrderMtm`               | `GET /mtm/orders/{order_id}`                                   | `Order MTM`                    | `MTM da Ordem`                   |
| `marketDataPostTitle`          | `POST /market-data/westmetall/aluminum/cash-settlement/ingest` | `Ingest Cash Settlement Price` | `Importar Preço de Liquidação`   |

#### 3.2.2 Chaves i18n — UUID References (C2)

| Chave i18n                 | ❌ Before                | ✅ After (EN)     | ✅ After (PT-BR)         |
| -------------------------- | ------------------------ | ----------------- | ------------------------ |
| `ordersOrderId`            | `order_id (uuid)`        | `Order ID`        | `ID da Ordem`            |
| `rfqRfqId`                 | `rfq_id (uuid)`          | `RFQ ID`          | `ID da RFQ`              |
| `contractsContractId`      | `contract_id (uuid)`     | `Contract ID`     | `ID do Contrato`         |
| `contractsLinkageId`       | `linkage_id (uuid)`      | `Linkage ID`      | `ID do Vínculo`          |
| `cashflowSettleContractId` | `contract_id (uuid)`     | `Contract ID`     | `ID do Contrato`         |
| `cashflowSourceEventId`    | `source_event_id (uuid)` | `Source Event ID` | `ID do Evento de Origem` |
| `cashflowLedgerContractId` | `contract_id (uuid)`     | `Contract ID`     | `ID do Contrato`         |
| `pnlEntityId`              | `entity_id (uuid)`       | `Entity ID`       | `ID da Entidade`         |
| `mtmObjectId`              | `object_id (uuid)`       | `Object ID`       | `ID do Objeto`           |
| `mtmContractId`            | `contract_id (uuid)`     | `Contract ID`     | `ID do Contrato`         |
| `mtmOrderId`               | `order_id (uuid)`        | `Order ID`        | `ID da Ordem`            |
| `optionalUuid`             | `Optional UUID`          | `ID (optional)`   | `ID (opcional)`          |

#### 3.2.3 Chaves i18n — Parâmetros técnicos (C3)

| Chave i18n                | ❌ Before                         | ✅ After (EN)           | ✅ After (PT-BR)            |
| ------------------------- | --------------------------------- | ----------------------- | --------------------------- |
| `cashflowAsOfDate`        | `as_of_date (YYYY-MM-DD)`         | `Reference Date`        | `Data de Referência`        |
| `contractsAsOfDate`       | `as_of_date (YYYY-MM-DD) for MTM` | `MTM Reference Date`    | `Data de Referência MTM`    |
| `ordersAsOfDate`          | `as_of_date (YYYY-MM-DD) for MTM` | `MTM Reference Date`    | `Data de Referência MTM`    |
| `mtmAsOfDate`             | `as_of_date (YYYY-MM-DD)`         | `Reference Date`        | `Data de Referência`        |
| `pnlPeriodStart`          | `period_start (YYYY-MM-DD)`       | `Period Start`          | `Início do Período`         |
| `pnlPeriodEnd`            | `period_end (YYYY-MM-DD)`         | `Period End`            | `Fim do Período`            |
| `cashflowLedgerStart`     | `start (optional, YYYY-MM-DD)`    | `Start Date (optional)` | `Data Inicial (opcional)`   |
| `cashflowLedgerEnd`       | `end (optional, YYYY-MM-DD)`      | `End Date (optional)`   | `Data Final (opcional)`     |
| `cashflowSourceEventType` | `source_event_type (optional)`    | `Event Type (optional)` | `Tipo de Evento (opcional)` |
| `pnlEntityType`           | `entity_type`                     | `Entity Type`           | `Tipo de Entidade`          |
| `mtmObjectType`           | `object_type`                     | `Object Type`           | `Tipo de Objeto`            |

#### 3.2.4 Chaves i18n — Jargão interno (C4)

| Chave i18n              | ❌ Before                                                                                  | ✅ After (EN)                                                | ✅ After (PT-BR)                                               |
| ----------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------ | -------------------------------------------------------------- |
| `responseHeader`        | `Response (as-is)`                                                                         | `Server Response`                                            | `Resposta do Servidor`                                         |
| `errorHeader`           | `Error (deterministic)`                                                                    | `Error Details`                                              | `Detalhes do Erro`                                             |
| `formRequestJson`       | `Request JSON`                                                                             | `Request Payload`                                            | `Dados da Requisição`                                          |
| `headerBadge`           | `Admin read-only (no auth configured)`                                                     | `Read-Only Mode`                                             | `Modo Somente Leitura`                                         |
| `homeCardOverviewText`  | `This frontend is read-only and reflects backend authority without client-side inference.` | `Real-time view of authoritative platform data.`             | `Visão em tempo real dos dados autorizados da plataforma.`     |
| `homeCardBackendTitle`  | `Backend Contract`                                                                         | `System Governance`                                          | `Governança do Sistema`                                        |
| `homeCardBackendText`   | `OpenAPI-driven. No endpoints are invented.`                                               | `All operations are contract-governed and auditable.`        | `Todas as operações são governadas por contrato e auditáveis.` |
| `homeCardWorklistsText` | `Blocked by Backend B1 (worklist endpoints missing).`                                      | `Worklists — pending activation.`                            | `Worklists — ativação pendente.`                               |
| `homeCardRfqText`       | `Blocked by Backend B2 (send/evidence endpoint missing).`                                  | `Evidence submission — pending activation.`                  | `Submissão de evidência — ativação pendente.`                  |
| `homeCardUiText`        | `SAP Horizon theming via theming-base-content.`                                            | `Enterprise-grade visual experience powered by SAP Horizon.` | `Experiência visual corporativa com tecnologia SAP Horizon.`   |

#### 3.2.5 Strings Hardcoded — Controllers (Categorias A)

| Controller → Método   | ❌ Before                                        | ✅ After (i18n key sugerida)   | ✅ Valor EN                                                |
| --------------------- | ------------------------------------------------ | ------------------------------ | ---------------------------------------------------------- |
| Base → `_formatError` | `"Unknown error"`                                | `errorUnknown`                 | `An unexpected error occurred. Please try again.`          |
| Base → `_formatError` | `"Request failed"`                               | `errorRequestFailed`           | `The request could not be completed.`                      |
| Base → `_formatError` | `"HTTP " + status + ": " + msg`                  | `errorServiceFailure`          | `Service error: {0}`                                       |
| Base → `submitData`   | `"Operation completed successfully"`             | `msgOperationSuccess`          | `Operation completed successfully.`                        |
| MarketData            | `"Please fill in Symbol, Date and Price."`       | `marketDataValidation`         | `Please provide the symbol, date, and price.`              |
| MarketData            | `"Cash settlement price ingested successfully."` | `marketDataIngestSuccess`      | `Cash settlement price recorded successfully.`             |
| MarketData            | `"Price ingested."`                              | `marketDataIngestToast`        | `Price recorded.`                                          |
| Mtm                   | `"Please provide Object ID and As-of Date."`     | `mtmValidationObjectDate`      | `Please provide the object identifier and reference date.` |
| Mtm                   | `"Please provide all snapshot query fields."`    | `mtmValidationSnapshot`        | `Please fill in all snapshot query parameters.`            |
| Mtm                   | `"Please provide all snapshot fields."`          | `mtmValidationSnapshotCreate`  | `Please fill in all snapshot fields.`                      |
| Mtm                   | `"MTM snapshot created."`                        | `mtmSnapshotCreated`           | `MTM snapshot created.`                                    |
| RfqDetail             | `"Counterparty ID"`                              | `rfqPlaceholderCounterparty`   | `Counterparty ID`                                          |
| RfqDetail             | `"Ranking failed: ..."`                          | `rfqRankingFailed`             | `Ranking could not be calculated: {0}`                     |
| LinkagesList          | `"Order UUID"`                                   | `linkagePlaceholderOrderId`    | `Order ID`                                                 |
| LinkagesList          | `"Contract UUID"`                                | `linkagePlaceholderContractId` | `Contract ID`                                              |
| Scenario (×16)        | `"Contract ID"`, `"Quantity MT"`, etc.           | `scenario*` keys               | _(ver seção 3.2.6)_                                        |

#### 3.2.6 Strings Hardcoded — Scenario.controller.js (16 instâncias)

| Hardcoded atual              | i18n key sugerida            | Valor EN                                | Valor PT-BR                                |
| ---------------------------- | ---------------------------- | --------------------------------------- | ------------------------------------------ |
| `"Contract ID"`              | `scenarioContractId`         | `Contract ID`                           | `ID do Contrato`                           |
| `"Quantity MT"`              | `scenarioQuantityMt`         | `Quantity (MT)`                         | `Quantidade (MT)`                          |
| `"Fixed Leg Side"`           | `scenarioFixedLegSide`       | `Fixed Leg Side`                        | `Lado da Perna Fixa`                       |
| `"Variable Leg Side"`        | `scenarioVariableLegSide`    | `Variable Leg Side`                     | `Lado da Perna Variável`                   |
| `"Fixed Price Value"`        | `scenarioFixedPriceValue`    | `Fixed Price`                           | `Preço Fixo`                               |
| `"Fixed Price Unit"`         | `scenarioFixedPriceUnit`     | `Price Unit`                            | `Unidade de Preço`                         |
| `"Float Pricing Convention"` | `scenarioFloatPricingConv`   | `Floating Pricing Convention`           | `Convenção de Precificação Flutuante`      |
| `"Order ID"`                 | `scenarioOrderId`            | `Order ID`                              | `ID da Ordem`                              |
| `"New Quantity MT"`          | `scenarioNewQuantityMt`      | `New Quantity (MT)`                     | `Nova Quantidade (MT)`                     |
| `"Symbol"`                   | `scenarioSymbol`             | `Symbol`                                | `Símbolo`                                  |
| `"Settlement Date"`          | `scenarioSettlementDate`     | `Settlement Date`                       | `Data de Liquidação`                       |
| `"Price USD"`                | `scenarioPriceUsd`           | `Price (USD)`                           | `Preço (USD)`                              |
| `"Add"`                      | `scenarioDialogAdd`          | `Add`                                   | `Adicionar`                                |
| `"Cancel"`                   | `scenarioDialogCancel`       | `Cancel`                                | `Cancelar`                                 |
| `"All fields are required."` | `scenarioFieldsRequired`     | `All fields are required.`              | `Todos os campos são obrigatórios.`        |
| `"Please fill in all..."`    | `scenarioValidationPeriod`   | `Please fill in all period parameters.` | `Preencha todos os parâmetros do período.` |
| `"What-if simulation..."`    | `scenarioSimulationComplete` | `What-if simulation completed.`         | `Simulação what-if concluída.`             |

#### 3.2.7 Strings Hardcoded — Views XML (Categoria B)

| View → Elemento                                   | ❌ Before                         | ✅ i18n key sugerida                                      | Valor EN                   |
| ------------------------------------------------- | --------------------------------- | --------------------------------------------------------- | -------------------------- |
| Cashflow → DatePicker (×4)                        | `placeholder="dd/MM/yyyy"`        | _(usar `displayFormat` nativo)_                           | —                          |
| Cashflow → Input                                  | `placeholder="Contract UUID"`     | `{i18n>contractsContractId}`                              | `Contract ID`              |
| ContractCreate → Input commodity                  | `placeholder="e.g. ALUMINIUM"`    | `placeholderCommodity`                                    | `e.g. Aluminium`           |
| ContractCreate → Input price                      | `placeholder="0.00"`              | `placeholderPrice`                                        | `0.00`                     |
| MarketData → Input symbol                         | `placeholder="e.g. LME_ALUMINUM"` | `placeholderSymbol`                                       | `e.g. LME Aluminum`        |
| MarketData → DatePicker                           | `placeholder="dd/MM/yyyy"`        | _(usar `displayFormat` nativo)_                           | —                          |
| MarketData → Input price                          | `placeholder="0.00"`              | `placeholderPrice`                                        | `0.00`                     |
| MarketData → Input source                         | `placeholder="e.g. westmetall"`   | `placeholderSource`                                       | `e.g. Westmetall`          |
| Mtm → Select items `"Hedge Contract"`/`"Order"`   | `text="Hedge Contract"`           | `mtmTypeHedgeContract` / `mtmTypeOrder`                   | `Hedge Contract` / `Order` |
| Mtm → Input (×2)                                  | `placeholder="UUID"`              | `{i18n>placeholderIdentifier}`                            | `Enter identifier`         |
| Mtm → DatePicker (×2)                             | `placeholder="dd/MM/yyyy"`        | _(usar `displayFormat` nativo)_                           | —                          |
| OrderCreate → Input quantity                      | `placeholder="0.00"`              | `placeholderQuantity`                                     | `0.00`                     |
| OrderCreate → Select items `AVG`/`AVGInter`/`C2R` | `text="AVG"` etc.                 | _(manter — termos técnicos do modelo econômico canônico)_ | —                          |
| OrderCreate → Input price                         | `placeholder="0.0000"`            | `placeholderPriceDetailed`                                | `0.0000`                   |
| Pnl → Input (×2)                                  | `placeholder="UUID"`              | `{i18n>placeholderIdentifier}`                            | `Enter identifier`         |
| Pnl → DatePicker (×4)                             | `placeholder="dd/MM/yyyy"`        | _(usar `displayFormat` nativo)_                           | —                          |
| RfqCreate → Select `"Commercial Hedge"` etc.      | `text="Commercial Hedge"`         | `rfqIntentCommercialHedge` etc.                           | `Commercial Hedge`         |
| RfqCreate → Input commodity                       | `placeholder="e.g., aluminum"`    | `placeholderCommodity`                                    | `e.g. Aluminium`           |
| RfqCreate → Select `"BUY"`/`"SELL"`               | `text="BUY"` / `text="SELL"`      | `directionBuy` / `directionSell`                          | `Buy` / `Sell`             |
| RfqCreate → Input quantity                        | `placeholder="0.00"`              | `placeholderQuantity`                                     | `0.00`                     |

> **Nota sobre `AVG`, `AVGInter`, `C2R`**: Estes são termos canônicos do modelo econômico constitucional (pricing conventions). Devem ser mantidos como estão, pois são nomenclatura de domínio, não jargão técnico.

---

## 4. Terminologia Oficial

### 4.1 Glossário Canônico

Termos derivados da System Constitution que devem ser usados consistentemente em toda a plataforma.

| Termo Canônico (EN)         | Termo Canônico (PT-BR)      | Definição                                                | ❌ Não usar                      |
| --------------------------- | --------------------------- | -------------------------------------------------------- | -------------------------------- |
| Sales Order (SO)            | Ordem de Venda (OV)         | Ordem que gera exposição comercial ativa                 | sell order, venda                |
| Purchase Order (PO)         | Ordem de Compra (OC)        | Ordem que gera exposição comercial passiva               | buy order, compra                |
| Commercial Active Exposure  | Exposição Comercial Ativa   | MT residuais de ordens de venda com preço variável       | long exposure, exposure ativa    |
| Commercial Passive Exposure | Exposição Comercial Passiva | MT residuais de ordens de compra com preço variável      | short exposure, exposure passiva |
| Commercial Net Exposure     | Exposição Comercial Líquida | Active − Passive                                         | net, saldo                       |
| Global Active Exposure      | Exposição Global Ativa      | Commercial Active + Hedge Short (não vinculado)          | total active                     |
| Global Passive Exposure     | Exposição Global Passiva    | Commercial Passive + Hedge Long (não vinculado)          | total passive                    |
| Global Net Exposure         | Exposição Global Líquida    | Global Active − Global Passive (KPI primário de risco)   | net global, risco total          |
| Hedge Contract              | Contrato de Hedge           | Contrato com duas pernas (fixa + variável)               | hedge, contrato                  |
| Fixed Leg                   | Perna Fixa                  | Perna do contrato com preço fixo                         | fixed side, lado fixo            |
| Variable Leg                | Perna Variável              | Perna do contrato com preço variável                     | float leg, floating              |
| Hedge Long                  | Hedge Long                  | Classificação: Fixed Buy leg                             | compra de hedge                  |
| Hedge Short                 | Hedge Short                 | Classificação: Fixed Sell leg                            | venda de hedge                   |
| Linkage                     | Vínculo                     | Associação entre contrato de hedge e ordem               | link, associação, ligação        |
| RFQ                         | RFQ                         | Request for Quote — solicitação de cotação institucional | pedido de cotação, quote request |
| Award                       | Adjudicação                 | Ação canônica de concessão de contrato via RFQ           | concessão, premiação             |
| Mark-to-Market (MTM)        | Marcação a Mercado (MTM)    | Valorização de posição a preço D-1                       | valuation, valoração             |
| Cash Settlement             | Liquidação em Caixa         | Preço de referência autoritativo (série Cash Settlement) | preço de mercado, closing price  |
| Cashflow Analytic           | Fluxo de Caixa Analítico    | Visão não persistente para gestão de risco               | cashflow view, fluxo analítico   |
| Cashflow Baseline           | Fluxo de Caixa Baseline     | Registro institucional persistente                       | baseline snapshot, foto base     |
| Cashflow Ledger             | Razão de Fluxo de Caixa     | Registro contábil/auditoria                              | ledger, livro razão              |
| P&L Snapshot                | Snapshot de P&L             | Registro imutável, append-only, idempotente              | foto de P&L, P&L report          |
| What-If Scenario            | Cenário What-If             | Simulação em memória, sem persistência                   | simulação, scenario run          |
| Pricing Convention          | Convenção de Precificação   | AVG, AVGInter, C2R — termos canônicos                    | tipo de preço, pricing type      |
| Metric Ton (MT)             | Tonelada Métrica (MT)       | Unidade canônica de quantidade                           | ton, tonelada                    |

### 4.2 Termos Proibidos na UI

| Termo                 | Motivo                                  | Substituição                       |
| --------------------- | --------------------------------------- | ---------------------------------- |
| `uuid`                | Implementação interna                   | `ID` ou `Identifier`               |
| `endpoint`            | Jargão de API                           | _(remover — não é conceito de UI)_ |
| `backend`             | Arquitetura interna                     | `platform` ou `system`             |
| `payload`             | Jargão técnico                          | `data` ou `request data`           |
| `HTTP xxx`            | Protocolo de transporte                 | _(mensagem funcional)_             |
| `as_of_date`          | snake_case de backend                   | `Reference Date`                   |
| `contract_id`         | Nome de campo de banco                  | `Contract ID`                      |
| `snake_case` em geral | Conveção de naming de backend Python    | camelCase ou linguagem natural     |
| `blocker`, `B1`, `B2` | Referência interna de gestão de projeto | `pending activation`               |
| `OpenAPI`             | Especificação técnica                   | _(remover)_                        |
| `inference`           | Conceito técnico de arquitetura         | _(remover)_                        |

---

## 5. Convenção de i18n

### 5.1 Estrutura de Chaves

Padrão de nomenclatura para chaves i18n:

```
{módulo}{Tipo}{Elemento}
```

| Prefixo de módulo | Módulo              |
| ----------------- | ------------------- |
| `home`            | Home / Dashboard    |
| `exposures`       | Exposures           |
| `orders`          | Orders              |
| `rfq`             | RFQ                 |
| `contracts`       | Contracts           |
| `linkages`        | Linkages            |
| `cashflow`        | Cashflow            |
| `pnl`             | P&L                 |
| `scenario`        | Scenario            |
| `mtm`             | MTM                 |
| `marketData`      | Market Data         |
| `audit`           | Audit               |
| `nav`             | Navigation          |
| `col`             | Column headers      |
| `msg`             | System messages     |
| `error`           | Error messages      |
| `placeholder`     | Shared placeholders |
| `validation`      | Validation messages |

| Tipo de elemento    | Sufixo/Elemento | Exemplo                          |
| ------------------- | --------------- | -------------------------------- |
| Label de campo      | `Label`         | `ordersQuantityLabel`            |
| Placeholder         | `Placeholder`   | `ordersQuantityPlaceholder`      |
| Título de seção     | `Title`         | `rfqCreateTitle`                 |
| Subtítulo           | `Subtitle`      | `homeSubtitle`                   |
| Botão/Ação          | `Action`        | `rfqAwardAction`                 |
| Mensagem de sucesso | `Success`       | `ordersCreateSuccess`            |
| Mensagem de erro    | `Error`         | `ordersCreateError`              |
| Validação           | `Validation`    | `ordersQuantityValidation`       |
| Tooltip             | `Tooltip`       | `exposuresHedgeRatioTooltip`     |
| Tab label           | `Tab`           | `rfqQuotesTab`                   |
| Select item         | `Option`        | `rfqIntentCommercialHedgeOption` |

### 5.2 Regras de Conteúdo por Idioma

| Arquivo                 | Escopo              | Regra                                                          |
| ----------------------- | ------------------- | -------------------------------------------------------------- |
| `i18n.properties`       | Default (EN)        | Autoridade. Todos os demais herdam deste.                      |
| `i18n_en.properties`    | English explícito   | Deve ser idêntico ao default ou pode ser removido.             |
| `i18n_pt_BR.properties` | Português do Brasil | Tradução institucional. Base para todos os mercados lusófonos. |
| `i18n_pt.properties`    | Português genérico  | Deve ser idêntico ao `pt_BR` ou pode ser removido como alias.  |

### 5.3 Regras de Manutenção

| Regra  | Descrição                                                                                                   |
| ------ | ----------------------------------------------------------------------------------------------------------- |
| **M1** | Toda nova chave i18n deve existir em TODOS os 4 arquivos (ou nos 2 canônicos: default + pt_BR).             |
| **M2** | Nenhum texto visível pode aparecer hardcoded em controller `.js` ou view `.xml`.                            |
| **M3** | Chaves obsoletas são removidas, não comentadas.                                                             |
| **M4** | Chaves de placeholder com formatos numéricos (`0.00`, `0.0000`) podem usar o valor literal como i18n value. |
| **M5** | DatePickers devem usar `displayFormat` / `valueFormat` nativo do UI5 em vez de placeholder strings.         |
| **M6** | Select items (core:Item) devem usar `{i18n>key}` binding, nunca `text="literal"`.                           |

---

## 6. Regras de Governança

### 6.1 Revisão de Linguagem como Gate de PR

Toda Pull Request que adicione ou modifique texto visível ao usuário deve passar por verificação de conformidade com este plano antes de merge.

**Critérios de aprovação:**

| #   | Critério                                                         | Tipo    |
| --- | ---------------------------------------------------------------- | ------- |
| G1  | Nenhuma string hardcoded em controller ou view                   | Blocker |
| G2  | Todas as chaves i18n existem nos 4 arquivos                      | Blocker |
| G3  | Nenhum verbo HTTP ou caminho de API em valor i18n                | Blocker |
| G4  | Nenhum `(uuid)` ou snake_case em texto visível                   | Blocker |
| G5  | Mensagens de erro descrevem impacto funcional, não causa técnica | Blocker |
| G6  | Terminologia alinhada ao Glossário Canônico (seção 4.1)          | Warning |
| G7  | Naming convention de chaves i18n segue padrão (seção 5.1)        | Warning |

### 6.2 Automação Recomendada

| Ferramenta          | Propósito                                                                              | Prioridade |
| ------------------- | -------------------------------------------------------------------------------------- | ---------- |
| **Lint rule XML**   | Rejeitar `text="..."` / `placeholder="..."` hardcoded em views                         | Alta       |
| **Lint rule JS**    | Rejeitar strings literais em `MessageBox`, `MessageToast`, `setText`, `setPlaceholder` | Alta       |
| **i18n sync check** | Verificar paridade de chaves entre os 4 arquivos                                       | Média      |
| **Grep CI**         | `grep -rn "GET \|POST \|PUT \|DELETE " webapp/i18n/` = fail                            | Alta       |
| **Grep CI**         | `grep -rn "(uuid)" webapp/i18n/` = fail                                                | Alta       |

### 6.3 Alinhamento com Governance.md Existente

Este plano estende o framework de governança existente (`docs/governance.md`) com a seguinte cláusula interpretativa:

> A regra constitucional _"Frontend renders only. Frontend does not infer or compute economics"_ se estende à linguagem: **o frontend não expõe implementação interna**. Assim como o frontend não deve computar economia, também não deve exibir detalhes de API, protocolo ou arquitetura.

A regra de _"No silent fallback"_ se aplica a mensagens de erro:

> Mensagens de erro genéricas como `"Unknown error"` ou `"Operation completed successfully"` constituem _silent fallback_ linguístico — a interface falha silenciosamente em comunicar o que aconteceu. Cada mensagem deve ser específica ao contexto.

---

## 7. Checklist de Consolidação

### 7.1 Prioridade de Execução

A execução deve seguir a ordem: **impacto sistêmico** → **frequência de exposição** → **volume de instâncias**.

#### Wave 1 — Correções Sistêmicas (Impacto: ALL controllers)

| #   | Ação                                                                                    | Arquivos            | Instâncias | Prioridade |
| --- | --------------------------------------------------------------------------------------- | ------------------- | ---------- | ---------- |
| 1.1 | Refatorar `BaseController._formatError()` — remover exposição de HTTP status, usar i18n | `BaseController.js` | 4          | **P0**     |
| 1.2 | Refatorar `BaseController.submitData()` — fallback de sucesso via i18n                  | `BaseController.js` | 1          | **P0**     |

#### Wave 2 — i18n: Eliminar Linguagem de API (Impacto: TODAS as telas)

| #   | Ação                                                               | Arquivos              | Instâncias | Prioridade |
| --- | ------------------------------------------------------------------ | --------------------- | ---------- | ---------- |
| 2.1 | Reescrever 30 chaves C1 (HTTP paths → labels institucionais)       | `i18n*.properties` ×4 | 30 ×4      | **P0**     |
| 2.2 | Reescrever 12 chaves C2 (UUID refs → labels legíveis)              | `i18n*.properties` ×4 | 12 ×4      | **P1**     |
| 2.3 | Reescrever 11 chaves C3 (parâmetros técnicos → labels descritivos) | `i18n*.properties` ×4 | 11 ×4      | **P1**     |
| 2.4 | Reescrever 10 chaves C4 (jargão interno → linguagem institucional) | `i18n*.properties` ×4 | 10 ×4      | **P0**     |

#### Wave 3 — Controllers: Extrair Hardcoded para i18n

| #   | Ação                                                     | Arquivo                      | Instâncias | Prioridade |
| --- | -------------------------------------------------------- | ---------------------------- | ---------- | ---------- |
| 3.1 | Scenario.controller.js — extrair 16 strings para i18n    | `Scenario.controller.js`     | 16         | **P1**     |
| 3.2 | Mtm.controller.js — extrair 4 strings para i18n          | `Mtm.controller.js`          | 4          | **P1**     |
| 3.3 | RfqDetail.controller.js — extrair 4 strings para i18n    | `RfqDetail.controller.js`    | 4          | **P1**     |
| 3.4 | MarketData.controller.js — extrair 3 strings para i18n   | `MarketData.controller.js`   | 3          | **P2**     |
| 3.5 | LinkagesList.controller.js — extrair 3 strings para i18n | `LinkagesList.controller.js` | 3          | **P2**     |

#### Wave 4 — Views XML: Extrair Hardcoded para i18n

| #   | Ação                                               | Arquivo                   | Instâncias | Prioridade |
| --- | -------------------------------------------------- | ------------------------- | ---------- | ---------- |
| 4.1 | Mtm.view.xml — Select items + placeholders UUID    | `Mtm.view.xml`            | 8          | **P1**     |
| 4.2 | RfqCreate.view.xml — Select items + placeholders   | `RfqCreate.view.xml`      | 7          | **P1**     |
| 4.3 | Pnl.view.xml — placeholders UUID + datas           | `Pnl.view.xml`            | 6          | **P2**     |
| 4.4 | Cashflow.view.xml — placeholders UUID + datas      | `Cashflow.view.xml`       | 5          | **P2**     |
| 4.5 | OrderCreate.view.xml — Select items + placeholders | `OrderCreate.view.xml`    | 5          | **P2**     |
| 4.6 | MarketData.view.xml — placeholders                 | `MarketData.view.xml`     | 4          | **P2**     |
| 4.7 | ContractCreate.view.xml — placeholders             | `ContractCreate.view.xml` | 2          | **P2**     |

#### Wave 5 — Validação e Formalização

| #   | Ação                                                                                   | Escopo               | Prioridade |
| --- | -------------------------------------------------------------------------------------- | -------------------- | ---------- |
| 5.1 | Lint: Adicionar grep CI para HTTP verbs e `(uuid)` em i18n                             | CI pipeline          | **P1**     |
| 5.2 | Lint: Verificar paridade de chaves i18n entre os 4 arquivos                            | CI pipeline          | **P2**     |
| 5.3 | Revisar `i18n_en.properties` vs `i18n.properties` — considerar eliminação de duplicata | `i18n_en.properties` | **P2**     |
| 5.4 | Documentar regra de linguagem no `AGENTS.md` para agentes de código                    | `AGENTS.md`          | **P1**     |

### 7.2 Métricas de Sucesso

| Métrica                                 | Estado atual | Meta pós-consolidação |
| --------------------------------------- | ------------ | --------------------- |
| Strings hardcoded em controllers        | 34           | 0                     |
| Strings hardcoded em views XML          | 37           | 0                     |
| Chaves i18n com verbos HTTP             | 30           | 0                     |
| Chaves i18n com `(uuid)`                | 12           | 0                     |
| Chaves i18n com jargão técnico          | 21           | 0                     |
| Controllers afetados por `_formatError` | 21           | 0 (refatorado)        |
| **Total de violações**                  | **134**      | **0**                 |

### 7.3 Estimativa de Esforço

| Wave | Escopo                     | Itens i18n (×4 arquivos) | Arquivos código | Esforço estimado |
| ---- | -------------------------- | ------------------------ | --------------- | ---------------- |
| 1    | BaseController (sistêmico) | +6 novas chaves          | 1               | Baixo            |
| 2    | Reescrita i18n             | 63 chaves ×4             | 4               | Médio            |
| 3    | Controllers hardcoded      | +30 novas chaves         | 5               | Médio            |
| 4    | Views XML hardcoded        | +15 novas chaves         | 7               | Médio            |
| 5    | Automação + governança     | —                        | CI + docs       | Baixo            |

---

## Anexo A — Mapa de Dependências

```
Wave 1 (BaseController)
  ↓ deve ser executado ANTES de
Wave 2 (i18n rewrite) ──→ pode rodar em paralelo com ──→ Wave 3 (controllers)
                                                          Wave 4 (views)
  ↓ tudo acima deve estar concluído ANTES de
Wave 5 (automação + lint)
```

**Regra**: Wave 1 é pré-requisito absoluto. Waves 2, 3, 4 podem ser paralelizadas. Wave 5 só é executada após validação das waves anteriores.

---

## Anexo B — Referências Constitucionais

| Regra constitucional aplicável                               | Seção deste plano que endereça           |
| ------------------------------------------------------------ | ---------------------------------------- |
| _"Frontend is a presenter. Frontend renders only."_          | §2 Product Voice, §6 Governança          |
| _"Frontend does not infer or compute economics."_            | §3 R5, R7 (sem inferir causa de erro)    |
| _"Messages are evidence, not UI artifacts."_                 | §4.1 (terminologia de RFQ)               |
| _"No silent fallback."_                                      | §3 R7, R8 (erros e sucessos específicos) |
| _"All outputs must be precise, structured, verifiable."_     | §2.2 Pilares da Voz                      |
| _"Correctness, determinism and auditability have priority."_ | §6.1 Gates de PR                         |

---

**Fim do documento.**

_Este plano é prescritivo e executável. Nenhuma alteração de código deve ser feita fora do escopo definido nas 5 waves acima. A execução deve seguir a ordem de prioridade e respeitar as dependências documentadas no Anexo A._
