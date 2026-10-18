import type { ApiError, QuestRequest, QuestResponse } from "@/types/quest";
import { buildMockResponse } from "@/lib/mock";

// Mock is the default. Set NEXT_PUBLIC_USE_MOCK=false to hit the real backend.
const USE_MOCK = (process.env.NEXT_PUBLIC_USE_MOCK ?? "true") === "true";

// Dev-only: NEXT_PUBLIC_MOCK_SCENARIO=error | empty lets you preview those UI states.
const MOCK_SCENARIO = process.env.NEXT_PUBLIC_MOCK_SCENARIO;

const MOCK_DELAY_MS = 1500;

export class QuestApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "QuestApiError";
    this.code = code;
  }
}

function isApiError(body: unknown): body is ApiError {
  return (
    typeof body === "object" &&
    body !== null &&
    "error" in body &&
    typeof (body as ApiError).error?.message === "string"
  );
}

export async function generateQuests(req: QuestRequest): Promise<QuestResponse> {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, MOCK_DELAY_MS));
    if (MOCK_SCENARIO === "error") {
      throw new QuestApiError("MOCK_ERROR", "Our scouts got lost on the way.");
    }
    if (MOCK_SCENARIO === "empty") return { quests: [] };
    return buildMockResponse(req);
  }

  let res: Response;
  try {
    res = await fetch("/api/quest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  } catch {
    throw new QuestApiError("NETWORK_ERROR", "Couldn't reach the quest board. Check your connection and try again.");
  }

  const body: unknown = await res.json().catch(() => null);

  if (!res.ok) {
    if (isApiError(body)) throw new QuestApiError(body.error.code, body.error.message);
    throw new QuestApiError(`HTTP_${res.status}`, "Something went wrong generating quests. Please try again.");
  }

  return body as QuestResponse;
}
