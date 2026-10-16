"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  DocumentFinancialFactsResponse,
  FinancialFactChartPoint,
  FinancialFactChartResponse,
} from "@/lib/financial-facts";


type Props = {
  documentId: string;
};


function shortPeriod(
  point: FinancialFactChartPoint,
) {
  if (point.period_end) {
    return (
      point.period_end
        .slice(
          0,
          4,
        )
    );
  }

  if (point.period_start) {
    return (
      point.period_start
        .slice(
          0,
          4,
        )
    );
  }

  const match =
    point.period_label.match(
      /\b(?:19|20)\d{2}\b/,
    );

  return (
    match?.[0] ??
    point.period_label
  );
}


function scoreLabel(
  value: number | null,
) {
  if (value == null) {
    return "—";
  }

  return `${
    Math.round(
      value * 100,
    )
  }%`;
}


export function FinancialFactChartBuilder({
  documentId,
}: Props) {
  const [
    facts,
    setFacts,
  ] = useState<
    DocumentFinancialFactsResponse
    | null
  >(null);

  const [
    metricKey,
    setMetricKey,
  ] = useState("");

  const [
    chart,
    setChart,
  ] = useState<
    FinancialFactChartResponse
    | null
  >(null);

  const [
    loadingFacts,
    setLoadingFacts,
  ] = useState(false);

  const [
    loadingChart,
    setLoadingChart,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    selectedPoint,
    setSelectedPoint,
  ] = useState<
    FinancialFactChartPoint
    | null
  >(null);


  useEffect(() => {
    if (!documentId) {
      return;
    }

    const controller =
      new AbortController();

    async function loadFacts() {
      setLoadingFacts(true);
      setError(null);

      try {
        const response =
          await fetch(
            `/api/facts/${encodeURIComponent(
              documentId,
            )}?status=validated&limit=500`,
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
            "Unable to load validated facts.",
          );
        }

        setFacts(body);

      } catch (caught) {
        if (
          caught instanceof DOMException &&
          caught.name === "AbortError"
        ) {
          return;
        }

        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load facts.",
        );

      } finally {
        setLoadingFacts(false);
      }
    }

    loadFacts();

    return () => {
      controller.abort();
    };

  }, [
    documentId,
  ]);


  const metrics =
    useMemo(() => {
      const map =
        new Map<
          string,
          string
        >();

      for (
        const fact
        of facts?.facts ?? []
      ) {
        if (
          ![
            "currency",
            "percentage",
            "number",
            "count",
            "ratio",
            "per_share",
          ].includes(
            fact.value_type,
          )
        ) {
          continue;
        }

        if (
          !fact.period_label &&
          !fact.period_start &&
          !fact.period_end
        ) {
          continue;
        }

        const key =
          fact.canonical_metric_key ??
          fact.metric_key;

        if (!map.has(key)) {
          map.set(
            key,
            fact.metric_label,
          );
        }
      }

      return Array.from(
        map.entries(),
      )
        .map(
          ([
            key,
            label,
          ]) => ({
            key,
            label,
          }),
        )
        .sort(
          (a, b) =>
            a.label.localeCompare(
              b.label,
            ),
        );

    }, [
      facts,
    ]);


  useEffect(() => {
    if (
      !metricKey &&
      metrics.length > 0
    ) {
      setMetricKey(
        metrics[0].key,
      );
    }

  }, [
    metrics,
    metricKey,
  ]);


  useEffect(() => {
    if (
      !documentId ||
      !metricKey
    ) {
      return;
    }

    const controller =
      new AbortController();

    async function loadChart() {
      setLoadingChart(true);
      setError(null);
      setSelectedPoint(null);

      try {
        const params =
          new URLSearchParams({
            metric_key:
              metricKey,
            chart_type:
              "auto",
          });

        const response =
          await fetch(
            `/api/facts/${encodeURIComponent(
              documentId,
            )}/chart?${params.toString()}`,
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
            "Unable to build chart.",
          );
        }

        setChart(body);

      } catch (caught) {
        if (
          caught instanceof DOMException &&
          caught.name === "AbortError"
        ) {
          return;
        }

        setChart(null);

        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to build chart.",
        );

      } finally {
        setLoadingChart(false);
      }
    }

    loadChart();

    return () => {
      controller.abort();
    };

  }, [
    documentId,
    metricKey,
  ]);


  const chartData =
    useMemo(
      () =>
        (
          chart?.points ??
          []
        ).map(
          (point) => ({
            period:
              shortPeriod(
                point,
              ),

            value:
              point.value,

            raw:
              point.raw_value,

            point,
          }),
        ),
      [
        chart,
      ],
    );


  return (
    <section
      className="
        space-y-4
        rounded-xl
        border
        border-slate-200
        bg-white
        p-5
      "
    >
      <div
        className="
          flex flex-col gap-3
          lg:flex-row
          lg:items-end
          lg:justify-between
        "
      >
        <div>
          <h2
            className="
              text-lg
              font-semibold
              text-slate-950
            "
          >
            Financial fact chart
          </h2>

          <p
            className="
              mt-1 text-sm
              text-slate-500
            "
          >
            Charts use validated
            document facts only.
          </p>
        </div>


        <div
          className="
            min-w-72
          "
        >
          <label
            className="
              mb-1 block
              text-xs
              font-medium
              text-slate-500
            "
          >
            Metric
          </label>

          <select
            value={metricKey}
            disabled={
              loadingFacts ||
              metrics.length === 0
            }
            onChange={
              (event) =>
                setMetricKey(
                  event.target.value,
                )
            }
            className="
              w-full
              rounded-lg
              border
              border-slate-200
              bg-white
              px-3 py-2
              text-sm
              outline-none
              focus:border-slate-400
            "
          >
            {metrics.map(
              (metric) => (
                <option
                  key={
                    metric.key
                  }
                  value={
                    metric.key
                  }
                >
                  {
                    metric.label
                  }
                </option>
              ),
            )}
          </select>
        </div>
      </div>


      {error && (
        <div
          className="
            rounded-lg
            border
            border-red-200
            bg-red-50
            p-3
            text-sm
            text-red-700
          "
        >
          {error}
        </div>
      )}


      {loadingChart && (
        <div
          className="
            flex h-80
            items-center
            justify-center
            text-sm
            text-slate-500
          "
        >
          Building chart…
        </div>
      )}


      {!loadingChart &&
        chart && (
          <>
            <div>
              <div
                className="
                  font-medium
                  text-slate-950
                "
              >
                {
                  chart.metric_label
                }
              </div>

              <div
                className="
                  mt-1 text-xs
                  text-slate-500
                "
              >
                {
                  chart.y_axis_label
                }
              </div>
            </div>


            <div
              className="
                h-80 w-full
              "
            >
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                {chart.chart_type ===
                "line" ? (
                  <LineChart
                    data={
                      chartData
                    }
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="period"
                    />

                    <YAxis />

                    <Tooltip
                      formatter={(
                        value,
                        _name,
                        item,
                      ) => {
                        const raw =
                          (
                            item
                            ?.payload
                            ?.raw
                          );

                        return [
                          raw ??
                          value,
                          chart.metric_label,
                        ];
                      }}
                    />

                    <Line
                      type="monotone"
                      dataKey="value"
                      strokeWidth={2}
                      activeDot={{
                        r: 6,
                      }}
                    />
                  </LineChart>
                ) : (
                  <BarChart
                    data={
                      chartData
                    }
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="period"
                    />

                    <YAxis />

                    <Tooltip
                      formatter={(
                        value,
                        _name,
                        item,
                      ) => {
                        const raw =
                          (
                            item
                            ?.payload
                            ?.raw
                          );

                        return [
                          raw ??
                          value,
                          chart.metric_label,
                        ];
                      }}
                    />

                    <Bar
                      dataKey="value"
                    />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>


            {chart.warnings.length >
              0 && (
              <div
                className="
                  rounded-lg
                  border
                  border-amber-200
                  bg-amber-50
                  p-3
                  text-sm
                  text-amber-800
                "
              >
                {
                  chart.warnings.join(
                    " ",
                  )
                }
              </div>
            )}


            <div
              className="
                border-t
                border-slate-100
                pt-4
              "
            >
              <div
                className="
                  mb-2 text-sm
                  font-medium
                  text-slate-900
                "
              >
                Chart evidence
              </div>

              <div
                className="
                  space-y-2
                "
              >
                {chart.points.map(
                  (point) => (
                    <div
                      key={
                        point.fact_id
                      }
                      className="
                        flex
                        items-center
                        justify-between
                        gap-3
                        rounded-lg
                        bg-slate-50
                        px-3 py-2
                        text-sm
                      "
                    >
                      <div>
                        <span
                          className="
                            font-medium
                            text-slate-900
                          "
                        >
                          {
                            point.period_label
                          }
                        </span>

                        <span
                          className="
                            ml-2
                            text-slate-500
                          "
                        >
                          {
                            point.raw_value ??
                            point.numeric_value
                          }
                        </span>

                        <span
                          className="
                            ml-2
                            text-xs
                            text-slate-400
                          "
                        >
                          {
                            scoreLabel(
                              point.validation_score,
                            )
                          }
                        </span>
                      </div>

                      {point.source && (
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedPoint(
                              point,
                            )
                          }
                          className="
                            text-sm
                            font-medium
                            text-slate-700
                            underline
                            underline-offset-4
                          "
                        >
                          View source
                        </button>
                      )}
                    </div>
                  ),
                )}
              </div>
            </div>
          </>
        )}


      {selectedPoint?.source && (
        <div
          className="
            rounded-lg
            border
            border-slate-200
            bg-slate-50
            p-4
          "
        >
          <div
            className="
              flex
              justify-between
              gap-4
            "
          >
            <div>
              <div
                className="
                  font-medium
                  text-slate-950
                "
              >
                Source evidence
              </div>

              <div
                className="
                  mt-1 text-xs
                  text-slate-500
                "
              >
                {
                  selectedPoint
                    .source
                    .source_title ??
                  "Document"
                }

                {
                  selectedPoint
                    .source
                    .page_number !=
                    null &&
                  ` · Page ${
                    selectedPoint
                      .source
                      .page_number
                  }`
                }
              </div>
            </div>

            <button
              type="button"
              onClick={() =>
                setSelectedPoint(
                  null,
                )
              }
              className="
                text-sm
                text-slate-500
              "
            >
              Close
            </button>
          </div>

          <p
            className="
              mt-4
              whitespace-pre-wrap
              text-sm
              leading-6
              text-slate-700
            "
          >
            {
              selectedPoint
                .source
                .source_snippet ??
              (
                "No source "
                + "snippet available."
              )
            }
          </p>
        </div>
      )}
    </section>
  );
}