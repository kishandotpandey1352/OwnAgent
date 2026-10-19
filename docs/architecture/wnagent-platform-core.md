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



new architecture::

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