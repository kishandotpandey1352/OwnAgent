"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  toPng,
} from "html-to-image";

import type {
  ChartDataRow,
  ChartSpec,
} from "@/types/chart";


type ChartRendererProps = {
  spec: ChartSpec;
  height?: number;
  showMetadata?: boolean;
  showExportActions?: boolean;
  showZoomControls?: boolean;
};


type ExportStatus = {
  kind: "success" | "error";
  message: string;
} | null;


const SERIES_COLORS = [
  "#22d3ee",
  "#fbbf24",
  "#a78bfa",
  "#34d399",
  "#fb7185",
  "#60a5fa",
  "#f97316",
  "#2dd4bf",
];


const MIN_EXPORT_WIDTH = 900;


function seriesColor(
  index: number,
) {
  return SERIES_COLORS[
    index %
      SERIES_COLORS.length
  ];
}


function formatCompactNumber(
  value: number,
) {
  const absolute =
    Math.abs(value);

  if (
    absolute >=
    1_000_000_000
  ) {
    return `${(
      value /
      1_000_000_000
    ).toFixed(1)}B`;
  }

  if (
    absolute >=
    1_000_000
  ) {
    return `${(
      value /
      1_000_000
    ).toFixed(1)}M`;
  }

  if (
    absolute >=
    1_000
  ) {
    return `${(
      value /
      1_000
    ).toFixed(1)}K`;
  }

  return new Intl.NumberFormat(
    undefined,
    {
      maximumFractionDigits: 2,
    },
  ).format(value);
}


function formatAxisValue(
  value: unknown,
) {
  if (
    typeof value ===
    "number"
  ) {
    return formatCompactNumber(
      value,
    );
  }

  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  return String(value);
}


function coverageLabel(
  coverage: number,
) {
  return `${Math.round(
    coverage * 100,
  )}%`;
}


function sanitizeFileName(
  value: string,
) {
  const cleaned = value
    .trim()
    .toLowerCase()
    .replace(
      /[^a-z0-9]+/g,
      "-",
    )
    .replace(
      /^-+|-+$/g,
      "",
    );

  return (
    cleaned ||
    "finance-chart"
  );
}


function downloadBlob(
  blob: Blob,
  fileName: string,
) {
  const url =
    URL.createObjectURL(
      blob,
    );

  const anchor =
    document.createElement(
      "a",
    );

  anchor.href = url;
  anchor.download =
    fileName;

  document.body.appendChild(
    anchor,
  );

  anchor.click();

  anchor.remove();

  window.setTimeout(
    () => {
      URL.revokeObjectURL(
        url,
      );
    },
    1000,
  );
}


function getExportColumns(
  spec: ChartSpec,
) {
  const columns: string[] =
    [];

  if (spec.x) {
    columns.push(
      spec.x,
    );
  }

  for (
    const seriesName
    of spec.series
  ) {
    if (
      !columns.includes(
        seriesName,
      )
    ) {
      columns.push(
        seriesName,
      );
    }
  }

  /*
   * Preserve any additional backend-provided fields.
   * This is useful for table responses and future
   * chart specifications with source metadata.
   */
  for (
    const row
    of spec.data
  ) {
    for (
      const key
      of Object.keys(row)
    ) {
      if (
        !columns.includes(
          key,
        )
      ) {
        columns.push(
          key,
        );
      }
    }
  }

  return columns;
}


function serializeCell(
  value:
    | ChartDataRow[string]
    | undefined,
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  return String(value);
}


function escapeCsvCell(
  value:
    | ChartDataRow[string]
    | undefined,
) {
  const text =
    serializeCell(value);

  if (
    text.includes(",") ||
    text.includes('"') ||
    text.includes("\n") ||
    text.includes("\r")
  ) {
    return `"${text.replace(
      /"/g,
      '""',
    )}"`;
  }

  return text;
}


function chartSpecToCsv(
  spec: ChartSpec,
) {
  const columns =
    getExportColumns(
      spec,
    );

  const header =
    columns
      .map(
        escapeCsvCell,
      )
      .join(",");

  const rows =
    spec.data.map(
      (row) =>
        columns
          .map(
            (column) =>
              escapeCsvCell(
                row[
                  column
                ],
              ),
          )
          .join(","),
    );

  /*
   * UTF-8 BOM improves compatibility with Excel
   * when files contain non-ASCII text.
   */
  return (
    "\uFEFF" +
    [
      header,
      ...rows,
    ].join("\r\n")
  );
}


function chartSpecToTsv(
  spec: ChartSpec,
) {
  const columns =
    getExportColumns(
      spec,
    );

  const sanitizeTsv =
    (
      value:
        | ChartDataRow[string]
        | undefined,
    ) =>
      serializeCell(value)
        .replace(
          /\t/g,
          " ",
        )
        .replace(
          /\r?\n/g,
          " ",
        );

  const rows =
    spec.data.map(
      (row) =>
        columns
          .map(
            (column) =>
              sanitizeTsv(
                row[
                  column
                ],
              ),
          )
          .join("\t"),
    );

  return [
    columns.join("\t"),
    ...rows,
  ].join("\n");
}


async function copyText(
  text: string,
) {
  if (
    navigator.clipboard &&
    window.isSecureContext
  ) {
    await navigator.clipboard.writeText(
      text,
    );

    return;
  }

  const textarea =
    document.createElement(
      "textarea",
    );

  textarea.value = text;
  textarea.style.position =
    "fixed";
  textarea.style.left =
    "-9999px";
  textarea.style.top =
    "-9999px";

  document.body.appendChild(
    textarea,
  );

  textarea.focus();
  textarea.select();

  const copied =
    document.execCommand(
      "copy",
    );

  textarea.remove();

  if (!copied) {
    throw new Error(
      "The browser did not allow clipboard access.",
    );
  }
}


function waitForLayout() {
  return new Promise<void>(
    (resolve) => {
      window.requestAnimationFrame(
        () => {
          window.requestAnimationFrame(
            () => resolve(),
          );
        },
      );
    },
  );
}


export function ChartRenderer({
  spec,
  height = 380,
  showMetadata = true,
  showExportActions = true,
  showZoomControls = true,
}: ChartRendererProps) {
  const chartContainerRef =
    useRef<HTMLDivElement | null>(
      null,
    );

  const [
    exportingPng,
    setExportingPng,
  ] = useState(false);

  const [
    exportStatus,
    setExportStatus,
  ] =
    useState<ExportStatus>(
      null,
    );

  const [
    zoomRange,
    setZoomRange,
  ] = useState({
    start: 0,
    end: Math.max(
      spec.data.length - 1,
      0,
    ),
  });

  const totalPoints =
    spec.data.length;

  useEffect(() => {
    setZoomRange({
      start: 0,
      end: Math.max(
        spec.data.length - 1,
        0,
      ),
    });
  }, [
    spec.dataset_id,
    spec.chart_type,
    spec.x,
    spec.title,
    spec.data.length,
    spec.series.join("|"),
  ]);

  const visibleData =
    spec.data.slice(
      zoomRange.start,
      zoomRange.end + 1,
    );

  const zoomedSpec: ChartSpec = {
    ...spec,
    data: visibleData,
  };

  const isZoomed =
    totalPoints > 0 &&
    (zoomRange.start > 0 ||
      zoomRange.end <
        totalPoints - 1);


  function resetZoom() {
    setZoomRange({
      start: 0,
      end: Math.max(
        totalPoints - 1,
        0,
      ),
    });
  }


  function handleZoomIn() {
    if (totalPoints <= 2) {
      return;
    }

    setZoomRange(
      (current) => {
        const currentSize =
          current.end -
          current.start +
          1;

        if (currentSize <= 2) {
          return current;
        }

        const nextSize =
          Math.max(
            2,
            Math.floor(
              currentSize *
                0.7,
            ),
          );

        const center =
          (current.start +
            current.end) /
          2;

        let start = Math.max(
          0,
          Math.round(
            center -
              (nextSize - 1) /
                2,
          ),
        );

        let end =
          start +
          nextSize -
          1;

        if (
          end >= totalPoints
        ) {
          end =
            totalPoints - 1;

          start = Math.max(
            0,
            end -
              nextSize +
              1,
          );
        }

        return {
          start,
          end,
        };
      },
    );
  }


  function handleZoomOut() {
    setZoomRange(
      (current) => {
        const currentSize =
          current.end -
          current.start +
          1;

        if (
          currentSize >=
          totalPoints
        ) {
          return current;
        }

        const nextSize =
          Math.min(
            totalPoints,
            Math.max(
              currentSize + 1,
              Math.ceil(
                currentSize /
                  0.7,
              ),
            ),
          );

        const center =
          (current.start +
            current.end) /
          2;

        let start = Math.max(
          0,
          Math.round(
            center -
              (nextSize - 1) /
                2,
          ),
        );

        let end =
          start +
          nextSize -
          1;

        if (
          end >= totalPoints
        ) {
          end =
            totalPoints - 1;

          start = Math.max(
            0,
            end -
              nextSize +
              1,
          );
        }

        return {
          start,
          end,
        };
      },
    );
  }


  function panZoom(
    direction: "left" | "right",
  ) {
    if (!isZoomed) {
      return;
    }

    setZoomRange(
      (current) => {
        const currentSize =
          current.end -
          current.start +
          1;

        const shift =
          Math.max(
            1,
            Math.floor(
              currentSize *
                0.25,
            ),
          );

        if (
          direction ===
          "left"
        ) {
          const start =
            Math.max(
              0,
              current.start -
                shift,
            );

          return {
            start,
            end:
              start +
              currentSize -
              1,
          };
        }

        const end = Math.min(
          totalPoints - 1,
          current.end + shift,
        );

        return {
          start:
            end -
            currentSize +
            1,
          end,
        };
      },
    );
  }


  function clearExportStatusSoon() {
    window.setTimeout(
      () => {
        setExportStatus(
          null,
        );
      },
      3000,
    );
  }


  function handleExportCsv() {
    try {
      const csv =
        chartSpecToCsv(
          spec,
        );

      const blob =
        new Blob(
          [csv],
          {
            type:
              "text/csv;charset=utf-8",
          },
        );

      downloadBlob(
        blob,
        `${sanitizeFileName(
          spec.title,
        )}.csv`,
      );

      setExportStatus({
        kind: "success",
        message:
          "Chart data exported as CSV.",
      });

      clearExportStatusSoon();
    } catch (error) {
      setExportStatus({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "CSV export failed.",
      });
    }
  }


  async function handleCopyData() {
    try {
      const tsv =
        chartSpecToTsv(
          spec,
        );

      await copyText(
        tsv,
      );

      setExportStatus({
        kind: "success",
        message:
          "Chart data copied. Paste it into Excel or Google Sheets.",
      });

      clearExportStatusSoon();
    } catch (error) {
      setExportStatus({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to copy chart data.",
      });
    }
  }


  async function handleDownloadPng() {
    if (
      spec.chart_type ===
      "table"
    ) {
      setExportStatus({
        kind: "error",
        message:
          "PNG export is available for visual charts. Use CSV export for table views.",
      });

      clearExportStatusSoon();
      return;
    }

    const container =
      chartContainerRef.current;

    if (!container) {
      setExportStatus({
        kind: "error",
        message:
          "The rendered chart could not be located.",
      });

      clearExportStatusSoon();
      return;
    }

    setExportingPng(true);
    setExportStatus(null);

    const originalWidth =
      container.style.width;

    const originalMaxWidth =
      container.style.maxWidth;

    try {
      /*
       * ResponsiveContainer can be extremely narrow if the
       * surrounding workspace is narrow. Temporarily give the
       * export surface a report-friendly width so Recharts can
       * recalculate before html-to-image captures it.
       */
      const visibleWidth =
        Math.round(
          container
            .getBoundingClientRect()
            .width,
        );

      if (
        visibleWidth <
        MIN_EXPORT_WIDTH
      ) {
        container.style.width =
          `${MIN_EXPORT_WIDTH}px`;

        container.style.maxWidth =
          "none";

        await waitForLayout();
      }

      const exportWidth =
        Math.max(
          container.scrollWidth,
          Math.round(
            container
              .getBoundingClientRect()
              .width,
          ),
          MIN_EXPORT_WIDTH,
        );

      const exportHeight =
        Math.max(
          container.scrollHeight,
          Math.round(
            container
              .getBoundingClientRect()
              .height,
          ),
          1,
        );

      const dataUrl =
        await toPng(
          container,
          {
            cacheBust: true,
            pixelRatio: 2,
            backgroundColor:
              "#020617",
            width:
              exportWidth,
            height:
              exportHeight,
            style: {
              margin: "0",
              width:
                `${exportWidth}px`,
            },
          },
        );

      const response =
        await fetch(
          dataUrl,
        );

      const blob =
        await response.blob();

      downloadBlob(
        blob,
        `${sanitizeFileName(
          spec.title,
        )}.png`,
      );

      setExportStatus({
        kind: "success",
        message:
          "Chart downloaded as PNG.",
      });

      clearExportStatusSoon();
    } catch (error) {
      setExportStatus({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "PNG export failed.",
      });
    } finally {
      container.style.width =
        originalWidth;

      container.style.maxWidth =
        originalMaxWidth;

      await waitForLayout();

      setExportingPng(
        false,
      );
    }
  }


  if (!spec.data.length) {
    return (
      <ChartError
        message="The chart specification does not contain any data points."
      />
    );
  }

  const chart =
    renderChart(
      zoomedSpec,
      height,
    );

  return (
    <section className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
      {/*
       * Only this block is exported to PNG.
       * Export controls and transient status messages stay outside.
       */}
      <div
        ref={chartContainerRef}
        className="bg-slate-950"
      >
        <div className="border-b border-white/10 px-4 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                {spec.chart_type}{" "}
                visualization
              </p>

              <h3 className="mt-1 break-words text-base font-semibold text-white">
                {spec.title}
              </h3>

              {spec.explanation ? (
                <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">
                  {
                    spec.explanation
                  }
                </p>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[10px] font-semibold text-cyan-100">
                {
                  spec.chart_row_count
                }{" "}
                points
              </span>

              <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-100">
                {coverageLabel(
                  spec.source_coverage,
                )}{" "}
                source coverage
              </span>

              {spec.sampled ? (
                <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-2.5 py-1 text-[10px] font-semibold text-amber-100">
                  sampled
                </span>
              ) : null}

              {isZoomed ? (
                <span className="rounded-full border border-violet-300/20 bg-violet-300/10 px-2.5 py-1 text-[10px] font-semibold text-violet-100">
                  zoom {zoomRange.start + 1}-{zoomRange.end + 1}
                </span>
              ) : null}
            </div>
          </div>
        </div>

        <div className="p-3 sm:p-4">
          {chart}
        </div>

        {showMetadata ? (
          <ChartMetadata
            spec={spec}
          />
        ) : null}
      </div>

      {showZoomControls &&
      spec.chart_type !==
        "table" &&
      totalPoints > 1 ? (
        <div className="border-t border-white/10 bg-slate-950/70 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={
                handleZoomIn
              }
              disabled={
                visibleData.length <=
                2
              }
              className="rounded-lg border border-violet-300/20 bg-violet-300/10 px-3 py-2 text-xs font-semibold text-violet-100 transition hover:border-violet-300/40 hover:bg-violet-300/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Zoom in
            </button>

            <button
              type="button"
              onClick={
                handleZoomOut
              }
              disabled={!isZoomed}
              className="rounded-lg border border-violet-300/20 bg-violet-300/10 px-3 py-2 text-xs font-semibold text-violet-100 transition hover:border-violet-300/40 hover:bg-violet-300/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Zoom out
            </button>

            <button
              type="button"
              onClick={() =>
                panZoom(
                  "left",
                )
              }
              disabled={
                !isZoomed ||
                zoomRange.start ===
                  0
              }
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-white/20 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Pan left
            </button>

            <button
              type="button"
              onClick={() =>
                panZoom(
                  "right",
                )
              }
              disabled={
                !isZoomed ||
                zoomRange.end >=
                  totalPoints -
                    1
              }
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-white/20 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Pan right
            </button>

            <button
              type="button"
              onClick={
                resetZoom
              }
              disabled={!isZoomed}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-white/20 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Reset zoom
            </button>

            <span className="ml-auto rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold text-slate-300">
              Showing {
                zoomRange.start +
                1
              }-{
                zoomRange.end +
                1
              } of {
                totalPoints
              } points
            </span>
          </div>
        </div>
      ) : null}

      {showExportActions ? (
        <div className="border-t border-white/10 bg-black/20 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            {spec.chart_type !==
            "table" ? (
              <button
                type="button"
                onClick={
                  handleDownloadPng
                }
                disabled={
                  exportingPng
                }
                className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-xs font-semibold text-cyan-100 transition hover:border-cyan-300/40 hover:bg-cyan-300/15 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {exportingPng
                  ? "Preparing PNG..."
                  : "Download PNG"}
              </button>
            ) : null}

            <button
              type="button"
              onClick={
                handleExportCsv
              }
              className="rounded-lg border border-emerald-300/20 bg-emerald-300/10 px-3 py-2 text-xs font-semibold text-emerald-100 transition hover:border-emerald-300/40 hover:bg-emerald-300/15"
            >
              Export CSV
            </button>

            <button
              type="button"
              onClick={
                handleCopyData
              }
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-white/20 hover:bg-white/10 hover:text-white"
            >
              Copy data
            </button>
          </div>

          {exportStatus ? (
            <div
              className={[
                "mt-3 rounded-xl border px-3 py-2 text-xs",
                exportStatus.kind ===
                "success"
                  ? "border-emerald-300/20 bg-emerald-300/5 text-emerald-100"
                  : "border-rose-300/20 bg-rose-300/5 text-rose-100",
              ].join(" ")}
            >
              {
                exportStatus.message
              }
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}


function renderChart(
  spec: ChartSpec,
  height: number,
) {
  switch (
    spec.chart_type
  ) {
    case "line":
      return (
        <LineChartView
          spec={spec}
          height={height}
        />
      );

    case "bar":
      return (
        <BarChartView
          spec={spec}
          height={height}
        />
      );

    case "area":
      return (
        <AreaChartView
          spec={spec}
          height={height}
        />
      );

    case "scatter":
      return (
        <ScatterChartView
          spec={spec}
          height={height}
        />
      );

    case "table":
      return (
        <TableChartView
          spec={spec}
        />
      );

    default:
      return (
        <ChartError
          message="Unsupported chart type."
        />
      );
  }
}


function LineChartView({
  spec,
  height,
}: {
  spec: ChartSpec;
  height: number;
}) {
  if (
    !spec.x ||
    !spec.series.length
  ) {
    return (
      <ChartError
        message="Line chart requires an x-axis and at least one series."
      />
    );
  }

  return (
    <div
      style={{
        height,
      }}
      className="w-full"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
      >
        <LineChart
          data={spec.data}
          margin={{
            top: 16,
            right: 20,
            bottom: 12,
            left: 4,
          }}
        >
          <CartesianGrid
            stroke="rgba(148,163,184,0.12)"
            vertical={false}
          />

          <XAxis
            dataKey={spec.x}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={{
              stroke:
                "rgba(148,163,184,0.25)",
            }}
            tickLine={false}
            minTickGap={24}
          />

          <YAxis
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={
              formatAxisValue
            }
          />

          <Tooltip />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            width={130}
            wrapperStyle={{
              paddingLeft: "12px",
              lineHeight: "22px",
              fontSize: "11px",
            }}
          />

          {spec.series.map(
            (
              seriesName,
              index,
            ) => (
              <Line
                key={
                  seriesName
                }
                type="monotone"
                dataKey={
                  seriesName
                }
                name={
                  seriesName
                }
                stroke={
                  seriesColor(
                    index,
                  )
                }
                strokeWidth={2}
                dot={
                  spec.data.length <=
                  50
                    ? {
                        r: 3,
                      }
                    : false
                }
                activeDot={{
                  r: 5,
                }}
                connectNulls={
                  false
                }
              />
            ),
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}


function BarChartView({
  spec,
  height,
}: {
  spec: ChartSpec;
  height: number;
}) {
  if (
    !spec.x ||
    !spec.series.length
  ) {
    return (
      <ChartError
        message="Bar chart requires an x-axis and at least one series."
      />
    );
  }

  return (
    <div
      style={{
        height,
      }}
      className="w-full"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
      >
        <BarChart
          data={spec.data}
          margin={{
            top: 16,
            right: 20,
            bottom: 12,
            left: 4,
          }}
        >
          <CartesianGrid
            stroke="rgba(148,163,184,0.12)"
            vertical={false}
          />

          <XAxis
            dataKey={spec.x}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={{
              stroke:
                "rgba(148,163,184,0.25)",
            }}
            tickLine={false}
            minTickGap={20}
          />

          <YAxis
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={
              formatAxisValue
            }
          />

          <Tooltip />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            width={130}
            wrapperStyle={{
              paddingLeft: "12px",
              lineHeight: "22px",
              fontSize: "11px",
            }}
          />

          {spec.series.map(
            (
              seriesName,
              index,
            ) => (
              <Bar
                key={
                  seriesName
                }
                dataKey={
                  seriesName
                }
                name={
                  seriesName
                }
                fill={
                  seriesColor(
                    index,
                  )
                }
                radius={[
                  4,
                  4,
                  0,
                  0,
                ]}
              />
            ),
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}


function AreaChartView({
  spec,
  height,
}: {
  spec: ChartSpec;
  height: number;
}) {
  if (
    !spec.x ||
    !spec.series.length
  ) {
    return (
      <ChartError
        message="Area chart requires an x-axis and at least one series."
      />
    );
  }

  return (
    <div
      style={{
        height,
      }}
      className="w-full"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
      >
        <AreaChart
          data={spec.data}
          margin={{
            top: 16,
            right: 20,
            bottom: 12,
            left: 4,
          }}
        >
          <CartesianGrid
            stroke="rgba(148,163,184,0.12)"
            vertical={false}
          />

          <XAxis
            dataKey={spec.x}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={{
              stroke:
                "rgba(148,163,184,0.25)",
            }}
            tickLine={false}
            minTickGap={24}
          />

          <YAxis
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={
              formatAxisValue
            }
          />

          <Tooltip />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            width={130}
            wrapperStyle={{
              paddingLeft: "12px",
              lineHeight: "22px",
              fontSize: "11px",
            }}
          />

          {spec.series.map(
            (
              seriesName,
              index,
            ) => (
              <Area
                key={
                  seriesName
                }
                type="monotone"
                dataKey={
                  seriesName
                }
                name={
                  seriesName
                }
                stroke={
                  seriesColor(
                    index,
                  )
                }
                fill={
                  seriesColor(
                    index,
                  )
                }
                fillOpacity={
                  0.16
                }
                strokeWidth={2}
                connectNulls={
                  false
                }
              />
            ),
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}


function ScatterChartView({
  spec,
  height,
}: {
  spec: ChartSpec;
  height: number;
}) {
  const ySeries =
    spec.series[0];

  if (
    !spec.x ||
    !ySeries
  ) {
    return (
      <ChartError
        message="Scatter chart requires numeric x and y fields."
      />
    );
  }

  return (
    <div
      style={{
        height,
      }}
      className="w-full"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
      >
        <ScatterChart
          margin={{
            top: 16,
            right: 20,
            bottom: 20,
            left: 8,
          }}
        >
          <CartesianGrid
            stroke="rgba(148,163,184,0.12)"
          />

          <XAxis
            type="number"
            dataKey={spec.x}
            name={spec.x}
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={{
              stroke:
                "rgba(148,163,184,0.25)",
            }}
            tickLine={false}
            tickFormatter={
              formatAxisValue
            }
          />

          <YAxis
            type="number"
            dataKey={
              ySeries
            }
            name={
              ySeries
            }
            tick={{
              fill: "#94a3b8",
              fontSize: 11,
            }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={
              formatAxisValue
            }
          />

          <Tooltip />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            width={130}
            wrapperStyle={{
              paddingLeft: "12px",
              lineHeight: "22px",
              fontSize: "11px",
            }}
          />

          <Scatter
            name={
              ySeries
            }
            data={
              spec.data
            }
            fill={
              seriesColor(
                0,
              )
            }
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}


function TableChartView({
  spec,
}: {
  spec: ChartSpec;
}) {
  const columns =
    getExportColumns(
      spec,
    );

  if (!columns.length) {
    return (
      <ChartError
        message="No table columns were returned."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="min-w-full border-collapse text-left text-xs">
        <thead className="bg-white/5">
          <tr>
            {columns.map(
              (column) => (
                <th
                  key={
                    column
                  }
                  className="whitespace-nowrap border-b border-white/10 px-4 py-3 font-semibold text-slate-300"
                >
                  {
                    column
                  }
                </th>
              ),
            )}
          </tr>
        </thead>

        <tbody>
          {spec.data.map(
            (
              row,
              rowIndex,
            ) => (
              <tr
                key={
                  rowIndex
                }
                className="border-b border-white/5 last:border-b-0"
              >
                {columns.map(
                  (
                    column,
                  ) => (
                    <td
                      key={
                        column
                      }
                      className="whitespace-nowrap px-4 py-3 text-slate-300"
                    >
                      {formatTableValue(
                        row[
                          column
                        ],
                      )}
                    </td>
                  ),
                )}
              </tr>
            ),
          )}
        </tbody>
      </table>
    </div>
  );
}


function formatTableValue(
  value:
    | ChartDataRow[string]
    | undefined,
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "-";
  }

  if (
    typeof value ===
    "number"
  ) {
    return new Intl.NumberFormat(
      undefined,
      {
        maximumFractionDigits: 4,
      },
    ).format(value);
  }

  return String(value);
}


function ChartMetadata({
  spec,
}: {
  spec: ChartSpec;
}) {
  return (
    <footer className="border-t border-white/10 bg-white/[0.02] px-4 py-3">
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-slate-500">
        <span>
          Dataset:{" "}
          <span className="text-slate-300">
            {
              spec.file_name
            }
          </span>
        </span>

        <span>
          Source rows:{" "}
          <span className="text-slate-300">
            {
              spec.source_row_count
            }
          </span>
        </span>

        <span>
          Chart rows:{" "}
          <span className="text-slate-300">
            {
              spec.chart_row_count
            }
          </span>
        </span>

        {spec.x ? (
          <span>
            X:{" "}
            <span className="text-slate-300">
              {
                spec.x
              }
            </span>
          </span>
        ) : null}
      </div>

      {spec.warnings.length ? (
        <div className="mt-3 space-y-1.5">
          {spec.warnings.map(
            (
              warning,
              index,
            ) => (
              <p
                key={
                  index
                }
                className="rounded-lg border border-amber-300/15 bg-amber-300/5 px-3 py-2 text-xs text-amber-100"
              >
                {
                  warning
                }
              </p>
            ),
          )}
        </div>
      ) : null}
    </footer>
  );
}


function ChartError({
  message,
}: {
  message: string;
}) {
  return (
    <div className="rounded-xl border border-rose-300/20 bg-rose-300/5 px-4 py-6 text-center">
      <p className="text-sm font-medium text-rose-100">
        Unable to render chart
      </p>

      <p className="mt-1 text-xs text-rose-200/70">
        {
          message
        }
      </p>
    </div>
  );
}
