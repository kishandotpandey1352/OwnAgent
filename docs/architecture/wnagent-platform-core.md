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