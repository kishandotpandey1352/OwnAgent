"use client";

import { useEffect, useState } from "react";

import { MemorySuggestionCard } from "@/components/MemorySuggestionCard";
import { ResponseCard } from "@/components/ResponseCard";
import { WebSourcePanel } from "./WebSourcePanel";
import { WebFallbackToggle } from "@/components/WebFallbackToggle";

import {
  sendFinancePrompt,
  type WebAwareFinanceResponse,
} from "@/lib/api";
import { appendHistory } from "@/lib/history";

import type {
  AppMode,
  AuthState,
  FinanceResponse,
  FinanceTask,
  HistoryAttachment,
  HistoryEntry,
  ProviderOption,
} from "@/types";

interface ChatPanelProps {
  auth: AuthState | null;
  mode: Exclude<AppMode, "compare">;
  task: FinanceTask;
  provider: ProviderOption;

  onModeChange: (
    mode: Exclude<AppMode, "compare">,
  ) => void;

  onTaskChange: (
    task: FinanceTask,
  ) => void;

  onProviderChange: (
    providerId: string,
  ) => void;

  onSaved?: (
    entry: HistoryEntry,
  ) => void;
}


type AttachmentKind =
  | "pdf"
  | "docx"
  | "text"
  | "csv"
  | "image"
  | "unknown";


type ChatAttachment = {
  id: string;
  name: string;
  type: string;
  size: number;
  kind: AttachmentKind;

  text?: string;

  pageCount?: number;

  truncated?: boolean;

  warnings?: string[];

  note?: string;
};


type AttachmentExtractResponse = {
  ok: boolean;

  request_id?: string;

  attachment?: ChatAttachment;

  error?: string;
};


type MemorySuggestion = {
  is_memory_request: boolean;

  memory_type: string | null;

  memory_key: string | null;

  memory_value: string | null;

  confidence: number;

  requires_confirmation: boolean;

  reason: string | null;

  blocked: boolean;
};


const taskCopy: Record<
  FinanceTask,
  {
    route: string;

    primaryLabel: string;

    primaryPlaceholder: string;

    secondaryLabel: string;

    secondaryPlaceholder: string;

    defaultPrompt: string;

    defaultContext: string;

    runLabel: string;

    helperText: string;
  }
> = {
  summarize: {
    route: "POST /summarize",

    primaryLabel:
      "Text to summarize",

    primaryPlaceholder:
      "Paste a financial update, filing excerpt, earnings note, or market paragraph...",

    secondaryLabel:
      "Optional instructions",

    secondaryPlaceholder:
      "Example: Summarize in 3 bullets. Focus on revenue, margins, cash flow, and risks...",

    defaultPrompt:
      "Revenue increased 12 percent, but margins declined because input costs and interest expense rose. Operating cash flow improved, while management warned that higher interest rates may pressure demand next quarter.",

    defaultContext:
      "Summarize in 3 concise bullets. Focus on revenue growth, margin pressure, cash flow, and forward-looking risks.",

    runLabel:
      "Run summary",

    helperText:
      "Create a concise finance summary from an update, filing excerpt, earnings paragraph, or market note.",
  },

  qa: {
    route: "POST /qa",

    primaryLabel:
      "Question",

    primaryPlaceholder:
      "Ask a finance question, for example: What caused margin pressure?",

    secondaryLabel:
      "Context",

    secondaryPlaceholder:
      "Paste the source material the model should use to answer the question...",

    defaultPrompt:
      "What caused margin pressure, and what should investors monitor next quarter?",

    defaultContext:
      "Revenue increased 12 percent, but margins declined because input costs and interest expense rose. Operating cash flow improved, while management warned that higher interest rates may pressure demand next quarter.",

    runLabel:
      "Run Q&A",

    helperText:
      "Ask a targeted finance question using pasted context or attached document text.",
  },

  "risk-analysis": {
    route: "POST /risk-analysis",

    primaryLabel:
      "Text to analyze",

    primaryPlaceholder:
      "Paste a company update, filing excerpt, earnings commentary, or disclosure to analyze...",

    secondaryLabel:
      "Optional risk focus",

    secondaryPlaceholder:
      "Example: Focus on liquidity risk, margin pressure, refinancing risk, or demand slowdown...",

    defaultPrompt:
      "The company has rising revenue, declining margins, higher interest expense, improved operating cash flow, and a weaker demand outlook for next quarter.",

    defaultContext:
      "Focus on liquidity risk, margin pressure, interest expense, refinancing risk, and demand slowdown.",

    runLabel:
      "Run risk analysis",

    helperText:
      "Identify financial, operating, liquidity, demand, refinancing, and disclosure risks.",
  },
};


function toHistoryAttachments(
  activeAttachments: ChatAttachment[],
): HistoryAttachment[] {
  return activeAttachments.map(
    (attachment) => ({
      id:
        attachment.id,

      name:
        attachment.name,

      type:
        attachment.type,

      size:
        attachment.size,

      kind:
        attachment.kind,

      pageCount:
        attachment.pageCount,

      truncated:
        attachment.truncated,

      extractedChars:
        attachment.text?.length ?? 0,
    }),
  );
}


function makeHistoryEntry(
  response: FinanceResponse,
  context?: string,
  attachments?: HistoryAttachment[],
): HistoryEntry {
  return {
    ...response,

    sourcePrompt:
      response.prompt,

    context,

    attachments,
  };
}


function getTaskLabel(
  task: FinanceTask,
) {
  if (
    task === "summarize"
  ) {
    return "Summarize";
  }

  if (
    task === "qa"
  ) {
    return "Q&A";
  }

  return "Risk Analysis";
}


function formatFileSize(
  size: number,
) {
  if (
    size < 1024
  ) {
    return `${size} B`;
  }

  if (
    size
    < 1024 * 1024
  ) {
    return `${(
      size / 1024
    ).toFixed(1)} KB`;
  }

  return `${(
    size
    / 1024
    / 1024
  ).toFixed(1)} MB`;
}


function buildAttachmentContext(
  attachment: ChatAttachment,
) {
  if (
    !attachment.text?.trim()
  ) {
    return "";
  }

  const metadata = [
    `File: ${attachment.name}`,

    `Type: ${attachment.kind}`,

    attachment.pageCount
      ? `Pages: ${attachment.pageCount}`
      : undefined,

    attachment.truncated
      ? "Note: extracted text was truncated"
      : undefined,
  ]
    .filter(Boolean)
    .join(" | ");

  return (
    `\n\n--- Attached document context (${metadata}) ---\n`
    + `${attachment.text.trim()}\n`
    + "--- End attached document context ---"
  );
}


function buildActiveAttachmentContext(
  activeAttachments: ChatAttachment[],
) {
  return (
    activeAttachments
      .filter(
        (attachment) =>
          attachment.text?.trim(),
      )
      .map(
        (attachment) =>
          buildAttachmentContext(
            attachment,
          ),
      )
      .join("\n\n")
  );
}


function statusToneClass(
  tone:
    | "cyan"
    | "emerald"
    | "amber"
    | "slate",
) {
  if (
    tone === "cyan"
  ) {
    return (
      "border-cyan-300/20 "
      + "bg-cyan-300/10 "
      + "text-cyan-100"
    );
  }

  if (
    tone === "emerald"
  ) {
    return (
      "border-emerald-300/20 "
      + "bg-emerald-300/10 "
      + "text-emerald-100"
    );
  }

  if (
    tone === "amber"
  ) {
    return (
      "border-amber-300/20 "
      + "bg-amber-300/10 "
      + "text-amber-100"
    );
  }

  return (
    "border-white/10 "
    + "bg-white/5 "
    + "text-slate-300"
  );
}


function MiniPill({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;

  tone?:
    | "cyan"
    | "emerald"
    | "amber"
    | "slate";
}) {
  return (
    <span
      className={[
        "inline-flex rounded-full border",
        "px-2.5 py-1",
        "text-[11px] font-semibold",
        statusToneClass(
          tone,
        ),
      ].join(" ")}
    >
      {children}
    </span>
  );
}


export function ChatPanel({
  auth,
  mode,
  task,
  provider,
  onModeChange,
  onTaskChange,
  onProviderChange,
  onSaved,
}: ChatPanelProps) {
  const currentTaskCopy =
    taskCopy[
      task
    ];

  const [
    prompt,
    setPrompt,
  ] = useState(
    currentTaskCopy.defaultPrompt,
  );

  const [
    context,
    setContext,
  ] = useState(
    currentTaskCopy.defaultContext,
  );

  const [
    temperature,
    setTemperature,
  ] = useState(
    provider.defaultTemperature,
  );

  const [
    maxNewTokens,
    setMaxNewTokens,
  ] = useState(
    provider.defaultMaxNewTokens,
  );

  const [
    response,
    setResponse,
  ] = useState<
    WebAwareFinanceResponse | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(
    false,
  );

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    attachments,
    setAttachments,
  ] = useState<
    ChatAttachment[]
  >([]);

  const [
    attachmentError,
    setAttachmentError,
  ] = useState<
    string | null
  >(null);

  const [
    uploadingAttachment,
    setUploadingAttachment,
  ] = useState(
    false,
  );

  const [
    memorySuggestion,
    setMemorySuggestion,
  ] = useState<
    MemorySuggestion | null
  >(null);

  const [
    savingMemorySuggestion,
    setSavingMemorySuggestion,
  ] = useState(
    false,
  );

  const [
    memoryStatusMessage,
    setMemoryStatusMessage,
  ] = useState<
    string | null
  >(null);

  // =====================================================
  // Phase 3H-F-D
  // Explicit user permission for public web fallback.
  //
  // Default MUST remain false.
  // =====================================================

  const [
    allowWebFallback,
    setAllowWebFallback,
  ] = useState(
    false,
  );

  const memoryDecisionPending =
    Boolean(
      memorySuggestion,
    );


  useEffect(
    () => {
      setPrompt(
        taskCopy[
          task
        ].defaultPrompt,
      );

      setContext(
        taskCopy[
          task
        ].defaultContext,
      );

      setAttachments([]);

      setAttachmentError(
        null,
      );

      setResponse(
        null,
      );

      setError(
        null,
      );
    },
    [
      task,
    ],
  );


  useEffect(
    () => {
      setTemperature(
        provider.defaultTemperature,
      );

      setMaxNewTokens(
        provider.defaultMaxNewTokens,
      );
    },
    [
      provider.defaultTemperature,
      provider.defaultMaxNewTokens,
    ],
  );


  async function handleAttachmentUpload(
    files: FileList | null,
  ) {
    if (
      !files?.length
    ) {
      return;
    }

    setAttachmentError(
      null,
    );

    setUploadingAttachment(
      true,
    );

    try {
      const maxAttachments =
        Number(
          process.env
            .NEXT_PUBLIC_MAX_ATTACHMENTS_PER_REQUEST
          ?? "3",
        );

      const selectedFiles =
        Array.from(
          files,
        ).slice(
          0,
          maxAttachments,
        );

      for (
        const file
        of selectedFiles
      ) {
        const formData =
          new FormData();

        formData.append(
          "file",
          file,
        );

        const uploadResponse =
          await fetch(
            "/api/attachments/extract",
            {
              method:
                "POST",

              body:
                formData,
            },
          );

        const payload =
          (
            await uploadResponse.json()
          ) as AttachmentExtractResponse;

        if (
          !uploadResponse.ok
          || !payload.ok
          || !payload.attachment
        ) {
          throw new Error(
            payload.error
            ?? "Attachment extraction failed.",
          );
        }

        const attachment =
          payload.attachment;

        setAttachments(
          (current) => [
            ...current,
            attachment,
          ],
        );

        if (
          !attachment.text?.trim()
          && attachment.kind
          !== "image"
        ) {
          setAttachmentError(
            `${attachment.name} was uploaded, but no text could be extracted.`,
          );
        }

        if (
          attachment.truncated
        ) {
          setAttachmentError(
            `${attachment.name} was extracted, but the text was truncated before being sent to the model.`,
          );
        }

        if (
          attachment.note
        ) {
          setAttachmentError(
            attachment.note,
          );
        }
      }
    }
    catch (
      uploadError
    ) {
      setAttachmentError(
        uploadError
          instanceof Error
          ? uploadError.message
          : "Attachment upload failed.",
      );
    }
    finally {
      setUploadingAttachment(
        false,
      );
    }
  }


  async function detectMemoryFromPrompt(
    promptText: string,
  ) {
    try {
      const memoryResponse =
        await fetch(
          "/api/agent-memory/detect",
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                {
                  text:
                    promptText,
                },
              ),
          },
        );

      const payload =
        (
          await memoryResponse.json()
        ) as {
          ok: boolean;

          suggestion?:
            MemorySuggestion;
        };

      if (
        memoryResponse.ok
        && payload.ok
        && payload
          .suggestion
          ?.is_memory_request
      ) {
        setMemorySuggestion(
          payload.suggestion,
        );

        setMemoryStatusMessage(
          null,
        );
      }
    }
    catch {
      // Memory detection must never block normal chat.
    }
  }


  async function saveMemorySuggestion() {
    if (
      !memorySuggestion
      || memorySuggestion.blocked
      || !memorySuggestion.memory_type
      || !memorySuggestion.memory_key
      || !memorySuggestion.memory_value
    ) {
      return;
    }

    setSavingMemorySuggestion(
      true,
    );

    setMemoryStatusMessage(
      null,
    );

    try {
      const proposeResponse =
        await fetch(
          "/api/agent-memory/propose",
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                {
                  memory_type:
                    memorySuggestion
                      .memory_type,

                  memory_key:
                    memorySuggestion
                      .memory_key,

                  memory_value:
                    memorySuggestion
                      .memory_value,

                  confidence:
                    memorySuggestion
                      .confidence,

                  source:
                    "chat-confirmed",

                  metadata: {
                    created_from:
                      "chat_memory_suggestion",
                  },
                },
              ),
          },
        );

      const proposePayload =
        (
          await proposeResponse.json()
        ) as {
          ok: boolean;

          memory?: {
            id: string;
          };

          error?: string;

          detail?: string;
        };

      if (
        !proposeResponse.ok
        || !proposePayload.ok
        || !proposePayload.memory
      ) {
        throw new Error(
          proposePayload.error
          ?? proposePayload.detail
          ?? "Failed to propose memory.",
        );
      }

      const confirmResponse =
        await fetch(
          "/api/agent-memory/confirm",
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                {
                  memory_id:
                    proposePayload
                      .memory
                      .id,
                },
              ),
          },
        );

      const confirmPayload =
        (
          await confirmResponse.json()
        ) as {
          ok: boolean;

          error?: string;

          detail?: string;
        };

      if (
        !confirmResponse.ok
        || !confirmPayload.ok
      ) {
        throw new Error(
          confirmPayload.error
          ?? confirmPayload.detail
          ?? "Failed to confirm memory.",
        );
      }

      setMemorySuggestion(
        null,
      );

      setMemoryStatusMessage(
        "Preference saved to memory.",
      );
    }
    catch (
      memoryError
    ) {
      setMemoryStatusMessage(
        memoryError
          instanceof Error
          ? memoryError.message
          : "Failed to save memory.",
      );
    }
    finally {
      setSavingMemorySuggestion(
        false,
      );
    }
  }


  function handleRemoveAttachment(
    attachmentId: string,
  ) {
    setAttachments(
      (current) =>
        current.filter(
          (attachment) =>
            attachment.id
            !== attachmentId,
        ),
    );
  }


  function handleClearAttachments() {
    setAttachments([]);

    setAttachmentError(
      null,
    );
  }


  async function handleSubmit() {
    if (
      !prompt.trim()
    ) {
      setError(
        `Add ${currentTaskCopy.primaryLabel.toLowerCase()} before submitting.`,
      );

      return;
    }

    void detectMemoryFromPrompt(
      prompt,
    );

    if (
      task === "qa"
      && !context.trim()
    ) {
      setError(
        "Add context before running Q&A.",
      );

      return;
    }

    setError(
      null,
    );

    setLoading(
      true,
    );

    const activeAttachmentContext =
      buildActiveAttachmentContext(
        attachments,
      );

    const combinedContext = [
      context.trim(),
      activeAttachmentContext.trim(),
    ]
      .filter(Boolean)
      .join("\n\n");

    const historyAttachments =
      toHistoryAttachments(
        attachments,
      );

    try {
      const result =
          await sendFinancePrompt(
            {
              task,

              prompt,

              context:
                combinedContext,

              provider,

              mode,

              accessToken:
                auth?.accessToken,

              temperature,

              maxNewTokens,

              // Phase 3H-F-D
              allowWebFallback,

              trustedWebDomains: [],
            },
          );

      setResponse(
        result,
      );

      const historyEntry =
        makeHistoryEntry(
          result,

          context.trim()
            || undefined,

          historyAttachments.length
            ? historyAttachments
            : undefined,
        );

      appendHistory(
        historyEntry,
      );

      onSaved?.(
        historyEntry,
      );
    }
    catch (
      submitError
    ) {
      setError(
        submitError
          instanceof Error
          ? submitError.message
          : "The request failed.",
      );
    }
    finally {
      setLoading(
        false,
      );
    }
  }


  function handleClear() {
    setPrompt("");

    setContext("");

    setAttachments([]);

    setAttachmentError(
      null,
    );

    setResponse(
      null,
    );

    setError(
      null,
    );
  }


  function handleLoadExample() {
    setPrompt(
      currentTaskCopy.defaultPrompt,
    );

    setContext(
      currentTaskCopy.defaultContext,
    );

    setResponse(
      null,
    );

    setError(
      null,
    );
  }


  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      {memorySuggestion ? (
        <MemorySuggestionCard
          suggestion={
            memorySuggestion
          }
          saving={
            savingMemorySuggestion
          }
          onSave={() =>
            void saveMemorySuggestion()
          }
          onDismiss={() =>
            setMemorySuggestion(
              null,
            )
          }
        />
      ) : null}

      <div className="space-y-4">
        <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">
                Prompt Console
              </p>

              <h2 className="mt-2 text-lg font-semibold text-white">
                Compose finance task
              </h2>

              <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">
                Add finance text, optional context, or attachments.
                The selected provider will run the active task.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <MiniPill tone="cyan">
                {mode === "basic"
                  ? "Basic"
                  : "Premium"}
              </MiniPill>

              <MiniPill tone="emerald">
                {provider.name}
              </MiniPill>

              <MiniPill>
                {provider.modelId}
              </MiniPill>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-3">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                  Finance task
                </p>

                <p className="mt-1 text-xs leading-5 text-slate-400">
                  {currentTaskCopy.helperText}
                </p>
              </div>

              <div className="flex shrink-0 flex-wrap gap-2">
                {(
                  [
                    "summarize",
                    "qa",
                    "risk-analysis",
                  ] as FinanceTask[]
                ).map(
                  (item) => {
                    const isActive =
                      task === item;

                    return (
                      <button
                        key={
                          item
                        }
                        type="button"
                        onClick={() =>
                          onTaskChange(
                            item,
                          )
                        }
                        disabled={
                          loading
                          || memoryDecisionPending
                        }
                        className={[
                          "rounded-xl border px-3 py-2 text-xs font-semibold transition",

                          isActive
                            ? "border-cyan-300/50 bg-cyan-300/15 text-cyan-50"
                            : "border-white/10 bg-white/0 text-slate-300 hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-white",

                          loading
                          || memoryDecisionPending
                            ? "cursor-not-allowed opacity-60"
                            : "",
                        ].join(
                          " ",
                        )}
                      >
                        {getTaskLabel(
                          item,
                        )}
                      </button>
                    );
                  },
                )}
              </div>
            </div>
          </div>

          {/* ===============================================
              Phase 3H-F-D
              Explicit web fallback permission
              =============================================== */}

          <div className="mt-4">
            <WebFallbackToggle
              enabled={
                allowWebFallback
              }
              disabled={
                loading
                || memoryDecisionPending
              }
              onChange={
                setAllowWebFallback
              }
            />
          </div>

          {memoryStatusMessage ? (
            <p className="mt-4 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              {memoryStatusMessage}
            </p>
          ) : null}

          <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.55fr)]">
            <label className="block space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-semibold text-slate-200">
                  {currentTaskCopy.primaryLabel}
                </span>

                <MiniPill tone="amber">
                  Required
                </MiniPill>
              </div>

              <textarea
                value={
                  prompt
                }
                onChange={(
                  event,
                ) =>
                  setPrompt(
                    event.target.value,
                  )
                }
                rows={
                  8
                }
                disabled={
                  memoryDecisionPending
                }
                className="min-h-[260px] w-full rounded-2xl border border-white/10 bg-black/25 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60"
                placeholder={
                  currentTaskCopy.primaryPlaceholder
                }
              />
            </label>

            <div className="space-y-4">
              <label className="block space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-200">
                    {currentTaskCopy.secondaryLabel}
                  </span>

                  <MiniPill
                    tone={
                      task === "qa"
                        ? "amber"
                        : "slate"
                    }
                  >
                    {task === "qa"
                      ? "Required"
                      : "Optional"}
                  </MiniPill>
                </div>

                <textarea
                  value={
                    context
                  }
                  onChange={(
                    event,
                  ) =>
                    setContext(
                      event.target.value,
                    )
                  }
                  rows={
                    6
                  }
                  disabled={
                    memoryDecisionPending
                  }
                  className="min-h-[145px] w-full rounded-2xl border border-white/10 bg-black/25 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60"
                  placeholder={
                    currentTaskCopy.secondaryPlaceholder
                  }
                />
              </label>

              <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                      Attachments
                    </p>

                    <p className="mt-1 text-xs leading-5 text-slate-400">
                      PDF, DOCX, TXT, MD, CSV, or images.
                    </p>
                  </div>

                  <label className="cursor-pointer rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-3 py-2 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-300/20">
                    {uploadingAttachment
                      ? "Extracting..."
                      : "Attach"}

                    <input
                      type="file"
                      multiple
                      accept=".pdf,.docx,.txt,.md,.csv,.png,.jpg,.jpeg,.webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,text/csv,image/png,image/jpeg,image/webp"
                      className="hidden"
                      disabled={
                        uploadingAttachment
                        || memoryDecisionPending
                        || loading
                      }
                      onChange={(
                        event,
                      ) => {
                        void handleAttachmentUpload(
                          event.target.files,
                        );

                        event.currentTarget.value =
                          "";
                      }}
                    />
                  </label>
                </div>

                {attachments.length ? (
                  <div className="mt-3 space-y-2">
                    {attachments.map(
                      (
                        attachment,
                      ) => (
                        <div
                          key={
                            attachment.id
                          }
                          className="flex items-start justify-between gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-xs font-semibold text-white">
                              {attachment.name}
                            </p>

                            <p className="mt-1 text-[11px] text-slate-400">
                              {attachment.kind.toUpperCase()}
                              {" · "}
                              {formatFileSize(
                                attachment.size,
                              )}

                              {attachment.pageCount
                                ? ` · ${attachment.pageCount} pages`
                                : ""}

                              {attachment.truncated
                                ? " · truncated"
                                : ""}
                            </p>
                          </div>

                          <button
                            type="button"
                            disabled={
                              loading
                            }
                            onClick={() =>
                              handleRemoveAttachment(
                                attachment.id,
                              )
                            }
                            className="shrink-0 text-[11px] font-semibold text-slate-400 transition hover:text-rose-200 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Remove
                          </button>
                        </div>
                      ),
                    )}

                    <button
                      type="button"
                      onClick={
                        handleClearAttachments
                      }
                      disabled={
                        loading
                      }
                      className="text-[11px] font-semibold text-slate-400 transition hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Clear all attachments
                    </button>
                  </div>
                ) : null}

                {attachmentError ? (
                  <p className="mt-3 rounded-xl border border-amber-300/30 bg-amber-300/10 px-3 py-2 text-xs leading-5 text-amber-100">
                    {attachmentError}
                  </p>
                ) : null}
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-3">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Temperature
                  </span>

                  <span className="text-xs font-semibold text-white">
                    {temperature.toFixed(
                      2,
                    )}
                  </span>
                </div>

                <input
                  type="range"
                  min="0"
                  max="1.5"
                  step="0.05"
                  value={
                    temperature
                  }
                  disabled={
                    loading
                  }
                  onChange={(
                    event,
                  ) =>
                    setTemperature(
                      Number(
                        event.target.value,
                      ),
                    )
                  }
                  className="w-full accent-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </label>

              <label className="block space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Max tokens
                  </span>

                  <span className="text-xs font-semibold text-white">
                    {maxNewTokens}
                  </span>
                </div>

                <input
                  type="range"
                  min="32"
                  max="1024"
                  step="32"
                  value={
                    maxNewTokens
                  }
                  disabled={
                    loading
                  }
                  onChange={(
                    event,
                  ) =>
                    setMaxNewTokens(
                      Number(
                        event.target.value,
                      ),
                    )
                  }
                  className="w-full accent-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </label>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() =>
                void handleSubmit()
              }
              disabled={
                loading
                || memoryDecisionPending
              }
              className="rounded-xl bg-gradient-to-r from-cyan-400 to-sky-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading
                ? "Running..."
                : currentTaskCopy.runLabel}
            </button>

            <button
              type="button"
              onClick={
                handleLoadExample
              }
              disabled={
                loading
                || memoryDecisionPending
              }
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-70"
            >
              Example
            </button>

            <button
              type="button"
              onClick={
                handleClear
              }
              disabled={
                loading
                || memoryDecisionPending
              }
              className="rounded-xl border border-white/10 bg-white/0 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white disabled:cursor-not-allowed disabled:opacity-70"
            >
              Clear
            </button>

            <button
              type="button"
              onClick={() => {
                onModeChange(
                  mode,
                );

                onTaskChange(
                  task,
                );

                onProviderChange(
                  provider.id,
                );
              }}
              disabled={
                loading
                || memoryDecisionPending
              }
              className="rounded-xl border border-white/10 bg-white/0 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white disabled:cursor-not-allowed disabled:opacity-70"
            >
              Keep settings
            </button>
          </div>

          {error ? (
            <p className="mt-4 rounded-xl border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">
              {error}
            </p>
          ) : null}
        </div>
      </div>

      <aside className="space-y-4">
        <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">
            Output
          </p>

          {/* Phase 3H-F-D
            Show whether public web fallback was actually used.
        */}


          {response ? (
            <div className="mt-3">

              {response.web_fallback_used ? (
                <div className="mb-3 rounded-xl border border-cyan-300/20 bg-cyan-300/[0.05] px-3 py-2">
                  <p className="text-xs font-medium text-cyan-100">
                    Public web evidence was used because the
                    available local evidence was insufficient.
                  </p>
                </div>
              ) : null}

              {response.web_fallback_available &&
              !allowWebFallback ? (
                <div className="mb-3 rounded-xl border border-amber-300/20 bg-amber-300/[0.05] px-3 py-2">
                  <p className="text-xs font-medium text-amber-100">
                    The available evidence appears incomplete.
                    Enable public web fallback to search external
                    sources.
                  </p>
                </div>
              ) : null}

              <ResponseCard
                response={response}
              />

              {response.web_research ? (
                <div className="mt-3">
                  <WebSourcePanel research={response.web_research} />
                </div>
              ) : null}

            </div>
          ) : (
            <div className="mt-3 rounded-2xl border border-white/10 bg-black/20 p-4">
              <h3 className="text-lg font-semibold text-white">
                Waiting for the first run
              </h3>

              <p className="mt-2 text-sm leading-6 text-slate-400">
                Generated summaries, answers, risk analysis,
                token usage, and latency metadata will appear
                here.
              </p>
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
            Current route
          </p>

          <div className="mt-3 space-y-3">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
              <p className="text-xs text-slate-400">
                Endpoint
              </p>

              <p className="mt-1 text-sm font-semibold text-white">
                {currentTaskCopy.route}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
              <p className="text-xs text-slate-400">
                Provider
              </p>

              <p className="mt-1 text-sm font-semibold text-white">
                {mode === "basic"
                  ? "Basic"
                  : "Premium"}
                {" · "}
                {provider.name}
              </p>

              <p className="mt-1 truncate text-xs text-slate-500">
                {provider.modelId}
              </p>
            </div>

            {/* ============================================
                Phase 3H-F-D
                Current web permission state
                ============================================ */}

            <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
              <p className="text-xs text-slate-400">
                Public web fallback
              </p>

              <div className="mt-2">
                <MiniPill
                  tone={
                    allowWebFallback
                      ? "cyan"
                      : "slate"
                  }
                >
                  {allowWebFallback
                    ? "Enabled if needed"
                    : "Disabled"}
                </MiniPill>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <MiniPill>
                {provider.costClass}
              </MiniPill>

              <MiniPill>
                {provider.privacy}
              </MiniPill>

              <MiniPill>
                {provider.latency}
              </MiniPill>
            </div>
          </div>
        </div>
      </aside>
    </section>
  );
}