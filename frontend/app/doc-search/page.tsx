"use client";

import {
  ChangeEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import type { AuthState, FinanceTask } from "@/types";
import { AppTopMenu } from "@/components/AppTopMenu";
import { WebFallbackToggle } from "@/components/WebFallbackToggle";
import { CitedAnswer } from "@/components/CitedAnswer";
import { RetrievedSourcesPanel } from "@/components/RetrievedSourcesPanel";
import { WebSourcePanel } from "@/components/WebSourcePanel";
import type { PublicWebResearchSummary } from "@/lib/api";

type StoredDocument = {
  id: string;
  userId: string;
  fileName: string;
  fileType: string;
  kind: "pdf" | "docx" | "text" | "csv" | "image" | "unknown";
  size: number;
  pageCount?: number;
  chunkCount: number;
  extractedChars: number;
  embeddingModel: string;
  storageProfile: string;
  createdAt: string;
};

type RetrievedSource = {
  documentId: string;
  chunkId: string;
  fileName: string;
  chunkIndex: number;
  pageNumber?: number;
  score: number;
  snippet: string;
};

type RagAnswer = {
  id?: string;
  request_id?: string;
  provider?: string;
  model_id?: string;
  output?: string;
  latency_ms?: number;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  };
};

type RagQueryResponse = {
  ok: boolean;
  request_id?: string;
  answer?: RagAnswer;
  sources?: RetrievedSource[];
  retrieval?: {
    topK?: number;
    bestScore?: number;
    embeddingModel?: string;
    usage?: {
      prompt_tokens?: number;
      total_tokens?: number;
    };
  };
  error?: string;
};

type AgentDocumentSource = {
  document_id?: string;
  chunk_id?: string;
  file_name?: string;
  chunk_index?: number;
  page_number?: number | null;
  score?: number;
  snippet?: string;
};

type AgentToolResult = {
  tool_name?: string;
  status?: string;
  output?: {
    sources?: AgentDocumentSource[];
  };
};

type AgentAnalyzeResponse = {
  ok: boolean;
  request_id?: string;
  answer?: string;
  model?: string;
  web_fallback_used?: boolean;
  web_fallback_available?: boolean;
  web_fallback_reason?: string | null;
  web_research?: PublicWebResearchSummary | null;
  tool_results?: AgentToolResult[];
  error?: string;
  detail?: string;
};

type DocumentStorageProfile =
  | "session"
  | "local-json"
  | "local-sqlite"
  | "supabase-pgvector"
  | "aws"
  | "export-import";

type RagStorageConfig = {
  profile: DocumentStorageProfile;
  originalFileStorage: string;
  vectorStorage: string;
  metadataStorage: string;
  historyStorage: string;
  storeOriginalFiles: boolean;
  embeddingProvider: string;
  embeddingModel: string;
  chunkSizeChars: number;
  chunkOverlapChars: number;
  retrievalTopK: number;
  maxIndexedChars: number;
  updatedAt: string;
};

type DisabledProfile = {
  profile: DocumentStorageProfile;
  label: string;
  reason: string;
};

const providerOptions = [
  {
    id: "openai-premium",
    name: "OpenAI Premium",
    description: "Recommended for document-grounded finance analysis.",
  },
  {
    id: "claude-premium",
    name: "Claude Premium",
    description: "Useful for long narrative finance documents if configured.",
  },
  {
    id: "gemini-premium",
    name: "Gemini Premium",
    description: "Useful for long-context experiments if configured.",
  },
];

const taskOptions: Array<{
  id: FinanceTask;
  name: string;
  description: string;
}> = [
  {
    id: "qa",
    name: "Q&A",
    description: "Ask direct questions over selected indexed documents.",
  },
  {
    id: "summarize",
    name: "Summarize",
    description: "Summarize retrieved evidence from selected documents.",
  },
  {
    id: "risk-analysis",
    name: "Risk Analysis",
    description: "Find financial, operational, liquidity, and disclosure risks.",
  },
];

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatKind(kind: StoredDocument["kind"]) {
  if (kind === "pdf") return "PDF";
  if (kind === "docx") return "DOCX";
  if (kind === "text") return "TEXT";
  if (kind === "csv") return "CSV";
  if (kind === "image") return "IMAGE";
  return "UNKNOWN";
}

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function profileLabel(profile?: DocumentStorageProfile | null) {
  if (profile === "session") return "Session only";
  if (profile === "local-json") return "Local project";
  if (profile === "local-sqlite") return "Local SQLite";
  if (profile === "supabase-pgvector") return "Supabase pgvector";
  if (profile === "aws") return "AWS";
  if (profile === "export-import") return "Export/import";
  return "Loading";
}

function extractAgentDocumentSources(
  payload: AgentAnalyzeResponse,
): RetrievedSource[] {
  const rawSources = payload.tool_results?.find(
    (result) =>
      result.tool_name === "document_search" &&
      result.status === "completed",
  )?.output?.sources ?? [];

  return rawSources.flatMap((source) => {
    if (
      typeof source.document_id !== "string" ||
      typeof source.chunk_id !== "string" ||
      typeof source.file_name !== "string" ||
      typeof source.chunk_index !== "number" ||
      typeof source.score !== "number" ||
      typeof source.snippet !== "string"
    ) {
      return [];
    }

    return [{
      documentId: source.document_id,
      chunkId: source.chunk_id,
      fileName: source.file_name,
      chunkIndex: source.chunk_index,
      pageNumber:
        typeof source.page_number === "number"
          ? source.page_number
          : undefined,
      score: source.score,
      snippet: source.snippet,
    }];
  });
}

export default function DocSearchPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [auth, setAuth] = useState<AuthState | null>(null);
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [providerId, setProviderId] = useState("openai-premium");
  const [task, setTask] = useState<FinanceTask>("qa");
  const [allowWebFallback, setAllowWebFallback] = useState(false);
  const [question, setQuestion] = useState(
    "What are the main financial risks in the selected document?",
  );
  const [topK, setTopK] = useState(6);

  const [indexing, setIndexing] = useState(false);
  const [querying, setQuerying] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const [answer, setAnswer] = useState<RagAnswer | null>(null);
  const [sources, setSources] = useState<RetrievedSource[]>([]);
  const [webResearch, setWebResearch] =
    useState<PublicWebResearchSummary | null>(null);
  const [latestRequestId, setLatestRequestId] = useState<string | null>(null);

  const [ragConfig, setRagConfig] = useState<RagStorageConfig | null>(null);
  const [disabledProfiles, setDisabledProfiles] = useState<DisabledProfile[]>(
    [],
  );
  const [savingConfig, setSavingConfig] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [pendingProfile, setPendingProfile] =
    useState<DocumentStorageProfile>("local-json");

  const selectedDocuments = useMemo(
    () =>
      documents.filter((document) =>
        selectedDocumentIds.includes(document.id),
      ),
    [documents, selectedDocumentIds],
  );

  const webFallbackUsed = Boolean(webResearch?.used);

  function clearSelectedFile() {
    setSelectedFile(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  useEffect(() => {
    setAuth(loadAuth());
    void loadDocuments();
    void loadRagConfig();
  }, []);

  useEffect(() => {
    if (!isConfigOpen) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPendingProfile(ragConfig?.profile ?? "local-json");
        setIsConfigOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isConfigOpen, ragConfig?.profile]);

  async function loadDocuments() {
    setLoadingDocuments(true);
    setError(null);

    try {
      const response = await fetch("/api/documents/list", {
        cache: "no-store",
      });
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to load indexed documents.");
      }

      const nextDocuments = (payload.documents ?? []) as StoredDocument[];
      setDocuments(nextDocuments);

      setSelectedDocumentIds((current) => {
        const availableIds = new Set(nextDocuments.map((item) => item.id));
        const stillAvailable = current.filter((id) => availableIds.has(id));

        if (stillAvailable.length) {
          return stillAvailable;
        }

        return nextDocuments[0]?.id ? [nextDocuments[0].id] : [];
      });
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load indexed documents.",
      );
    } finally {
      setLoadingDocuments(false);
    }
  }

  async function loadRagConfig() {
    try {
      const response = await fetch("/api/documents/config", {
        cache: "no-store",
      });
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to load RAG configuration.");
      }

      setRagConfig(payload.config);
      setPendingProfile(payload.config.profile);
      setDisabledProfiles(payload.disabledProfiles ?? []);
    } catch (configError) {
      setError(
        configError instanceof Error
          ? configError.message
          : "Failed to load RAG configuration.",
      );
    }
  }

  function openConfigDialog() {
    setPendingProfile(ragConfig?.profile ?? "local-json");
    setIsConfigOpen(true);
  }

  async function handleChangeStorageProfile(profile: DocumentStorageProfile) {
    if (profile === ragConfig?.profile) {
      setStatusMessage(`${profileLabel(profile)} is already active.`);
      return;
    }

    setSavingConfig(true);
    setPendingProfile(profile);
    setError(null);
    setStatusMessage(
      `Switching document memory to ${profileLabel(profile)}...`,
    );

    try {
      const response = await fetch("/api/documents/config", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ profile }),
      });

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to update RAG configuration.");
      }

      setRagConfig(payload.config);
      setPendingProfile(payload.config.profile);

      const warnings = Array.isArray(payload.warnings) ? payload.warnings : [];

      setStatusMessage(
        warnings.length
          ? `Storage updated to ${profileLabel(
              payload.config.profile,
            )}. ${warnings.join(" ")}`
          : `Storage updated to ${profileLabel(payload.config.profile)}.`,
      );

      await loadDocuments();
    } catch (configError) {
      setError(
        configError instanceof Error
          ? configError.message
          : "Failed to update RAG configuration.",
      );
    } finally {
      setSavingConfig(false);
    }
  }

  async function handleSaveConfigDialog() {
    await handleChangeStorageProfile(pendingProfile);
    setIsConfigOpen(false);
  }

  async function handleClearDocumentMemory() {
    const confirmed = window.confirm(
      "Clear all document memory for this user? This removes indexed documents, chunks, and vectors. Original files are not stored.",
    );

    if (!confirmed) return;

    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/documents/clear", {
        method: "DELETE",
      });

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to clear document memory.");
      }

      setDocuments([]);
      setSelectedDocumentIds([]);
      setAnswer(null);
      setSources([]);
      clearSelectedFile();
      setStatusMessage("All document memory was cleared.");
    } catch (clearError) {
      setError(
        clearError instanceof Error
          ? clearError.message
          : "Failed to clear document memory.",
      );
    }
  }

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setError(null);
    setStatusMessage(null);
  }

  function toggleDocument(documentId: string) {
    setSelectedDocumentIds((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId],
    );
  }

  async function handleUploadAndIndex() {
    if (!selectedFile) {
      setError("Choose a PDF, DOCX, TXT, MD, or CSV file first.");
      return;
    }

    setIndexing(true);
    setError(null);
    setStatusMessage(`Indexing ${selectedFile.name}...`);
    setAnswer(null);
    setSources([]);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch("/api/documents/upload", {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Document indexing failed.");
      }

      const indexedDocument = payload.document as StoredDocument;

      setStatusMessage(
        `${indexedDocument.fileName} indexed with ${indexedDocument.chunkCount} chunks and ${payload.vectorsIndexed} vectors.`,
      );

      setSelectedDocumentIds((current) => [
        indexedDocument.id,
        ...current.filter((id) => id !== indexedDocument.id),
      ]);

      await loadDocuments();
      clearSelectedFile();
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Document indexing failed.",
      );
    } finally {
      setIndexing(false);
    }
  }

  async function handleDeleteDocument(documentId: string) {
    const target = documents.find((document) => document.id === documentId);

    const confirmed = window.confirm(
      `Delete ${
        target?.fileName ?? "this document"
      } from document memory? This removes metadata, chunks, and vectors.`,
    );

    if (!confirmed) return;

    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/documents/delete", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ documentId }),
      });

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Document deletion failed.");
      }

      setSelectedDocumentIds((current) =>
        current.filter((id) => id !== documentId),
      );

      clearSelectedFile();
      setStatusMessage("Document memory deleted.");
      await loadDocuments();
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Document deletion failed.",
      );
    }
  }

  async function handleAskQuestion() {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      setError("Enter a question before running document search.");
      return;
    }

    if (!selectedDocumentIds.length) {
      setError("Select at least one indexed document.");
      return;
    }

    setQuerying(true);
    setError(null);
    setStatusMessage("Retrieving relevant chunks and asking the model...");
    setAnswer(null);
    setSources([]);
    setWebResearch(null);
    setLatestRequestId(null);

    try {
      const endpoint = allowWebFallback
        ? "/api/agents/analyze"
        : "/api/documents/query";
      const requestBody = allowWebFallback
        ? {
            question: trimmedQuestion,
            provider_id: providerId,
            use_documents: true,
            document_ids: selectedDocumentIds,
            top_k: topK,
            allow_web_fallback: true,
            trusted_web_domains: [],
          }
        : {
            question: trimmedQuestion,
            task,
            providerId,
            documentIds: selectedDocumentIds,
            topK,
          };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (allowWebFallback) {
        const payload =
          (await response.json()) as AgentAnalyzeResponse;

        if (!response.ok || !payload.ok) {
          throw new Error(
            payload.error ?? payload.detail ?? "Agent analysis failed.",
          );
        }

        setAnswer({
          output: payload.answer ?? "",
          provider: "openai",
          model_id: payload.model ?? "",
          request_id: payload.request_id,
        });
        setSources(extractAgentDocumentSources(payload));
        setWebResearch(payload.web_research ?? null);
        setLatestRequestId(payload.request_id ?? null);
        setStatusMessage(
          payload.web_fallback_used
            ? "Local document evidence was insufficient. Public web evidence was used."
            : "The answer was produced from the available local evidence.",
        );
        return;
      }

      const payload = (await response.json()) as RagQueryResponse;

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "RAG query failed.");
      }

      setAnswer(payload.answer ?? null);
      setSources(payload.sources ?? []);
      setWebResearch(null);
      setLatestRequestId(payload.request_id ?? null);

      const bestScore = payload.retrieval?.bestScore;

      setStatusMessage(
        `Retrieved ${(payload.sources ?? []).length} source chunk${
          (payload.sources ?? []).length === 1 ? "" : "s"
        } using ${
          payload.retrieval?.embeddingModel ?? "the configured embedding model"
        }.${
          typeof bestScore === "number" && bestScore < 0.3
            ? " Low retrieval confidence: review the source snippets."
            : ""
        }`,
      );
    } catch (queryError) {
      setError(
        queryError instanceof Error ? queryError.message : "RAG query failed.",
      );
    } finally {
      setQuerying(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar
          displayName={getDisplayName(auth)}
          mode="premium"
          onLogout={handleLogout}
        />

        <AppTopMenu />

        <div className="mx-auto w-full max-w-7xl space-y-4 px-3 pb-8">
          <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-xl shadow-black/20">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs uppercase tracking-[0.24em] text-emerald-200/70">
                  Doc Intelligent Search
                </p>

                <h1 className="mt-2 text-2xl font-semibold text-white">
                  Search and analyze finance documents
                </h1>

                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Upload reports, statements, PDFs, and CSVs. Ask grounded
                  questions using vector search, retrieved source snippets, and
                  provider-routed premium models.
                </p>

                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 font-semibold text-emerald-100">
                    RAG active
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                    {profileLabel(ragConfig?.profile)}
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                    Files not stored
                  </span>
                </div>
              </div>

              <div className="flex shrink-0 gap-3">
                <button
                  type="button"
                  onClick={openConfigDialog}
                  className="rounded-xl border border-lime-300/20 bg-lime-300/10 px-4 py-2.5 text-sm font-semibold text-lime-50 transition hover:border-lime-200/40 hover:bg-lime-300/20"
                >
                  Configure
                </button>

                <button
                  type="button"
                  onClick={loadDocuments}
                  disabled={loadingDocuments}
                  className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loadingDocuments ? "Refreshing..." : "Refresh"}
                </button>
              </div>
            </div>
          </section>

          {error ? (
            <div className="rounded-2xl border border-rose-300/20 bg-rose-300/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          {statusMessage && !webFallbackUsed ? (
            <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 px-4 py-3 text-sm text-cyan-100">
              {statusMessage}
            </div>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-[390px_minmax(0,1fr)]">
            <section className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">
                    Document Library
                  </p>
                  <h2 className="mt-2 text-lg font-semibold text-white">
                    Upload and index
                  </h2>
                  <p className="mt-1 text-xs leading-5 text-slate-400">
                    Stores chunks and vectors in the selected memory profile.
                    Original files are not persisted.
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,.md,.csv,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,text/csv"
                  onChange={handleFileChange}
                  className="block w-full text-xs text-slate-300 file:mr-3 file:rounded-xl file:border-0 file:bg-cyan-300/10 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-cyan-100 hover:file:bg-cyan-300/20"
                />

                {selectedFile ? (
                  <p className="mt-2 truncate text-xs text-slate-400">
                    <span className="font-semibold text-slate-200">
                      {selectedFile.name}
                    </span>{" "}
                    · {formatFileSize(selectedFile.size)}
                  </p>
                ) : null}

                <button
                  type="button"
                  onClick={handleUploadAndIndex}
                  disabled={indexing || !selectedFile}
                  className="mt-3 w-full rounded-xl bg-cyan-300 px-3 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {indexing ? "Indexing..." : "Upload and index"}
                </button>
              </div>

              <div className="mt-4 space-y-2">
                {documents.length ? (
                  documents.map((document) => {
                    const selected = selectedDocumentIds.includes(document.id);

                    return (
                      <div
                        key={document.id}
                        className={`rounded-2xl border p-3 transition ${
                          selected
                            ? "border-emerald-300/30 bg-emerald-300/10"
                            : "border-white/10 bg-black/20 hover:border-white/20"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={() => toggleDocument(document.id)}
                            className="mt-1 h-4 w-4 rounded border-white/20 bg-black"
                          />

                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold text-white">
                              {document.fileName}
                            </p>

                            <p className="mt-1 text-[11px] leading-5 text-slate-400">
                              {formatKind(document.kind)} ·{" "}
                              {formatFileSize(document.size)} ·{" "}
                              {document.chunkCount} chunks
                              {document.pageCount
                                ? ` · ${document.pageCount} pages`
                                : ""}
                            </p>

                            <p className="mt-1 truncate text-[11px] text-slate-500">
                              {profileLabel(
                                document.storageProfile as DocumentStorageProfile,
                              )}{" "}
                              · {formatDate(document.createdAt)}
                            </p>
                          </div>

                          <button
                            type="button"
                            onClick={() => handleDeleteDocument(document.id)}
                            className="rounded-lg border border-white/10 px-2.5 py-1 text-[11px] font-medium text-slate-400 transition hover:border-rose-300/30 hover:bg-rose-300/10 hover:text-rose-100"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-400">
                    No indexed documents yet. Upload a document to create
                    chunks and embeddings.
                  </div>
                )}
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
                <p className="text-xs uppercase tracking-[0.2em] text-emerald-200/70">
                  Ask Documents
                </p>
                <h2 className="mt-2 text-lg font-semibold text-white">
                  Query selected memory
                </h2>

                <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_120px]">
                  <label className="space-y-1.5">
                    <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                      Provider
                    </span>
                    <select
                      value={providerId}
                      onChange={(event) => setProviderId(event.target.value)}
                      className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none transition focus:border-cyan-300/40"
                    >
                      {providerOptions.map((provider) => (
                        <option key={provider.id} value={provider.id}>
                          {provider.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-1.5">
                    <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                      Task
                    </span>
                    <select
                      value={task}
                      onChange={(event) =>
                        setTask(event.target.value as FinanceTask)
                      }
                      className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none transition focus:border-cyan-300/40"
                    >
                      {taskOptions.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-1.5">
                    <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                      Top-K
                    </span>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={topK}
                      onChange={(event) =>
                        setTopK(Number(event.target.value) || 6)
                      }
                      className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none transition focus:border-cyan-300/40"
                    />
                  </label>
                </div>

                <label className="mt-4 block space-y-1.5">
                  <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                    Question
                  </span>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    rows={4}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/40"
                    placeholder="Ask a question over selected indexed documents..."
                  />
                </label>

                <div className="mt-4">
                  <WebFallbackToggle
                    enabled={allowWebFallback}
                    disabled={querying}
                    onChange={setAllowWebFallback}
                  />
                </div>

                <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                    Selected documents
                  </p>
                  {selectedDocuments.length ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {selectedDocuments.map((document) => (
                        <span
                          key={document.id}
                          className="max-w-full truncate rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs font-medium text-emerald-100"
                        >
                          {document.fileName}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-slate-400">
                      No documents selected.
                    </p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleAskQuestion}
                  disabled={querying || !selectedDocumentIds.length}
                  className="mt-4 w-full rounded-xl bg-emerald-300 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {querying ? "Searching..." : "Ask selected documents"}
                </button>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-white/10 bg-slate-950/75 p-4 shadow-lg shadow-black/10">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200/70">
                      Answer
                    </p>
                    {webFallbackUsed ? (
                      <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[10px] font-semibold text-cyan-100">
                        Web-assisted
                      </span>
                    ) : null}
                  </div>

                  {answer?.output ? (
                    <div className="mt-3">
                      {webFallbackUsed ? (
                        <div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.04] p-3">
                          <p className="text-sm font-semibold text-white">
                            Uploaded document evidence was insufficient
                          </p>
                          <p className="mt-1 text-xs leading-5 text-slate-400">
                            The uploaded document did not contain enough evidence
                            for the requested period or metric. Web fallback found
                            the following relevant external evidence.
                          </p>
                        </div>
                      ) : null}

                      {webFallbackUsed ? (
                        <details className="group mt-3 rounded-xl border border-white/10 bg-black/20">
                          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2.5">
                            <span className="text-xs font-semibold text-slate-300">
                              Show full generated answer
                            </span>
                            <span className="text-sm text-slate-500 transition-transform group-open:rotate-180">
                              ▾
                            </span>
                          </summary>
                          <div className="border-t border-white/10 p-3">
                            <CitedAnswer
                              text={answer.output ?? ""}
                              citations={webResearch?.citations ?? []}
                            />
                          </div>
                        </details>
                      ) : (
                        <CitedAnswer text={answer.output ?? ""} citations={[]} />
                      )}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm text-slate-400">
                      Ask a question to generate a grounded answer.
                    </p>
                  )}
                </div>

                {webFallbackUsed && webResearch ? (
                  <WebSourcePanel research={webResearch} />
                ) : null}

                <RetrievedSourcesPanel
                  sources={sources}
                  defaultOpen={!webFallbackUsed}
                />

                {!webFallbackUsed && webResearch ? (
                  <WebSourcePanel research={webResearch} />
                ) : null}
              </div>
            </section>
          </div>
        </div>
      </div>

      {isConfigOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 py-8 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-slate-700 bg-slate-950 p-5 shadow-2xl shadow-black/60">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-lime-300/80">
                  Configuration
                </p>
                <h2 className="mt-2 text-xl font-semibold text-slate-50">
                  Document memory
                </h2>
                <p className="mt-1 text-sm text-slate-400">
                  Choose where document chunks and vectors should live.
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setPendingProfile(ragConfig?.profile ?? "local-json");
                  setIsConfigOpen(false);
                }}
                className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300 transition hover:border-slate-400 hover:text-white"
              >
                Esc
              </button>
            </div>

            <div className="mt-5 space-y-4">
              <label className="block">
                <span className="text-sm font-semibold text-slate-200">
                  Storage profile
                </span>

                <select
                  value={pendingProfile}
                  onChange={(event) =>
                    setPendingProfile(
                      event.target.value as DocumentStorageProfile,
                    )
                  }
                  disabled={savingConfig}
                  className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm font-semibold text-slate-100 outline-none transition focus:border-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <option value="local-json">Local project storage</option>
                  <option value="session">Session only</option>
                  <option value="supabase-pgvector">Supabase pgvector</option>
                </select>
              </label>

              <div className="grid gap-3 md:grid-cols-3">
                <button
                  type="button"
                  onClick={() => setPendingProfile("local-json")}
                  disabled={savingConfig}
                  className={`rounded-2xl border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                    pendingProfile === "local-json"
                      ? "border-cyan-300/70 bg-cyan-300/10"
                      : "border-slate-800 bg-slate-900/70 hover:border-slate-500"
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-100">
                    Local
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-400">
                    Project-local JSON memory.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setPendingProfile("session")}
                  disabled={savingConfig}
                  className={`rounded-2xl border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                    pendingProfile === "session"
                      ? "border-cyan-300/70 bg-cyan-300/10"
                      : "border-slate-800 bg-slate-900/70 hover:border-slate-500"
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-100">
                    Session
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-400">
                    Temporary privacy-first profile.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setPendingProfile("supabase-pgvector")}
                  disabled={savingConfig}
                  className={`rounded-2xl border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                    pendingProfile === "supabase-pgvector"
                      ? "border-lime-300/70 bg-lime-300/10"
                      : "border-slate-800 bg-slate-900/70 hover:border-slate-500"
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-100">
                    Supabase
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-400">
                    Cloud Postgres + pgvector.
                  </p>
                </button>
              </div>

              <details className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
                <summary className="cursor-pointer text-sm font-semibold text-slate-200">
                  Advanced storage layers
                </summary>

                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                      Original files
                    </p>
                    <p className="mt-1 text-sm text-slate-300">
                      {ragConfig?.originalFileStorage ?? "none"}
                    </p>
                  </div>

                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                      Vector storage
                    </p>
                    <p className="mt-1 text-sm text-slate-300">
                      {ragConfig?.vectorStorage ?? "local-json"}
                    </p>
                  </div>

                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                      Metadata storage
                    </p>
                    <p className="mt-1 text-sm text-slate-300">
                      {ragConfig?.metadataStorage ?? "local-json"}
                    </p>
                  </div>

                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                      History storage
                    </p>
                    <p className="mt-1 text-sm text-slate-300">
                      {ragConfig?.historyStorage ?? "browser-local"}
                    </p>
                  </div>

                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                      Embedding
                    </p>
                    <p className="mt-1 text-sm text-slate-300">
                      {ragConfig?.embeddingModel ?? "text-embedding-3-small"}
                    </p>
                  </div>

                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                      Retrieval top-K
                    </p>
                    <p className="mt-1 text-sm text-slate-300">
                      {ragConfig?.retrievalTopK ?? 6}
                    </p>
                  </div>
                </div>
              </details>

              {disabledProfiles.length ? (
                <details className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
                  <summary className="cursor-pointer text-sm font-semibold text-slate-200">
                    Coming later
                  </summary>

                  <div className="mt-3 space-y-2">
                    {disabledProfiles.map((item) => (
                      <div
                        key={item.profile}
                        className="rounded-xl border border-white/10 bg-white/5 p-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-slate-200">
                            {item.label}
                          </p>
                          <span className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                            Disabled
                          </span>
                        </div>
                        <p className="mt-1 text-xs leading-5 text-slate-500">
                          {item.reason}
                        </p>
                      </div>
                    ))}
                  </div>
                </details>
              ) : null}

              <button
                type="button"
                onClick={handleClearDocumentMemory}
                className="w-full rounded-xl border border-rose-300/30 bg-rose-300/10 px-4 py-2.5 text-sm font-semibold text-rose-100 transition hover:bg-rose-300/20"
              >
                Clear all document memory
              </button>
            </div>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => {
                  setPendingProfile(ragConfig?.profile ?? "local-json");
                  setIsConfigOpen(false);
                }}
                className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-semibold text-slate-300 transition hover:border-slate-400 hover:text-white"
              >
                Cancel
              </button>

              <button
                type="button"
                disabled={savingConfig}
                onClick={handleSaveConfigDialog}
                className="rounded-xl bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {savingConfig ? "Saving..." : "Save changes"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}