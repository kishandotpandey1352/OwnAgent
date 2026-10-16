"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  DocumentFinancialFactsResponse,
  FinancialFact,
  FinancialFactSource,
  FinancialFactStatus,
} from "@/lib/financial-facts";


type Props = {
  documentId: string;
};


const STATUS_OPTIONS: Array<{
  value: FinancialFactStatus;
  label: string;
}> = [
  {
    value: "validated",
    label: "Validated",
  },
  {
    value: "conflict",
    label: "Conflicts",
  },
  {
    value: "rejected",
    label: "Rejected",
  },
  {
    value: "all",
    label: "All",
  },
];


function formatScore(
  value: number | null,
) {
  if (value == null) {
    return "—";
  }

  return `${Math.round(
    value * 100,
  )}%`;
}


function displayValue(
  fact: FinancialFact,
) {
  if (fact.raw_value) {
    return fact.raw_value;
  }

  if (
    fact.normalized_numeric_value
  ) {
    return (
      fact.normalized_numeric_value
    );
  }

  if (fact.numeric_value) {
    return fact.numeric_value;
  }

  if (fact.text_value) {
    return fact.text_value;
  }

  return "—";
}


function statusClass(
  status: string,
) {
  switch (status) {
    case "validated":
      return (
        "bg-emerald-50 " +
        "text-emerald-700 " +
        "border-emerald-200"
      );

    case "conflict":
      return (
        "bg-amber-50 " +
        "text-amber-700 " +
        "border-amber-200"
      );

    case "rejected":
      return (
        "bg-red-50 " +
        "text-red-700 " +
        "border-red-200"
      );

    default:
      return (
        "bg-slate-50 " +
        "text-slate-700 " +
        "border-slate-200"
      );
  }
}


export function FinancialFactTable({
  documentId,
}: Props) {
  const [
    status,
    setStatus,
  ] = useState<
    FinancialFactStatus
  >("validated");

  const [
    data,
    setData,
  ] = useState<
    DocumentFinancialFactsResponse
    | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    selectedSource,
    setSelectedSource,
  ] = useState<
    FinancialFactSource | null
  >(null);


  useEffect(() => {
    if (!documentId) {
      return;
    }

    const controller =
      new AbortController();

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const response =
          await fetch(
            `/api/facts/${encodeURIComponent(
              documentId,
            )}?status=${status}&limit=250`,
            {
              signal:
                controller.signal,
              cache: "no-store",
            },
          );

        const body =
          await response.json();

        if (!response.ok) {
          throw new Error(
            body?.detail ??
              body?.error ??
              "Unable to load financial facts.",
          );
        }

        setData(body);
      } catch (caught) {
        if (
          caught instanceof DOMException &&
          caught.name ===
            "AbortError"
        ) {
          return;
        }

        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load facts.",
        );
      } finally {
        setLoading(false);
      }
    }

    load();

    return () => {
      controller.abort();
    };
  }, [
    documentId,
    status,
  ]);


  const filteredFacts =
    useMemo(() => {
      const facts =
        data?.facts ?? [];

      const normalized =
        search
          .trim()
          .toLowerCase();

      if (!normalized) {
        return facts;
      }

      return facts.filter(
        (fact) => {
          const haystack = [
            fact.metric_label,
            fact.metric_key,
            fact.canonical_metric_key,
            fact.period_label,
            fact.raw_value,
            fact.category,
            fact.statement_type,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

          return haystack.includes(
            normalized,
          );
        },
      );
    }, [
      data,
      search,
    ]);


  const countForStatus = (
    value: FinancialFactStatus,
  ) => {
    if (!data) {
      return 0;
    }

    if (value === "all") {
      return data.summary.total;
    }

    return data.summary[value];
  };


  return (
    <section className="space-y-4">
      <div
        className="
          flex flex-col gap-3
          lg:flex-row
          lg:items-center
          lg:justify-between
        "
      >
        <div>
          <h2
            className="
              text-lg font-semibold
              text-slate-950
            "
          >
            Financial facts
          </h2>

          <p
            className="
              mt-1 text-sm
              text-slate-500
            "
          >
            Structured facts extracted
            from the document and checked
            against source evidence.
          </p>
        </div>

        <input
          value={search}
          onChange={(event) =>
            setSearch(
              event.target.value,
            )
          }
          placeholder="Search metrics..."
          className="
            w-full rounded-lg border
            border-slate-200 bg-white
            px-3 py-2 text-sm
            outline-none
            focus:border-slate-400
            lg:w-72
          "
        />
      </div>


      <div
        className="
          flex flex-wrap gap-2
        "
      >
        {STATUS_OPTIONS.map(
          (option) => {
            const active =
              status ===
              option.value;

            return (
              <button
                key={option.value}
                type="button"
                onClick={() =>
                  setStatus(
                    option.value,
                  )
                }
                className={[
                  "rounded-full border",
                  "px-3 py-1.5",
                  "text-sm",
                  "transition",
                  active
                    ? (
                        "border-slate-900 " +
                        "bg-slate-900 " +
                        "text-white"
                      )
                    : (
                        "border-slate-200 " +
                        "bg-white " +
                        "text-slate-700 " +
                        "hover:bg-slate-50"
                      ),
                ].join(" ")}
              >
                {option.label}

                {data && (
                  <span
                    className="ml-1 opacity-70"
                  >
                    {countForStatus(
                      option.value,
                    )}
                  </span>
                )}
              </button>
            );
          },
        )}
      </div>


      {loading && (
        <div
          className="
            rounded-xl border
            border-slate-200
            bg-white p-8
            text-center text-sm
            text-slate-500
          "
        >
          Loading financial facts…
        </div>
      )}


      {error && (
        <div
          className="
            rounded-xl border
            border-red-200
            bg-red-50 p-4
            text-sm text-red-700
          "
        >
          {error}
        </div>
      )}


      {!loading &&
        !error &&
        data && (
          <div
            className="
              overflow-hidden
              rounded-xl border
              border-slate-200
              bg-white
            "
          >
            <div className="overflow-x-auto">
              <table
                className="
                  min-w-full
                  text-left text-sm
                "
              >
                <thead
                  className="
                    border-b
                    border-slate-200
                    bg-slate-50
                    text-xs uppercase
                    tracking-wide
                    text-slate-500
                  "
                >
                  <tr>
                    <th className="px-4 py-3">
                      Metric
                    </th>

                    <th className="px-4 py-3">
                      Period
                    </th>

                    <th className="px-4 py-3">
                      Value
                    </th>

                    <th className="px-4 py-3">
                      Status
                    </th>

                    <th className="px-4 py-3">
                      Score
                    </th>

                    <th className="px-4 py-3">
                      Source
                    </th>
                  </tr>
                </thead>

                <tbody
                  className="
                    divide-y
                    divide-slate-100
                  "
                >
                  {filteredFacts.map(
                    (fact) => (
                      <tr
                        key={
                          fact.fact_id
                        }
                        className="
                          align-top
                          hover:bg-slate-50/70
                        "
                      >
                        <td
                          className="
                            px-4 py-3
                          "
                        >
                          <div
                            className="
                              font-medium
                              text-slate-950
                            "
                          >
                            {
                              fact.metric_label
                            }
                          </div>

                          <div
                            className="
                              mt-1 font-mono
                              text-xs
                              text-slate-400
                            "
                          >
                            {
                              fact.canonical_metric_key ??
                              fact.metric_key
                            }
                          </div>
                        </td>

                        <td
                          className="
                            whitespace-nowrap
                            px-4 py-3
                            text-slate-700
                          "
                        >
                          {
                            fact.period_label ??
                            "—"
                          }
                        </td>

                        <td
                          className="
                            whitespace-nowrap
                            px-4 py-3
                            font-medium
                            text-slate-950
                          "
                        >
                          {
                            displayValue(
                              fact,
                            )
                          }

                          {fact.scale && (
                            <div
                              className="
                                mt-1 text-xs
                                font-normal
                                text-slate-400
                              "
                            >
                              Scale:{" "}
                              {
                                fact.scale
                              }
                            </div>
                          )}
                        </td>

                        <td
                          className="
                            px-4 py-3
                          "
                        >
                          <span
                            className={[
                              "inline-flex",
                              "rounded-full",
                              "border",
                              "px-2 py-1",
                              "text-xs",
                              "font-medium",
                              statusClass(
                                fact.validation_status,
                              ),
                            ].join(" ")}
                          >
                            {
                              fact.validation_status
                            }
                          </span>

                          {fact.validation_reason && (
                            <div
                              className="
                                mt-2 max-w-xs
                                text-xs
                                text-slate-500
                              "
                            >
                              {
                                fact.validation_reason
                              }
                            </div>
                          )}
                        </td>

                        <td
                          className="
                            px-4 py-3
                            text-slate-700
                          "
                        >
                          {
                            formatScore(
                              fact.validation_score,
                            )
                          }
                        </td>

                        <td
                          className="
                            px-4 py-3
                          "
                        >
                          {fact.source ? (
                            <button
                              type="button"
                              onClick={() =>
                                setSelectedSource(
                                  fact.source,
                                )
                              }
                              className="
                                text-sm
                                font-medium
                                text-slate-700
                                underline
                                underline-offset-4
                                hover:text-slate-950
                              "
                            >
                              View source
                            </button>
                          ) : (
                            <span
                              className="
                                text-slate-400
                              "
                            >
                              —
                            </span>
                          )}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>


            {filteredFacts.length ===
              0 && (
              <div
                className="
                  p-8 text-center
                  text-sm
                  text-slate-500
                "
              >
                No facts matched this
                filter.
              </div>
            )}
          </div>
        )}


      {selectedSource && (
        <div
          className="
            rounded-xl border
            border-slate-200
            bg-slate-50 p-4
          "
        >
          <div
            className="
              flex items-start
              justify-between
              gap-4
            "
          >
            <div>
              <h3
                className="
                  font-medium
                  text-slate-950
                "
              >
                Source evidence
              </h3>

              <div
                className="
                  mt-1 text-xs
                  text-slate-500
                "
              >
                {
                  selectedSource.source_title ??
                  "Document"
                }

                {selectedSource.page_number !=
                  null &&
                  ` · Page ${selectedSource.page_number}`}
              </div>
            </div>

            <button
              type="button"
              onClick={() =>
                setSelectedSource(
                  null,
                )
              }
              className="
                text-sm
                text-slate-500
                hover:text-slate-950
              "
            >
              Close
            </button>
          </div>

          <p
            className="
              mt-4 whitespace-pre-wrap
              text-sm leading-6
              text-slate-700
            "
          >
            {
              selectedSource.source_snippet ??
              "No source snippet available."
            }
          </p>

          <div
            className="
              mt-4 font-mono
              text-xs
              text-slate-400
            "
          >
            {
              selectedSource.chunk_id ??
              selectedSource.source_ledger_id
            }
          </div>
        </div>
      )}
    </section>
  );
}