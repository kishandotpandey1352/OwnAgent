                   OwnAgent
                      │
             ExecutionContext
                      │
        ┌─────────────┴─────────────┐
        │                           │
 Agent runtime                Legacy graph
        │                           │
 authorize_tool()        authorize_registered_tool()
        │                           │
        └─────────────┬─────────────┘
                      │
                  Tool Registry


                   Model calls
                      │
                ModelGateway
                      │
             Provider Registry
                      │
          ┌───────────┼────────────┐
          │           │            │
       OpenAI       Ollama      LM Studio



week 1 new architecture::

                         OwnAgent
                            │
              ┌─────────────┴─────────────┐
              │                           │
          Web App                    Desktop App
         Next.js                     Tauri
              │                           │
              └─────────────┬─────────────┘
                            │
                     OwnAgent Core
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
       Models             Tools           Workflows
          │                 │                 │
       Policies         Connectors        Knowledge
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                    Capability Packs
          ┌────────┬────────┼────────┬─────────┐
          │        │        │        │         │
       Student Research  Finance  Science   Creative

week 2:

                  ModelGateway
                       │
          ┌────────────┼────────────┐
          │            │            │
      generate       stream       health
          │            │            │
          ├──────── capabilities ────┤
          │            │            │
          └──────── estimate ────────┘
                       │
                ModelProvider
                       │
                    OpenAI