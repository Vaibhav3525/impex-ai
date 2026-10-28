/**
 * ImpEx AI — Frontend API Client
 * Connects Next.js 14 Dashboard to FastAPI backend at /api/v1
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface Lead {
  id: number;
  lead_id: string;
  company_name: string;
  country: string;
  city?: string;
  website?: string;
  product_category: string;
  contact_name?: string;
  job_title?: string;
  business_email?: string;
  phone_number?: string;
  source: string;
  source_url?: string;
  import_evidence?: string;
  verification_status: "Verified" | "Partially Verified" | "Unverified" | "Rejected";
  buyer_score: number;
  payment_risk_score?: number;
  risk_level?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_flags?: string[];
  pipeline_stage: string;
  outreach_status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface VerificationLog {
  id: number;
  lead_id: string;
  identity_score: number;
  relevance_score: number;
  website_score: number;
  email_score: number;
  import_evidence_score: number;
  independent_score: number;
  total_score: number;
  risk_level: string;
  detected_flags: string[];
  evidence_summary: string;
  verified_by: string;
  created_at: string;
}

export interface OutreachEmail {
  id: number;
  email_id: string;
  lead_id: string;
  product_id?: string;
  to_email: string;
  to_name?: string;
  company_name: string;
  country: string;
  subject: string;
  body_text: string;
  sequence_step: number;
  status: "Queued" | "Approved" | "Rejected" | "Sent" | "Failed" | "Replied" | "Suppressed";
  approval_mode: string;
  approved_by?: string;
  rejection_reason?: string;
  sent_at?: string;
  created_at: string;
}

export interface Deal {
  id: number;
  deal_id: string;
  lead_id: string;
  product_name: string;
  hs_code?: string;
  required_quantity?: string;
  target_price?: number;
  currency: string;
  destination_port?: string;
  incoterms?: string;
  payment_terms?: string;
  stage: string;
  payment_risk_status: string;
  payment_risk_notes?: string;
  quotation_amount?: number;
  confirmed_order_value?: number;
  notes?: string;
  created_at: string;
}

export interface BuyerReply {
  id: number;
  lead_id: string;
  deal_id?: string;
  from_email: string;
  subject: string;
  raw_body: string;
  received_at: string;
  classification: string;
  confidence_score: number;
  extracted_product?: string;
  extracted_quantity?: string;
  extracted_target_price?: number;
  extracted_delivery_port?: string;
  extracted_payment_method?: string;
  extracted_next_action?: string;
  reviewed_by_human: string;
  human_notes?: string;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {}
    throw new Error(`API Error [${res.status}] ${url}: ${errorDetail}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  // System Health
  getHealth: () => request<{ status: string; app: string; version: string }>("/health"),

  // Analytics & PRD Reporting
  getDashboard: () => request<any>("/analytics/dashboard"),
  getExecutiveReport: () => request<any>("/analytics/executive-report"),

  // Leads
  getLeads: (params?: { status?: string; min_score?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.append("verification_status", params.status);
    if (params?.min_score !== undefined) q.append("min_score", params.min_score.toString());
    if (params?.limit) q.append("limit", params.limit.toString());
    return request<Lead[]>(`/leads?${q.toString()}`);
  },
  getLead: (leadId: string) => request<Lead>(`/leads/${leadId}`),
  getLeadAuditTrail: (leadId: string) => request<VerificationLog[]>(`/leads/${leadId}/audit-trail`),
  getReviewQueue: () => request<Lead[]>("/leads/review-queue"),
  getHighRiskQueue: () => request<Lead[]>("/leads/high-risk"),
  manualVerifyLead: (leadId: string, payload: { verification_status: string; override_score?: number; reason: string }) =>
    request<Lead>(`/leads/${leadId}/verify-manual`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  verifyBatch: (params: { limit?: number; only_unverified?: boolean; run_live_checks?: boolean }) =>
    request<any>("/leads/verify-batch", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  // Products
  getProducts: () => request<any[]>("/products"),
  createProduct: (data: any) =>
    request<any>("/products", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  matchLeadsForProduct: (productId: string, limit: number = 50) =>
    request<any[]>(`/products/${productId}/match-leads?limit=${limit}`, {
      method: "POST",
    }),

  // CRM Pipeline & Deals
  getKanbanBoard: () => request<any>("/pipeline/kanban"),
  getPipelineSummary: () => request<any>("/pipeline/summary"),
  updateLeadStage: (leadId: string, newStage: string, notes?: string) =>
    request<Lead>(`/pipeline/leads/${leadId}/stage`, {
      method: "PATCH",
      body: JSON.stringify({ new_stage: newStage, notes }),
    }),
  getDeals: (stage?: string) => {
    const q = stage ? `?stage=${encodeURIComponent(stage)}` : "";
    return request<Deal[]>(`/deals${q}`);
  },
  createDeal: (deal: any) =>
    request<Deal>("/deals", {
      method: "POST",
      body: JSON.stringify(deal),
    }),
  updateDealStage: (dealId: string, newStage: string, notes?: string) =>
    request<Deal>(`/deals/${dealId}/stage`, {
      method: "PATCH",
      body: JSON.stringify({ new_stage: newStage, notes }),
    }),
  evaluateDealRisk: (dealId: string) =>
    request<any>(`/deals/${dealId}/financial-risk`, {
      method: "POST",
    }),

  // Outreach & Mode A Approvals
  getOutreachQueue: (status?: string) => {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<OutreachEmail[]>(`/outreach/queue${q}`);
  },
  composeOutreachEmail: (leadId: string, params?: { product_id?: string; sequence_step?: number }) =>
    request<OutreachEmail>(`/outreach/${leadId}/compose`, {
      method: "POST",
      body: JSON.stringify(params || {}),
    }),
  approveOutreachEmail: (emailId: string) =>
    request<OutreachEmail>(`/outreach/emails/${emailId}/approve`, {
      method: "POST",
    }),
  rejectOutreachEmail: (emailId: string, reason: string) =>
    request<OutreachEmail>(`/outreach/emails/${emailId}/reject`, {
      method: "POST",
      body: JSON.stringify({ rejection_reason: reason }),
    }),
  dispatchEmail: (emailId: string) =>
    request<any>(`/outreach/emails/${emailId}/send`, {
      method: "POST",
    }),
  dispatchBatch: (limit: number = 10) =>
    request<any>(`/outreach/dispatch-batch?limit=${limit}`, {
      method: "POST",
    }),

  // Replies & Inbound Intelligence
  getReplies: (params?: { classification?: string; reviewed_status?: string }) => {
    const q = new URLSearchParams();
    if (params?.classification) q.append("classification", params.classification);
    if (params?.reviewed_status) q.append("reviewed_status", params.reviewed_status);
    return request<BuyerReply[]>(`/replies?${q.toString()}`);
  },
  processIncomingReply: (replyData: { lead_id: string; from_email: string; subject: string; raw_body: string }) =>
    request<BuyerReply>("/replies/incoming", {
      method: "POST",
      body: JSON.stringify(replyData),
    }),
  reviewReply: (replyId: number, payload: { review_status: string; human_notes?: string; override_classification?: string }) =>
    request<BuyerReply>(`/replies/${replyId}/review`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
};
