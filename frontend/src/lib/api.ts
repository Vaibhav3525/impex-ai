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

export interface LeadPagination {
  total: number;
  page: number;
  page_size: number;
  items: Lead[];
}

export interface OutreachQueueSummary {
  total_queued: number;
  total_approved: number;
  total_rejected: number;
  total_sent: number;
  pending_emails: OutreachEmail[];
}

export interface KanbanColumn {
  stage: string;
  index: number;
  count: number;
  leads: Lead[];
  deals: Deal[];
}

export interface KanbanBoardResponse {
  stages: KanbanColumn[];
  total_leads: number;
  total_deals: number;
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
  getExportCsvUrl: (status?: string, minScore?: number) => {
    const q = new URLSearchParams();
    if (status) q.append("status_filter", status);
    if (minScore !== undefined) q.append("min_score", minScore.toString());
    return `${API_BASE_URL}/analytics/export-csv?${q.toString()}`;
  },

  // Leads
  getLeads: (params?: {
    status?: string;
    min_score?: number;
    limit?: number;
    page_size?: number;
    page?: number;
    country?: string;
    product_category?: string;
    pipeline_stage?: string;
    search?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.append("verification_status", params.status);
    if (params?.min_score !== undefined) q.append("min_score", params.min_score.toString());
    const size = params?.page_size || params?.limit || 100;
    q.append("page_size", size.toString());
    if (params?.page) q.append("page", params.page.toString());
    if (params?.country) q.append("country", params.country);
    if (params?.product_category) q.append("product_category", params.product_category);
    if (params?.pipeline_stage) q.append("pipeline_stage", params.pipeline_stage);
    if (params?.search) q.append("search", params.search);
    return request<LeadPagination>(`/leads?${q.toString()}`);
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

  // Autonomous Lead Discovery
  runAutonomousSearch: (payload: { commodity: string; country?: string; sources?: string[]; limit?: number; auto_ingest?: boolean; auto_verify?: boolean }) =>
    request<any>("/discover/autonomous-search", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  searchEmbassyDirectories: (payload: { country?: string; commodity?: string; auto_ingest?: boolean; auto_verify?: boolean }) =>
    request<any>("/discover/embassy-directories", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getLinkedInPersonas: (payload: { commodity: string; country: string; roles?: string[] }) =>
    request<any>("/discover/linkedin-personas", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Products & Exporter Profiles
  getProducts: (activeOnly: boolean = false) =>
    request<any[]>(`/products?active_only=${activeOnly}`),
  getProduct: (productId: string) =>
    request<any>(`/products/${productId}`),
  createProduct: (data: any) =>
    request<any>("/products", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateProduct: (productId: string, data: any) =>
    request<any>(`/products/${productId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteProduct: (productId: string) =>
    request<any>(`/products/${productId}`, {
      method: "DELETE",
    }),
  matchLeadsForProduct: (productId: string, limit: number = 50, minScore: number = 0) =>
    request<{
      product_profile: any;
      total_leads_evaluated: number;
      qualified_leads_count: number;
      top_matches: any[];
    }>(`/products/${productId}/match-leads?limit=${limit}&min_score=${minScore}`, {
      method: "POST",
    }),
  qualifyLeadAgainstProduct: (leadId: string, productId: string) =>
    request<any>(`/leads/${leadId}/qualify/${productId}`, {
      method: "POST",
    }),

  // CRM Pipeline & Deals
  getKanbanBoard: () => request<KanbanBoardResponse>("/pipeline/kanban"),
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
  getOutreachQueue: (status?: string, limit?: number) => {
    const q = new URLSearchParams();
    if (status) q.append("status_filter", status);
    if (limit) q.append("limit", limit.toString());
    return request<OutreachQueueSummary>(`/outreach/queue?${q.toString()}`);
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

  // Autonomous Cadence & Follow-Ups (PRD §7)
  getCadenceStatus: () =>
    request<{
      touch_1_sent: number;
      touch_2_queued_or_approved: number;
      touch_2_sent: number;
      touch_3_queued_or_approved: number;
      touch_3_sent: number;
      replied_and_halted: number;
      suppressed_and_halted: number;
      total_active_cadences: number;
    }>("/outreach/followups/status"),
  processDueFollowups: (params: { min_days?: number; force_advance?: boolean; limit?: number }) =>
    request<{
      eligible_leads: number;
      generated_count: number;
      generated_emails: any[];
      skipped_reasons: any[];
    }>("/outreach/followups/process", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  scheduleLeadNextFollowup: (leadId: string, force: boolean = false, minDays: number = 4) =>
    request<any>(`/outreach/followups/${leadId}/schedule-next?force=${force}&min_days=${minDays}`, {
      method: "POST",
    }),
  cancelLeadFollowups: (leadId: string, reason: string = "Manual Halt") =>
    request<any>(`/outreach/followups/${leadId}/cancel?reason=${encodeURIComponent(reason)}`, {
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

  // Proforma Invoice & Export Quotations
  getProformaInvoice: (dealId: string) =>
    request<any>(`/deals/${dealId}/proforma-invoice`),
  generateProformaInvoice: (dealId: string, payload?: any) =>
    request<any>(`/deals/${dealId}/proforma-invoice`, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }),
  listProformaInvoices: (limit: number = 50) =>
    request<any[]>(`/proforma-invoices?limit=${limit}`),
  getProformaInvoiceHtmlUrl: (dealId: string) =>
    `${API_BASE_URL}/deals/${dealId}/proforma-invoice/html`,
};

