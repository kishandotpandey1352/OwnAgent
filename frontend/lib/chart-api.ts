import type {
  ChartApiResponse,
  ChartRequest,
  ChartSpec,
} from "@/types/chart";


function getApiError(
  payload: unknown,
  fallback: string,
) {
  if (
    typeof payload !==
      "object" ||
    payload === null
  ) {
    return fallback;
  }

  const candidate =
    payload as Record<
      string,
      unknown
    >;

  if (
    typeof candidate.error ===
    "string"
  ) {
    return candidate.error;
  }

  if (
    typeof candidate.detail ===
    "string"
  ) {
    return candidate.detail;
  }

  return fallback;
}


export async function createChart(
  request: ChartRequest,
): Promise<ChartSpec> {
  const response = await fetch(
    "/api/data/chart",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify(
        request,
      ),
    },
  );

  const payload =
    (await response.json()) as
      ChartApiResponse;

  if (
    !response.ok ||
    !payload.ok
  ) {
    throw new Error(
      getApiError(
        payload,
        "Chart creation failed.",
      ),
    );
  }

  return payload;
}