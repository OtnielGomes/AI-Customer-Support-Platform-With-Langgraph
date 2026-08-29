# The Assistant does not create Tickets

A Ticket is started by the Customer (Portal) or by a Human Agent (Console). The Assistant must not call a tool to open a second Ticket in order to split intents or to reach a human — that is Escalation, or a new case opened in the UI. `create_support_ticket` is leftover form-era surface, not a domain action.

Status: accepted
