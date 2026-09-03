# Política Comercial, de Pedidos, Entregas, Trocas e Garantias — TechStore v1.0

**Versão:** 1.0 | **Operação:** 100% online | **Marketplace:** Não | **Lojas físicas:** Não

> Master document for **synthetic-policies**. Do not ingest this file as a single RAG chunk — split per `references/kb-split.md`.

---

## 1. Disposições Gerais

A TechStore vende exclusivamente por canais digitais oficiais. Condições de produto, preço, entrega e pagamento aparecem na página do produto ou no checkout. Ao concluir o pedido, o cliente declara acesso prévio às condições. Interpretar em conjunto com Política de Privacidade e Termos de Uso.

## 2. Pedidos e Cadastro

- Pedidos válidos apenas em canais oficiais TechStore.
- Cadastro com dados verdadeiros; e-mail válido para confirmação, pagamento, entrega, devoluções e suporte.
- Confirmação do pedido inclui: número, itens, valores, endereço, pagamento, previsão de entrega.

## 3. Produtos e Disponibilidade

Informações de marca, modelo, especificações, compatibilidade e garantia na página do produto. Imagens ilustrativas. Cliente deve verificar compatibilidade (hardware, periféricos, smartphones, etc.) antes da compra.

## 4. Preços e Ofertas

Preço vigente no momento da contratação. Promoções podem ter prazo, estoque limitado e condições de pagamento. Descontos PIX/cartão conforme oferta. Erros evidentes de publicação: análise e providências legais.

## 5. Pagamentos

**Formas v1.0:** PIX e cartão de crédito.

- **PIX:** prazo na finalização; não pagamento pode cancelar pedido; confirmação via instituição/intermediador; nunca PIX fora dos canais oficiais.
- **Cartão:** sujeito a autorização e antifraude; verificações adicionais quando necessário.
- Envio depende de confirmação do pagamento.

## 6. Cancelamento

Cancelamento enquanto etapa operacional permitir. Após expedição/entrega: fluxo de devolução. TechStore pode cancelar por: pagamento não confirmado, fraude, inconsistência, indisponibilidade, erro operacional, determinação legal. Cancelamento imputável à TechStore: restituição conforme lei.

## 7. Processamento e Entrega

100% online; entrega no endereço informado; **sem retirada em loja**. Prazo estimado no checkout; sujeito a confirmação de pagamento. Force majeure pode alterar prazo. Cliente responsável por endereço correto. Rastreamento após expedição quando disponível.

## 8. Recebimento e Avarias

Verificar embalagem e danos visíveis no recebimento. Comunicar avarias preferencialmente em **48 horas** (prazo operacional; não limita direitos legais).

## 9. Produto em Desacordo

Produto diferente do pedido: contatar canais oficiais. Soluções: devolução, envio correto, restituição. Conservar produto até instruções.

## 10. Direito de Arrependimento (CDC)

Compras eletrônicas: **7 dias** para desistência (CDC), contados conforme lei, da assinatura ou recebimento. Solicitação pelos canais oficiais. Devolução conforme orientações. Produtos digitais/códigos: regras específicas prévias.

## 11. Trocas e Devoluções

Solicitações pelos canais oficiais com pedido, produto, motivo e evidências. Análise técnica quando necessário. Mau uso ou instalação incorreta considerados na análise sem prejuízo de direitos legais.

## 12. Garantia

Garantia legal, contratual do fabricante e eventual adicional TechStore. **Produtos duráveis:** 90 dias CDC para vícios aparentes (desde entrega); ocultos desde evidência. Fabricante: documentação e fluxo TechStore/fabricante/assistência.

## 13. Exclusões de Garantia (análise)

Uso inadequado, instalação incorreta, violação, modificações, desgaste natural, etc. — análise caso a caso; não afasta direitos legais automaticamente.

## 14. Assistência Técnica

Envio, coleta, fabricante ou assistência autorizada conforme produto. Backup de dados antes de envio de dispositivos.

## 15. Segurança e Fraude

Análise antifraude; validações adicionais; possível bloqueio/cancelamento. Cliente protege senha e dispositivos. TechStore não pede senha por canais não oficiais.

## 16. Reembolso e Restituição

Restituição pela forma de pagamento e lei aplicável. PIX e cartão: prazos dependem de processador/emissor. Não converter automaticamente em crédito interno quando lei exigir restituição adequada.

## 17–18. Atendimento e Registro

Canais digitais oficiais; protocolo quando aplicável. Registro de solicitações para auditoria e compliance.

## 19–24. PJ/PF, Responsabilidades, Privacidade, Alterações, Vigência

Atendimento PF e PJ. Responsabilidades cliente e TechStore conforme seções 20–21. Dados conforme Política de Privacidade e LGPD. Política atualizável; prevalece lei imperativa em caso de conflito.

---

## Resumo operacional (automação)

```text
PEDIDO → Pagamento confirmado? → Processamento → Expedição → Entrega
→ Problema? → Arrependimento | Avaria | Defeito → Devolução/Análise/Garantia → Reembolso/solução
```

## Classificação AI (`policy_type`)

`ORDER`, `PAYMENT`, `CANCELLATION`, `SHIPPING`, `DELIVERY`, `DAMAGED_PRODUCT`, `WRONG_PRODUCT`, `RETURN`, `REFUND`, `WARRANTY`, `TECHNICAL_SUPPORT`, `FRAUD`, `CUSTOMER_ACCOUNT`, `PRIVACY`

Ver `references/intent-taxonomy.md`.
