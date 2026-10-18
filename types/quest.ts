// SHARED CONTRACT — locked. Do not change without telling both frontend and backend.

export type QuestRequest = {
  category: string; // e.g. "food", "outdoors", "arts", "nightlife", "games", "surprise me"
  startTime: string; // ISO 8601
  endTime: string; // ISO 8601
  budgetPerPerson: number; // USD
  maxDistanceMiles: number; // max radius from user location
  location: { lat: number; lng: number; label?: string };
  groupSize?: number; // default 1
};

export type Review = {
  author?: string;
  rating?: number; // 1-5
  snippet: string;
  sourceName: string; // "Google", "Yelp", etc.
  sourceUrl: string;
};

export type Stop = {
  id: string;
  order: number; // 1-based
  name: string;
  category: string;
  address: string;
  lat: number;
  lng: number;
  startTime?: string; // ISO 8601
  durationMinutes: number;
  estimatedCost: number; // per person, USD
  costIsEstimate: boolean; // show "~" and an "estimate" label if true
  distanceFromPreviousMiles: number; // from user's location for stop 1
  travelFromPreviousMinutes: number;
  travelMode: "driving" | "walking" | "transit";
  rating?: number;
  reviewCount?: number;
  reviewSummary: string; // AI-written 1-2 sentence summary of real reviews
  reviews: Review[]; // 0-3 real review snippets with source links
  sourceUrl?: string;
};

export type Quest = {
  id: string;
  title: string; // fun quest name, e.g. "Boba, Tide Pools, Sunset"
  tagline: string;
  totalCostPerPerson: number;
  totalDurationMinutes: number;
  totalTravelMinutes: number;
  totalDistanceMiles: number;
  stops: Stop[];
};

export type QuestResponse = { quests: Quest[] }; // usually 3 options

export type ApiError = { error: { code: string; message: string } };
