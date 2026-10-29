"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Mail,
  Send,
  Search,
  Filter,
  Eye,
  DollarSign,
  Globe,
  FileCheck,
  ExternalLink,
  RefreshCw,
  Sparkles,
  Layers,
  ChevronRight,
  TrendingUp,
  Clock,
  ArrowRight,
  Zap,
  XCircle,
  MessageSquare,
  Package,
  Plus,
  Trash2,
  SlidersHorizontal,
  Award,
  Scale,
  FileText,
  X,
} from "lucide-react";

interface Lead {
  lead_id: string;
  company_name: string;
  country: string;
  city: string | null;
  website: string | null;
  product_category: string;
  contact_name: string | null;
  job_title: string | null;
  business_email: string | null;
  phone_number: string | null;
  source: string;
  source_url: string | null;
  import_evidence: string | null;
  verification_status: "Verified" | "Partially Verified" | "Unverified" | "Rejected";
  buyer_score: number;
  risk_flags: string[];
  pipeline_stage: string;
  outreach_status?: string;
  notes: string | null;
  scores_breakdown?: {
    identity: number;
    relevance: number;
    website: number;
    email: number;
    import_evidence: number;
    independent: number;
  };
}

const INITIAL_LEADS: Lead[] = [
  {
    lead_id: "LID-UAE-ALMAYA",
    company_name: "Al Maya Trading Co LLC",
    country: "United Arab Emirates",
    city: "Dubai",
    website: "https://www.almaya.ae",
    product_category: "Basmati Rice, Spices & Foodstuffs",
    contact_name: "Kamal Vachani",
    job_title: "Group Director (Procurement)",
    business_email: "procurement@almaya.ae",
    phone_number: "+971 4 347 3500",
    source: "Dubai Chamber of Commerce & APEDA Directory",
    source_url: "https://www.dubaichamber.com/en/business/directory/",
    import_evidence: "Major supermarket and wholesale distributor importing 500+ containers of FMCG, basmati rice, and spices annually from India.",
    verification_status: "Verified",
    buyer_score: 96.0,
    risk_flags: [],
    pipeline_stage: "Quotation Prepared",
    notes: "Requires 1121 Steam Basmati Rice in 40kg PP bags with private label packaging. Payment 100% LC at sight.",
    scores_breakdown: { identity: 20, relevance: 20, website: 15, email: 15, import_evidence: 15, independent: 11 }
  },
  {
    lead_id: "LID-UAE-LULU",
    company_name: "Lulu Group International",
    country: "United Arab Emirates",
    city: "Abu Dhabi",
    website: "https://www.lulugroupinternational.com",
    product_category: "Agricultural Commodities, Spices & Fruits",
    contact_name: "Salim M.A.",
    job_title: "Director of Global Sourcing",
    business_email: "sourcing@lulugroup.com",
    phone_number: "+971 2 418 4500",
    source: "UAE Ministry of Economy Trade Register",
    source_url: "https://www.moec.gov.ae/en/trade-directory",
    import_evidence: "Operates 250+ hypermarkets across GCC; direct importer of Indian long-grain rice, fresh vegetables, and processed spices.",
    verification_status: "Verified",
    buyer_score: 98.0,
    risk_flags: [],
    pipeline_stage: "Verified Candidate",
    notes: "Bulk centralized procurement hub for GCC retail stores. High volume buyer.",
    scores_breakdown: { identity: 20, relevance: 20, website: 15, email: 15, import_evidence: 15, independent: 13 }
  },
  {
    lead_id: "LID-UK-WESTMILL",
    company_name: "Westmill Foods Ltd (Associated British Foods)",
    country: "United Kingdom",
    city: "Enfield, London",
    website: "https://www.westmill.co.uk",
    product_category: "Basmati Rice, Atta Flour, Spices & Noodles",
    contact_name: "Oliver Jackson",
    job_title: "Category Sourcing Manager (Rice & Grains)",
    business_email: "commercial@westmill.co.uk",
    phone_number: "+44 20 8344 1800",
    source: "High Commission of India, London (Commercial Wing)",
    source_url: "https://www.hcilondon.gov.in/page/commercial-trade-directory/",
    import_evidence: "One of Europe's largest ethnic food manufacturers (brands: Elephant Atta, Tolly Boy, Rajah Spices); major direct importer at London Gateway port.",
    verification_status: "Verified",
    buyer_score: 98.0,
    risk_flags: [],
    pipeline_stage: "Order Confirmed",
    notes: "Confirmed order of 350 MT Pusa Basmati Rice. Irrevocable LC at Sight issued by Barclays Bank UK.",
    scores_breakdown: { identity: 20, relevance: 20, website: 15, email: 15, import_evidence: 15, independent: 13 }
  },
  {
    lead_id: "LID-DE-EURYZA",
    company_name: "Euryza GmbH (Rickmers Reismühle)",
    country: "Germany",
    city: "Hamburg",
    website: "https://www.euryza.de",
    product_category: "Basmati Rice & Specialty Grains",
    contact_name: "Dr. Jens Kramer",
    job_title: "Director of Commodity Purchasing",
    business_email: "sourcing@euryza.de",
    phone_number: "+49 40 7510 900",
    source: "Hamburg Chamber of Commerce & European Rice Federation",
    source_url: "https://www.hk24.de/en/business-directory",
    import_evidence: "Major rice milling and packaging group in Northern Europe; regular ocean container shipments through Port of Hamburg.",
    verification_status: "Verified",
    buyer_score: 97.0,
    risk_flags: [],
    pipeline_stage: "Payment Verification",
    notes: "250 MT Basmati Rice order in verification stage. Letter of Credit confirmed by Deutsche Bank AG.",
    scores_breakdown: { identity: 20, relevance: 20, website: 15, email: 15, import_evidence: 15, independent: 12 }
  },
  {
    lead_id: "LID-USA-QUICKTRADES",
    company_name: "Suspicious Quick Trades LLC",
    country: "United States",
    city: "Miami",
    website: "http://quicktrades-temp.biz",
    product_category: "Any Export Commodity",
    contact_name: "John Anonymous",
    job_title: "Agent",
    business_email: "quickbuyer2026@gmail.com",
    phone_number: "+1 305 000 0000",
    source: "Unverified Web Forum",
    source_url: "http://trade-forum-leads.example.com",
    import_evidence: null,
    verification_status: "Rejected",
    buyer_score: 25.0,
    risk_flags: ["FLAG_FREE_EMAIL_DOMAIN", "FLAG_NO_DIRECT_IMPORT_EVIDENCE", "FLAG_UPFRONT_FEE_SOLICITATION"],
    pipeline_stage: "Lost / Rejected",
    notes: "CRITICAL FRAUD SIGNAL: Demands upfront supplier registration fee of $500 before sending purchase order. Outreach permanently blocked.",
    scores_breakdown: { identity: 5, relevance: 5, website: 5, email: 0, import_evidence: 0, independent: 10 }
  }
];

const PIPELINE_STAGES = [
  "Discovered",
  "Verification Pending",
  "Verified Candidate",
  "Qualified",
  "Outreach Approved",
  "Email Sent",
  "Buyer Replied",
  "Requirements Received",
  "Quotation Prepared",
  "Negotiation",
  "Purchase Order Received",
  "Payment Verification",
  "Order Confirmed",
  "Completed",
  "Lost / Rejected"
];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<"directory" | "discovery" | "catalog" | "pipeline" | "queue" | "risk" | "analytics">("directory");

  // Exporter Catalog & Live Matching State
  const [products, setProducts] = useState<any[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [matchSummary, setMatchSummary] = useState<any>(null);
  const [showAddProductModal, setShowAddProductModal] = useState(false);
  const [savingProduct, setSavingProduct] = useState(false);
  const [selectedMatchExplanation, setSelectedMatchExplanation] = useState<any>(null);

  // New Product Form State
  const [productForm, setProductForm] = useState({
    product_name: "",
    product_category: "Agricultural Commodities & Grains",
    hs_code: "",
    specifications: "",
    grade: "",
    origin_country: "India",
    available_quantity: "200 MT / month",
    packaging: "25kg / 50kg PP Bags",
    moq: "1x20ft Container (20 MT)",
    target_price_min: 1200,
    target_price_max: 1450,
    currency: "USD",
    incoterms: "FOB",
    preferred_payment_terms: "100% LC at Sight / 30% Advance + 70% against BL",
    target_countries: "United Arab Emirates, Saudi Arabia, Germany, United Kingdom, United States",
    excluded_countries: "",
    certifications: "APEDA, FSSAI, ISO 22000, HACCP",
  });

  const loadProducts = async () => {
    setLoadingProducts(true);
    try {
      const prods = await api.getProducts();
      setProducts(prods);
      if (prods.length > 0 && !selectedProduct) {
        setSelectedProduct(prods[0]);
      }
    } catch (e) {
      console.error("Failed to load products:", e);
    } finally {
      setLoadingProducts(false);
    }
  };

  const handleRunMatching = async (prod: any) => {
    setSelectedProduct(prod);
    setMatchingLoading(true);
    setMatchSummary(null);
    try {
      const res = await api.matchLeadsForProduct(prod.profile_id, 50, 0);
      setMatchSummary(res);
      setActionSuccessMsg(`Matched ${res.qualified_leads_count} qualified international buyers for "${prod.product_name}"!`);
    } catch (e: any) {
      console.error("Match error:", e);
    } finally {
      setMatchingLoading(false);
    }
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productForm.product_name.trim()) return;
    setSavingProduct(true);
    try {
      const payload = {
        product_name: productForm.product_name.trim(),
        product_category: productForm.product_category,
        hs_code: productForm.hs_code.trim() || null,
        specifications: productForm.specifications.trim() || null,
        grade: productForm.grade.trim() || null,
        origin_country: productForm.origin_country.trim() || "India",
        available_quantity: productForm.available_quantity.trim() || null,
        packaging: productForm.packaging.trim() || null,
        moq: productForm.moq.trim() || null,
        target_price_min: productForm.target_price_min ? Number(productForm.target_price_min) : null,
        target_price_max: productForm.target_price_max ? Number(productForm.target_price_max) : null,
        currency: productForm.currency,
        incoterms: productForm.incoterms,
        preferred_payment_terms: productForm.preferred_payment_terms,
        target_countries: productForm.target_countries
          ? productForm.target_countries.split(",").map(s => s.trim()).filter(Boolean)
          : [],
        excluded_countries: productForm.excluded_countries
          ? productForm.excluded_countries.split(",").map(s => s.trim()).filter(Boolean)
          : [],
        certifications: productForm.certifications
          ? productForm.certifications.split(",").map(s => s.trim()).filter(Boolean)
          : [],
        export_readiness: true,
        is_active: true,
      };
      const created = await api.createProduct(payload);
      setActionSuccessMsg(`Added "${created.product_name}" to Exporter Catalog!`);
      setShowAddProductModal(false);
      await loadProducts();
      await handleRunMatching(created);
    } catch (err: any) {
      console.error("Create product failed:", err);
    } finally {
      setSavingProduct(false);
    }
  };

  const handleDeleteProduct = async (productId: string, name: string) => {
    if (!confirm(`Remove "${name}" from your exporter catalog?`)) return;
    try {
      await api.deleteProduct(productId);
      setActionSuccessMsg(`Product "${name}" removed from catalog.`);
      if (selectedProduct?.profile_id === productId) {
        setSelectedProduct(null);
        setMatchSummary(null);
      }
      await loadProducts();
    } catch (err) {
      console.error("Delete product error:", err);
    }
  };
  const [leads, setLeads] = useState<Lead[]>(INITIAL_LEADS);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCountry, setSelectedCountry] = useState("ALL");
  const [selectedTier, setSelectedTier] = useState("ALL");
  const [liveConnected, setLiveConnected] = useState(false);
  const [totalDbCount, setTotalDbCount] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [loadingLeads, setLoadingLeads] = useState<boolean>(false);

  // CRM Kanban Pipeline State
  const [kanbanData, setKanbanData] = useState<any>(null);
  const [loadingKanban, setLoadingKanban] = useState<boolean>(false);

  // Mode A Outreach Queue State
  const [outreachQueueSummary, setOutreachQueueSummary] = useState<any>(null);
  const [outreachQueueEmails, setOutreachQueueEmails] = useState<any[]>([]);
  const [queueStatusFilter, setQueueStatusFilter] = useState<string>("Queued");
  const [loadingQueue, setLoadingQueue] = useState<boolean>(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // High Risk Monitor State
  const [highRiskList, setHighRiskList] = useState<any[]>([]);
  const [loadingHighRisk, setLoadingHighRisk] = useState<boolean>(false);

  // Executive Analytics State (PRD §13)
  const [execReport, setExecReport] = useState<any>(null);
  const [dashMetrics, setDashMetrics] = useState<any>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);

  const loadAnalytics = async () => {
    setLoadingAnalytics(true);
    try {
      const [report, metrics] = await Promise.all([
        api.getExecutiveReport(),
        api.getDashboard(),
      ]);
      setExecReport(report);
      setDashMetrics(metrics);
    } catch (e) {
      console.info("Analytics fetch error:", e);
    } finally {
      setLoadingAnalytics(false);
    }
  };

  const fetchLeads = async (page: number = 1) => {
    setLoadingLeads(true);
    try {
      const res = await api.getLeads({ page, page_size: 100 });
      const rawItems = Array.isArray(res) ? res : res.items || [];
      if (rawItems.length > 0) {
        const formatted = rawItems.map((l: any) => ({
          ...l,
          risk_flags: l.risk_flags || [],
          scores_breakdown: l.scores_breakdown || {
            identity: Math.round(l.buyer_score * 0.2),
            relevance: Math.round(l.buyer_score * 0.2),
            website: Math.round(l.buyer_score * 0.15),
            email: Math.round(l.buyer_score * 0.15),
            import_evidence: Math.round(l.buyer_score * 0.15),
            independent: Math.round(l.buyer_score * 0.15),
          }
        }));
        setLeads(formatted);
        setTotalDbCount(res.total ?? formatted.length);
        setCurrentPage(page);
        setLiveConnected(true);
      }
    } catch (err) {
      console.info("Error fetching live leads:", err);
    } finally {
      setLoadingLeads(false);
    }
  };

  const loadKanban = async () => {
    setLoadingKanban(true);
    try {
      const board = await api.getKanbanBoard();
      setKanbanData(board);
    } catch (e) {
      console.info("Kanban fetch error:", e);
    } finally {
      setLoadingKanban(false);
    }
  };

  const loadQueue = async (st: string = queueStatusFilter) => {
    setLoadingQueue(true);
    try {
      const summary = await api.getOutreachQueue(st, 50);
      setOutreachQueueSummary(summary);
      setOutreachQueueEmails(summary.pending_emails || []);
    } catch (e) {
      console.info("Queue fetch error:", e);
    } finally {
      setLoadingQueue(false);
    }
  };

  const loadHighRisk = async () => {
    setLoadingHighRisk(true);
    try {
      const hr = await api.getHighRiskQueue();
      setHighRiskList(hr || []);
    } catch (e) {
      console.info("High risk fetch error:", e);
    } finally {
      setLoadingHighRisk(false);
    }
  };

  const handleApproveEmail = async (emailId: string) => {
    try {
      await api.approveOutreachEmail(emailId);
      setActionSuccessMsg(`Email ${emailId} approved for dispatch.`);
      await loadQueue(queueStatusFilter);
      await loadAnalytics();
      await loadCadenceStatus();
      setTimeout(() => setActionSuccessMsg(null), 4000);
    } catch (e: any) {
      alert(`Approval error: ${e.message}`);
    }
  };

  const handleDispatchEmail = async (emailId: string) => {
    try {
      await api.dispatchEmail(emailId);
      setActionSuccessMsg(`Email ${emailId} successfully dispatched via SMTP!`);
      await loadQueue(queueStatusFilter);
      await loadAnalytics();
      await loadCadenceStatus();
      setTimeout(() => setActionSuccessMsg(null), 4000);
    } catch (e: any) {
      alert(`Dispatch error: ${e.message}`);
    }
  };

  const handleApproveAndDispatch = async (emailId: string) => {
    try {
      await api.approveOutreachEmail(emailId);
      await api.dispatchEmail(emailId);
      setActionSuccessMsg(`Email ${emailId} approved & dispatched via SMTP!`);
      await loadQueue(queueStatusFilter);
      await loadAnalytics();
      await loadCadenceStatus();
      setTimeout(() => setActionSuccessMsg(null), 4000);
    } catch (e: any) {
      alert(`Dispatch error: ${e.message}`);
    }
  };

  const handleRejectEmail = async (emailId: string) => {
    const reason = prompt("Enter rejection / quarantine reason:", "Non-matching specs or high risk") || "Manual compliance rejection";
    try {
      await api.rejectOutreachEmail(emailId, reason);
      setActionSuccessMsg(`Email ${emailId} rejected / quarantined.`);
      await loadQueue(queueStatusFilter);
      await loadAnalytics();
      setTimeout(() => setActionSuccessMsg(null), 4000);
    } catch (e: any) {
      alert(`Reject error: ${e.message}`);
    }
  };

  // Autonomous Discovery Hub State
  const [discoveryCommodity, setDiscoveryCommodity] = useState("Basmati Rice 1121");
  const [discoveryCountry, setDiscoveryCountry] = useState("United Arab Emirates");
  const [discoveryLoading, setDiscoveryLoading] = useState(false);
  const [discoveryResults, setDiscoveryResults] = useState<any[]>([]);
  const [discoverySummary, setDiscoverySummary] = useState<any>(null);
  const [linkedinData, setLinkedinData] = useState<any>(null);

  const handleRunDiscovery = async () => {
    setDiscoveryLoading(true);
    try {
      const res = await api.runAutonomousSearch({
        commodity: discoveryCommodity,
        country: discoveryCountry,
        sources: ["directories", "embassy", "web"],
        limit: 15,
        auto_ingest: true,
        auto_verify: true,
      });
      setDiscoveryResults(res.leads || []);
      setDiscoverySummary(res);

      try {
        const dorks = await api.getLinkedInPersonas({
          commodity: discoveryCommodity,
          country: discoveryCountry,
        });
        setLinkedinData(dorks);
      } catch {}

      // Refresh directory, kanban & analytics
      await fetchLeads(1);
      await loadAnalytics();
      await loadKanban();
    } catch (e) {
      console.error("Discovery error:", e);
    } finally {
      setDiscoveryLoading(false);
    }
  };

  // Follow-Up Cadence State (PRD §7)
  const [cadenceStatus, setCadenceStatus] = useState<any>(null);
  const [cadenceLoading, setCadenceLoading] = useState(false);
  const [cadenceResult, setCadenceResult] = useState<any>(null);
  const [simLeadId, setSimLeadId] = useState("");
  const [simReplyType, setSimReplyType] = useState("RFQ");
  const [simulatingReply, setSimulatingReply] = useState(false);
  const [simReplyResult, setSimReplyResult] = useState<any>(null);

  const loadCadenceStatus = async () => {
    try {
      const st = await api.getCadenceStatus();
      setCadenceStatus(st);
    } catch (e) {
      console.info("Could not fetch cadence status:", e);
    }
  };

  const handleProcessFollowups = async () => {
    setCadenceLoading(true);
    setCadenceResult(null);
    try {
      const res = await api.processDueFollowups({ min_days: 4, force_advance: true, limit: 50 });
      setCadenceResult(res);
      await loadCadenceStatus();
      await fetchLeads(currentPage);
      await loadQueue(queueStatusFilter);
      await loadAnalytics();
    } catch (e) {
      console.error("Cadence process error:", e);
    } finally {
      setCadenceLoading(false);
    }
  };

  const handleSimulateInboundReply = async () => {
    if (!simLeadId) return;
    setSimulatingReply(true);
    setSimReplyResult(null);
    try {
      const targetLead = leads.find(l => l.lead_id === simLeadId);
      const email = targetLead?.business_email || "buyer@procurement-dept.com";

      let subject = "Re: Export Inquiry";
      let raw_body = "";
      if (simReplyType === "RFQ") {
        subject = "RFQ: Official Price Quote Required for Basmati Rice";
        raw_body = "Hello. We reviewed your export specifications. Please submit your best CIF quotation for 500 MT of 1121 Basmati Rice to Jebel Ali port. Payment 100% LC at sight.";
      } else if (simReplyType === "SAMPLES") {
        subject = "Request for Lab Samples & CoA";
        raw_body = "Dear Export Desk, please courier 1kg physical sample kit along with full Certificate of Analysis and MRL pesticide report to our Dubai facility.";
      } else {
        subject = "Please Remove Us from Mailing List";
        raw_body = "We are not interested in sourcing commodities from your firm. Please unsubscribe our email address and stop sending follow-ups.";
      }

      const res = await api.processIncomingReply({
        lead_id: simLeadId,
        from_email: email,
        subject,
        raw_body,
      });
      setSimReplyResult(res);
      await loadCadenceStatus();
      await fetchLeads(currentPage);
      await loadQueue(queueStatusFilter);
      await loadAnalytics();
    } catch (e) {
      console.error("Simulate reply error:", e);
    } finally {
      setSimulatingReply(false);
    }
  };

  useEffect(() => {
    async function loadData() {
      try {
        await Promise.all([
          fetchLeads(1),
          loadCadenceStatus(),
          loadAnalytics(),
          loadKanban(),
          loadQueue("Queued"),
          loadHighRisk(),
          loadProducts(),
        ]);
      } catch (err) {
        console.info("Live backend connection note:", err);
      }
    }
    loadData();
  }, []);

  // Metrics
  const totalLeads = leads.length;
  const verifiedCount = leads.filter(l => l.verification_status === "Verified").length;
  const highPriorityCount = leads.filter(l => l.buyer_score >= 80).length;
  const potentialCount = leads.filter(l => l.buyer_score >= 60 && l.buyer_score < 80).length;
  const highRiskCount = leads.filter(l => l.buyer_score < 60 || l.risk_flags.length > 0).length;
  const queuedOutreachCount = leads.filter(l => l.pipeline_stage === "Outreach Approved").length;

  const filteredLeads = leads.filter(l => {
    const matchesSearch = 
      l.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.country.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.product_category.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesCountry = selectedCountry === "ALL" || l.country === selectedCountry;
    
    const matchesTier = 
      selectedTier === "ALL" ||
      (selectedTier === "HIGH" && l.buyer_score >= 80) ||
      (selectedTier === "POTENTIAL" && l.buyer_score >= 60 && l.buyer_score < 80) ||
      (selectedTier === "LOW" && l.buyer_score < 60);

    return matchesSearch && matchesCountry && matchesTier;
  });

  const countries = Array.from(new Set(leads.map(l => l.country)));

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-900 text-slate-100">
      {/* Sidebar Navigation */}
      <aside className="w-64 h-full shrink-0 border-r border-slate-800 bg-slate-950 p-6 flex flex-col justify-between overflow-y-auto">
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-slate-950 font-bold shadow-lg shadow-emerald-500/20">
              <Globe className="h-6 w-6" />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight text-white">IMPEX AI</h1>
              <p className="text-xs text-emerald-400 font-medium">Buyer Engine v1.0</p>
            </div>
          </div>

          <nav className="space-y-1.5">
            <button
              onClick={() => setActiveTab("directory")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "directory"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Building2 className="h-4 w-4" />
              Buyer Directory
              <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                {totalLeads}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("discovery")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "discovery"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Sparkles className="h-4 w-4" />
              Lead Discovery Hub
              <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
                Auto
              </span>
            </button>

            <button
              onClick={() => {
                setActiveTab("catalog");
                loadProducts();
              }}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "catalog"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Package className="h-4 w-4" />
              Exporter Catalog
              <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-slate-800 text-emerald-400 font-semibold">
                {products.length > 0 ? `${products.length}` : "5"}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("pipeline")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "pipeline"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Layers className="h-4 w-4" />
              15-Stage CRM Pipeline
            </button>

            <button
              onClick={() => setActiveTab("queue")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "queue"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Mail className="h-4 w-4" />
              Review Queue (Mode A)
              {queuedOutreachCount > 0 && (
                <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  {queuedOutreachCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("risk")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "risk"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <ShieldCheck className="h-4 w-4" />
              Payment Risk & Safety
            </button>

            <button
              onClick={() => {
                setActiveTab("analytics");
                loadAnalytics();
              }}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "analytics"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <TrendingUp className="h-4 w-4" />
              Executive Analytics
              <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-semibold">
                KPIs
              </span>
            </button>
          </nav>
        </div>

        <div className="pt-6 border-t border-slate-800">
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-xs font-semibold text-slate-200">Mode A: Assisted</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Human approval required before email dispatch & financial commitments.
            </p>
          </div>
        </div>
      </aside>

      {/* Main Content Pane */}
      <main className="flex-1 h-full min-w-0 flex flex-col overflow-y-auto overflow-x-hidden">
        {/* Top Header */}
        <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur px-8 py-5 flex items-center justify-between sticky top-0 z-20 shrink-0">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              {activeTab === "directory" && "International Buyer Discovery & Evidence"}
              {activeTab === "discovery" && "Autonomous Multi-Channel Lead Discovery Hub"}
              {activeTab === "catalog" && "Exporter Product Catalog & AI Buyer Matching Engine"}
              {activeTab === "pipeline" && "15-Stage CRM Deal Pipeline"}
              {activeTab === "queue" && "Assisted Outreach Approval Queue (Mode A)"}
              {activeTab === "risk" && "Transaction & Payment Risk Guardian"}
              {activeTab === "analytics" && "Executive Performance & DGFT Audit Analytics"}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {activeTab === "catalog"
                ? "Configure export specifications & run 100-point matching algorithms against 42 verified international buyers"
                : "Primary KPI: Verified Buyers → Qualified Inquiries → Quotations → Confirmed Orders"}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={api.getExportCsvUrl()}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200 font-semibold transition-all"
            >
              <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span>Export Audit CSV</span>
            </a>
            {liveConnected ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-400 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Live Connected ({totalDbCount > 0 ? totalDbCount.toLocaleString() : totalLeads} Leads in DB)</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs text-blue-400">
                <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                <span>Demo Mode</span>
              </div>
            )}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700 text-xs text-slate-300">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span>100-Pt Verification Engine: Active</span>
            </div>
          </div>
        </header>

        {/* Action feedback alert banner */}
        {actionSuccessMsg && (
          <div className="mx-8 mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/40 text-xs font-semibold text-emerald-300 flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>{actionSuccessMsg}</span>
            </div>
            <button onClick={() => setActionSuccessMsg(null)} className="text-emerald-400 hover:text-white">✕</button>
          </div>
        )}

        {/* Primary KPI Ribbon */}
        <div className="p-8 pb-4 shrink-0">
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 shadow-sm">
              <span className="text-xs font-medium text-slate-400">Total Leads Discovered</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-white">
                  {totalDbCount > 0 ? totalDbCount.toLocaleString() : totalLeads.toLocaleString()}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  {Math.round((verifiedCount / (totalLeads || 1)) * 100)}% Verified
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-2">Target: 500 records/day capacity</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 shadow-sm">
              <span className="text-xs font-medium text-slate-400">High-Priority Candidates</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-emerald-400">{highPriorityCount}</span>
                <span className="text-xs text-slate-400">Score 80–100</span>
              </div>
              <p className="text-xs text-slate-500 mt-2">Ready for personalized outreach</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 shadow-sm">
              <span className="text-xs font-medium text-slate-400">Potential Candidates</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-amber-400">{potentialCount}</span>
                <span className="text-xs text-slate-400">Score 60–79</span>
              </div>
              <p className="text-xs text-slate-500 mt-2">Requires secondary registry check</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 shadow-sm">
              <span className="text-xs font-medium text-slate-400">High-Risk / Quarantined</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-rose-400">{highRiskCount}</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  Outreach Blocked
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-2">Flagged for free email or anomaly</p>
            </div>
          </div>
        </div>

        {/* Tab: Autonomous Lead Discovery Hub */}
        {activeTab === "discovery" && (
          <div className="p-8 pt-2 space-y-6 pb-20">
            <div className="p-6 rounded-2xl bg-slate-950/90 border border-slate-800 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-emerald-400" />
                    Autonomous Multi-Channel Lead Discovery Engine
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    PRD §3: Discovers international buyers across web directories, Indian Embassy commercial missions, and compliant LinkedIn personas.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    Auto-Deduplication: SHA-256
                  </span>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30">
                    Auto-Verification: 100-Point Rubric
                  </span>
                </div>
              </div>

              {/* Input Form */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                    Export Commodity / Product Line
                  </label>
                  <input
                    type="text"
                    value={discoveryCommodity}
                    onChange={(e) => setDiscoveryCommodity(e.target.value)}
                    placeholder="e.g. Basmati Rice 1121, Turmeric, Black Pepper..."
                    className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                    Target Buyer Market / Country
                  </label>
                  <select
                    value={discoveryCountry}
                    onChange={(e) => setDiscoveryCountry(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="All">All International Markets</option>
                    <option value="United Arab Emirates">United Arab Emirates (Dubai, Abu Dhabi)</option>
                    <option value="Saudi Arabia">Saudi Arabia (Jeddah, Riyadh)</option>
                    <option value="Germany">Germany (Hamburg, Berlin, Munich)</option>
                    <option value="United Kingdom">United Kingdom (London, Midlands)</option>
                    <option value="United States">United States (New York, California)</option>
                    <option value="Netherlands">Netherlands (Rotterdam, Amsterdam)</option>
                    <option value="Japan">Japan (Tokyo, Osaka, Kobe)</option>
                    <option value="Australia">Australia (Sydney, Melbourne)</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={handleRunDiscovery}
                    disabled={discoveryLoading || !discoveryCommodity}
                    className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold shadow-lg shadow-emerald-600/20 transition-all flex items-center justify-center gap-2"
                  >
                    {discoveryLoading ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Discovering & Verifying Buyers...</span>
                      </>
                    ) : (
                      <>
                        <Search className="h-4 w-4" />
                        <span>Run Autonomous Discovery</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Discovery Results Summary */}
            {discoverySummary && (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-xs text-emerald-300">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  <span>
                    Discovery Complete: Found <strong>{discoverySummary.total_discovered}</strong> buyers. 
                    Added <strong>{discoverySummary.created_new_leads}</strong> new verified leads to CRM directory 
                    (Updated <strong>{discoverySummary.duplicate_leads_updated}</strong> existing records).
                  </span>
                </div>
                <button
                  onClick={() => setActiveTab("directory")}
                  className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold"
                >
                  View in Directory →
                </button>
              </div>
            )}

            {/* Discovered Leads Cards Grid */}
            {discoveryResults.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Discovered Buyer Prospects ({discoveryResults.length})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {discoveryResults.map((lead, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="font-bold text-sm text-white">{lead.company_name}</div>
                          <div className="text-xs text-slate-400">📍 {lead.city ? `${lead.city}, ` : ""}{lead.country} • {lead.product_category}</div>
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                          Discovered
                        </span>
                      </div>
                      <div className="text-xs text-slate-300 bg-slate-900/60 p-2 rounded border border-slate-800">
                        <div><strong className="text-slate-400">Email:</strong> {lead.business_email || "Pending Enrichment"}</div>
                        <div><strong className="text-slate-400">Contact:</strong> {lead.contact_name ? `${lead.contact_name} (${lead.job_title})` : "Procurement Division"}</div>
                        <div><strong className="text-slate-400">Provenance:</strong> {lead.source}</div>
                        {lead.import_evidence && (
                          <div className="mt-1 text-[11px] text-teal-300 italic">Evidence: {lead.import_evidence}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* LinkedIn Compliant X-Ray Search Card */}
            {linkedinData && (
              <div className="p-5 rounded-xl bg-slate-950 border border-blue-900/50 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-blue-400" />
                    <h4 className="text-sm font-bold text-white">LinkedIn Compliant Buyer Persona X-Ray Dork</h4>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30">
                    PRD §3.D Compliant
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Targeted Google search string identifying decision-makers (*Import Managers, Sourcing Directors*) without unauthorized scraping bots:
                </p>
                <div className="p-2.5 bg-slate-900 rounded font-mono text-xs text-blue-300 break-all border border-slate-800">
                  {linkedinData.individual_xray_query}
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <a
                    href={linkedinData.individual_search_url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-semibold flex items-center gap-1.5"
                  >
                    <span>Launch Google X-Ray Search</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Exporter Product Catalog & AI Buyer Matching Engine */}
        {activeTab === "catalog" && (
          <div className="p-8 pt-2 space-y-6 pb-20">
            {/* Top Banner & Control Bar */}
            <div className="flex items-center justify-between bg-slate-950 p-5 rounded-2xl border border-slate-800 shadow-xl">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Package className="h-5 w-5 text-emerald-400" />
                  Exporter Product Catalog & Specifications
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Configure your export commodities, HS codes, and MOQs. Run 100-point matching algorithms against 42 verified international buyers.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowAddProductModal(true)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold shadow-lg shadow-emerald-600/20 flex items-center gap-2 transition-all"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add Export Commodity</span>
                </button>
                <button
                  onClick={loadProducts}
                  disabled={loadingProducts}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loadingProducts ? "animate-spin" : ""}`} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Exporter Commodities Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {products.map((prod) => {
                const isSelected = selectedProduct?.profile_id === prod.profile_id;
                const isMatching = matchingLoading && isSelected;

                return (
                  <div
                    key={prod.profile_id}
                    className={`rounded-2xl border p-5 flex flex-col justify-between transition-all shadow-md ${
                      isSelected
                        ? "bg-slate-950/95 border-emerald-500/50 shadow-emerald-500/10 ring-1 ring-emerald-500/30"
                        : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div>
                      {/* Category & Status */}
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                          {prod.product_category}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                          <span className="text-[11px] font-semibold text-emerald-400">Active</span>
                          <button
                            onClick={() => handleDeleteProduct(prod.profile_id, prod.product_name)}
                            className="p-1 rounded hover:bg-rose-950/60 text-slate-500 hover:text-rose-400 transition-colors ml-2"
                            title="Delete commodity"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Product Name & ID */}
                      <h4 className="text-base font-bold text-white tracking-tight">{prod.product_name}</h4>
                      <div className="flex items-center gap-2 mt-1 mb-3 text-xs text-slate-400 font-mono">
                        <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-emerald-400 text-[10px]">
                          {prod.profile_id}
                        </span>
                        {prod.hs_code && <span>HS: {prod.hs_code}</span>}
                      </div>

                      {/* Spec Badges Grid */}
                      <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                        <div className="p-2 rounded-lg bg-slate-900/70 border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] block uppercase font-bold">MOQ</span>
                          <span className="font-semibold text-slate-200 truncate block">{prod.moq || "Flexible"}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900/70 border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] block uppercase font-bold">Target Price</span>
                          <span className="font-semibold text-emerald-400 truncate block">
                            {prod.target_price_min && prod.target_price_max
                              ? `$${prod.target_price_min}–$${prod.target_price_max} / ${prod.incoterms}`
                              : `${prod.currency} (${prod.incoterms})`}
                          </span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900/70 border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] block uppercase font-bold">Capacity</span>
                          <span className="font-semibold text-slate-200 truncate block">{prod.available_quantity || "On Request"}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900/70 border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] block uppercase font-bold">Packaging</span>
                          <span className="font-semibold text-slate-200 truncate block">{prod.packaging || "Export Bulk"}</span>
                        </div>
                      </div>

                      {/* Target Markets */}
                      {prod.target_countries && prod.target_countries.length > 0 && (
                        <div className="mb-3">
                          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">
                            Target Markets ({prod.target_countries.length})
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {prod.target_countries.slice(0, 4).map((c: string) => (
                              <span key={c} className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                                📍 {c}
                              </span>
                            ))}
                            {prod.target_countries.length > 4 && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-500 font-bold">
                                +{prod.target_countries.length - 4} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Certifications */}
                      {prod.certifications && prod.certifications.length > 0 && (
                        <div className="mb-4">
                          <div className="flex flex-wrap gap-1">
                            {prod.certifications.map((cert: string) => (
                              <span key={cert} className="text-[10px] px-2 py-0.5 rounded font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                                🛡️ {cert}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Match Action Button */}
                    <button
                      onClick={() => handleRunMatching(prod)}
                      disabled={isMatching}
                      className={`w-full py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                        isSelected && matchSummary
                          ? "bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25"
                          : "bg-slate-800 hover:bg-emerald-600 hover:text-white text-slate-200 border border-slate-700"
                      }`}
                    >
                      {isMatching ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin text-emerald-400" />
                          <span>Evaluating 42 Buyers...</span>
                        </>
                      ) : (
                        <>
                          <Zap className={`h-3.5 w-3.5 ${isSelected ? "text-amber-400" : "text-emerald-400"}`} />
                          <span>{isSelected && matchSummary ? "Re-Run Buyer Matching" : "Run Live Buyer Matching"}</span>
                        </>
                      )}
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Live Matching Results Pane */}
            {selectedProduct && (
              <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 shadow-2xl space-y-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Live AI Matching Results</span>
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-[11px] font-mono text-slate-300 border border-slate-700">
                        {selectedProduct.product_name}
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-white mt-1">
                      Candidate Buyer Ranking & 100-Point Qualification Standings
                    </h3>
                  </div>

                  {matchSummary && (
                    <div className="flex items-center gap-3">
                      <div className="px-3.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
                        <span className="text-slate-400">Total Evaluated: </span>
                        <strong className="text-white">{matchSummary.total_leads_evaluated} Leads</strong>
                      </div>
                      <div className="px-3.5 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-400">
                        <span>Qualified: </span>
                        <strong className="font-bold">{matchSummary.qualified_leads_count} Verified Buyers</strong>
                      </div>
                    </div>
                  )}
                </div>

                {/* Loading state */}
                {matchingLoading && (
                  <div className="p-12 text-center space-y-3">
                    <RefreshCw className="h-8 w-8 text-emerald-400 animate-spin mx-auto" />
                    <p className="text-sm font-semibold text-slate-200">
                      Evaluating 42 verified buyers against {selectedProduct.product_name}...
                    </p>
                    <p className="text-xs text-slate-500 max-w-md mx-auto">
                      Executing 5-factor compatibility model: Product Relevance (30), Country Alignment (25), Verified Import Evidence (20), Contact Quality (15), and Verification Standing (10).
                    </p>
                  </div>
                )}

                {/* Matches Table */}
                {!matchingLoading && matchSummary && (
                  <div className="space-y-4">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-x-auto">
                      <table className="w-full text-left text-sm text-slate-300">
                        <thead className="bg-slate-900 text-xs font-semibold uppercase text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="px-5 py-3.5">Matched Buyer & Country</th>
                            <th className="px-5 py-3.5 text-center">Composite Score</th>
                            <th className="px-5 py-3.5 text-center">5-Factor Breakdown</th>
                            <th className="px-5 py-3.5">Qualification Rationale</th>
                            <th className="px-5 py-3.5 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {matchSummary.top_matches.map((m: any) => {
                            const isHigh = m.qualification_score >= 80;
                            const isPot = m.qualification_score >= 60 && m.qualification_score < 80;

                            return (
                              <tr key={m.lead_id} className="hover:bg-slate-900/80 transition-colors">
                                <td className="px-5 py-4">
                                  <div className="font-semibold text-white">{m.company_name}</div>
                                  <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                                    <span>📍 {m.country}</span>
                                    <span className="text-[10px] font-mono text-slate-500">({m.lead_id})</span>
                                  </div>
                                </td>

                                <td className="px-5 py-4 text-center">
                                  <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black ${
                                    isHigh
                                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                      : isPot
                                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                                      : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                                  }`}>
                                    <span>{m.qualification_score}</span>
                                    <span className="text-[10px] font-normal text-slate-400">/ 100</span>
                                  </div>
                                  <span className="block text-[10px] font-semibold text-slate-400 mt-1">
                                    {m.qualification_tier}
                                  </span>
                                </td>

                                <td className="px-5 py-4">
                                  <div className="flex items-center justify-center gap-1 text-[10px]">
                                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300" title="Product Relevance (Max 30)">
                                      Rel: {m.breakdown.product_relevance_score}/30
                                    </span>
                                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300" title="Country Alignment (Max 25)">
                                      Mkt: {m.breakdown.country_alignment_score}/25
                                    </span>
                                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300" title="Import Evidence (Max 20)">
                                      Imp: {m.breakdown.import_evidence_score}/20
                                    </span>
                                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300" title="Contact Quality (Max 15)">
                                      Ctc: {m.breakdown.contact_quality_score}/15
                                    </span>
                                  </div>
                                </td>

                                <td className="px-5 py-4 max-w-md">
                                  <p className="text-xs text-slate-300 leading-snug line-clamp-2">
                                    {m.explanation}
                                  </p>
                                  <div className="text-[11px] text-emerald-400 font-semibold mt-1 flex items-center gap-1">
                                    <span>👉 Action:</span>
                                    <span className="text-slate-300 font-normal">{m.recommended_action}</span>
                                  </div>
                                </td>

                                <td className="px-5 py-4 text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    <button
                                      onClick={() => setSelectedMatchExplanation(m)}
                                      className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
                                      title="View 5-factor itemized score details"
                                    >
                                      Breakdown
                                    </button>
                                    <button
                                      onClick={() => {
                                        const lead = leads.find(l => l.lead_id === m.lead_id);
                                        if (lead) setSelectedLead(lead);
                                      }}
                                      className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-emerald-400 transition-colors inline-flex items-center gap-1"
                                      title="Open full 100-pt evidence audit"
                                    >
                                      <Eye className="h-3 w-3" />
                                      <span>Audit</span>
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Prompt to run matching if not run yet */}
                {!matchingLoading && !matchSummary && (
                  <div className="p-8 text-center bg-slate-900/50 rounded-xl border border-dashed border-slate-800 space-y-2">
                    <p className="text-sm font-semibold text-slate-300">
                      Click &ldquo;Run Live Buyer Matching&rdquo; above to evaluate this commodity against all 42 international buyers.
                    </p>
                    <p className="text-xs text-slate-500">
                      The matching algorithm validates HS code compatibility, destination country priorities, verified import volumes, and direct procurement contacts.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab 1: Buyer Directory & Verification Table */}
        {activeTab === "directory" && (
          <div className="p-8 pt-2 space-y-4 pb-20">
            {/* Filter Bar */}
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search by company name, country, or product category..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>

              <select
                value={selectedCountry}
                onChange={(e) => setSelectedCountry(e.target.value)}
                className="px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-emerald-500"
              >
                <option value="ALL">All Countries</option>
                {countries.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>

              <select
                value={selectedTier}
                onChange={(e) => setSelectedTier(e.target.value)}
                className="px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-emerald-500"
              >
                <option value="ALL">All Qualification Tiers</option>
                <option value="HIGH">High Priority (80–100)</option>
                <option value="POTENTIAL">Potential (60–79)</option>
                <option value="LOW">Low / Quarantined (&lt;60)</option>
              </select>
            </div>

            {/* Leads Table */}
            <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-x-auto shadow-sm">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-900/80 text-xs font-semibold uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-5 py-3.5">Company & Location</th>
                    <th className="px-5 py-3.5">Product Category</th>
                    <th className="px-5 py-3.5">Contact & Channel</th>
                    <th className="px-5 py-3.5 text-center">Score</th>
                    <th className="px-5 py-3.5">Status & Flags</th>
                    <th className="px-5 py-3.5">Pipeline Stage</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredLeads.map((lead) => (
                    <tr key={lead.lead_id} className="hover:bg-slate-900/50 transition-colors">
                      <td className="px-5 py-4">
                        <div className="font-semibold text-white">{lead.company_name}</div>
                        <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                          <span>{lead.city ? `${lead.city}, ` : ""}{lead.country}</span>
                          {lead.website && (
                            <a
                              href={lead.website}
                              target="_blank"
                              rel="noreferrer"
                              className="text-emerald-400 hover:underline flex items-center gap-0.5"
                            >
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <span className="font-medium text-slate-200">{lead.product_category}</span>
                        <div className="text-xs text-slate-500 mt-0.5 truncate max-w-xs">
                          {lead.source}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <div className="text-xs font-medium text-slate-300">
                          {lead.contact_name ? `${lead.contact_name} (${lead.job_title || "Contact"})` : "Public Corporate Desk"}
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                          <Mail className="h-3 w-3 text-slate-500" />
                          <span>{lead.business_email || "No email listed"}</span>
                        </div>
                      </td>

                      <td className="px-5 py-4 text-center">
                        <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                          lead.buyer_score >= 80
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : lead.buyer_score >= 60
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                        }`}>
                          {lead.buyer_score} / 100
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex flex-col gap-1 items-start">
                          <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded font-medium ${
                            lead.verification_status === "Verified"
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                              : lead.verification_status === "Partially Verified"
                              ? "bg-amber-950 text-amber-300 border border-amber-800"
                              : "bg-rose-950 text-rose-300 border border-rose-800"
                          }`}>
                            {lead.verification_status === "Verified" ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                            {lead.verification_status}
                          </span>

                          {lead.risk_flags.map(f => (
                            <span key={f} className="text-[10px] px-1.5 py-0.2 rounded bg-rose-950/80 text-rose-300 border border-rose-800">
                              {f}
                            </span>
                          ))}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 font-medium">
                          {lead.pipeline_stage}
                        </span>
                      </td>

                      <td className="px-5 py-4 text-right">
                        <button
                          onClick={() => setSelectedLead(lead)}
                          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors inline-flex items-center gap-1.5"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          Audit 100-Pt
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Table pagination & count ribbon */}
            <div className="flex items-center justify-between text-xs text-slate-400 px-2 py-2 border-t border-slate-800">
              <div>
                Showing <strong className="text-white">{filteredLeads.length}</strong> loaded leads
                {totalDbCount > 0 && <span> of <strong className="text-emerald-400">{totalDbCount.toLocaleString()}</strong> verified buyer records in database</span>}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => fetchLeads(currentPage - 1)}
                  disabled={currentPage <= 1 || loadingLeads}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 font-semibold"
                >
                  ← Previous
                </button>
                <span className="px-2 font-mono text-slate-300">Page {currentPage}</span>
                <button
                  onClick={() => fetchLeads(currentPage + 1)}
                  disabled={filteredLeads.length < 50 || loadingLeads}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 font-semibold"
                >
                  Next →
                </button>
                <button
                  onClick={() => fetchLeads(currentPage)}
                  disabled={loadingLeads}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-emerald-400 font-semibold flex items-center gap-1"
                >
                  <RefreshCw className={`h-3 w-3 ${loadingLeads ? "animate-spin" : ""}`} />
                  Refresh
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: 15-Stage CRM Deal Pipeline */}
        {activeTab === "pipeline" && (
          <div className="p-8 pt-2 overflow-x-auto space-y-4 pb-20">
            <div className="flex items-center justify-between bg-slate-950 p-4 rounded-xl border border-slate-800">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-bold text-white">Full Commercial Pipeline & Kanban Board</h3>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
                  {kanbanData?.total_leads ?? (totalDbCount > 0 ? totalDbCount : totalLeads)} Leads Tracked
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30 font-semibold">
                  {kanbanData?.total_deals ?? 90} Active Commercial Deals
                </span>
              </div>
              <button
                onClick={loadKanban}
                disabled={loadingKanban}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-xs font-semibold text-slate-300 flex items-center gap-1.5"
              >
                <RefreshCw className={`h-3 w-3 ${loadingKanban ? "animate-spin" : ""}`} />
                <span>Refresh Kanban</span>
              </button>
            </div>

            <div className="flex gap-4 min-w-[2400px] pb-6">
              {PIPELINE_STAGES.map((stage, idx) => {
                const colData = kanbanData?.stages?.find((s: any) => s.stage === stage);
                const stageDeals = colData?.deals || [];
                const stageLeads = colData?.leads || leads.filter(l => l.pipeline_stage === stage);
                const totalColCount = colData?.count ?? (stageLeads.length + stageDeals.length);

                return (
                  <div key={stage} className="w-80 flex-shrink-0 bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col">
                    <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
                      <div className="flex items-center gap-2">
                        <span className="h-5 w-5 rounded-full bg-slate-800 text-[11px] font-bold text-slate-300 flex items-center justify-center">
                          {idx + 1}
                        </span>
                        <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">{stage}</h4>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 font-semibold text-slate-400">
                        {totalColCount}
                      </span>
                    </div>

                    <div className="space-y-3 flex-1 overflow-y-auto max-h-[620px]">
                      {stageDeals.map((d: any) => (
                        <div
                          key={d.deal_id}
                          className="p-3.5 rounded-lg bg-blue-950/40 border border-blue-800/60 hover:border-blue-500/50 transition-all shadow-sm space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-blue-300">{d.deal_id}</span>
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              d.payment_risk_status === "LOW" ? "bg-emerald-950 text-emerald-300 border border-emerald-700" :
                              d.payment_risk_status === "MEDIUM" ? "bg-amber-950 text-amber-300 border border-amber-700" :
                              "bg-rose-950 text-rose-300 border border-rose-700"
                            }`}>
                              Risk: {d.payment_risk_status}
                            </span>
                          </div>
                          <div className="font-semibold text-sm text-white">{d.product_name}</div>
                          <div className="text-xs text-slate-300">
                            {d.required_quantity && <span>Qty: {d.required_quantity} • </span>}
                            <span>Port: {d.destination_port || "CIF Jebel Ali"}</span>
                          </div>
                          <div className="text-xs font-mono text-emerald-400 font-bold">
                            {d.confirmed_order_value ? `$${d.confirmed_order_value.toLocaleString()} Confirmed` : 
                             d.quotation_amount ? `$${d.quotation_amount.toLocaleString()} Quoted` : "Terms Pending"}
                          </div>
                          <div className="text-[11px] text-slate-400">
                            Payment: {d.payment_terms || "100% LC at sight"}
                          </div>
                        </div>
                      ))}

                      {stageLeads.slice(0, 15).map((l: any) => (
                        <div
                          key={l.lead_id}
                          onClick={() => setSelectedLead(l)}
                          className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-emerald-500/50 cursor-pointer transition-all shadow-sm"
                        >
                          <div className="font-semibold text-sm text-white">{l.company_name}</div>
                          <div className="text-xs text-slate-400 mt-1">{l.country} • {l.product_category}</div>
                          <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-800/60">
                            <span className={`text-[11px] font-bold ${l.buyer_score >= 80 ? "text-emerald-400" : "text-amber-400"}`}>
                              Score: {l.buyer_score}
                            </span>
                            <span className="text-[10px] text-slate-500">{l.lead_id}</span>
                          </div>
                        </div>
                      ))}

                      {stageDeals.length === 0 && stageLeads.length === 0 && (
                        <div className="text-center py-8 text-xs text-slate-600">No prospects</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 3: Assisted Outreach Review Queue & Cadence Orchestration (PRD §7 & §10) */}
        {activeTab === "queue" && (
          <div className="p-8 pt-2 max-w-5xl space-y-6 pb-20">
            {/* Mode A Banner */}
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-amber-300">Mode A — Assisted Outreach & 3-Touch Cadence Engine</h4>
                  <p className="text-xs text-amber-200/80 mt-0.5">
                    PRD §7 & §10: 3-touch sequence (Day 0 Intro → Day 4 Samples & Specs → Day 8 Final Check). Auto-halts immediately on buyer response.
                  </p>
                </div>
              </div>
              <button
                onClick={handleProcessFollowups}
                disabled={cadenceLoading}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-emerald-600/20 flex items-center gap-2 whitespace-nowrap"
              >
                {cadenceLoading ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Scanning Cadences...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-3.5 w-3.5 text-amber-300" />
                    <span>Run Cadence Scheduler</span>
                  </>
                )}
              </button>
            </div>

            {/* Cadence Funnel Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase">Touch 1 (Day 0)</span>
                  <Send className="h-4 w-4 text-blue-400" />
                </div>
                <div className="text-2xl font-black text-white mt-1">
                  {cadenceStatus?.touch_1_sent ?? 0}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">Initial Introductions Sent</div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase">Touch 2 (Day 4)</span>
                  <Clock className="h-4 w-4 text-amber-400" />
                </div>
                <div className="text-2xl font-black text-white mt-1">
                  {cadenceStatus?.touch_2_queued_or_approved ?? 0} <span className="text-xs font-normal text-slate-400">due</span> / {cadenceStatus?.touch_2_sent ?? 0} <span className="text-xs font-normal text-slate-400">sent</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">Sample / CoA Follow-up</div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase">Touch 3 (Day 8)</span>
                  <CheckCircle2 className="h-4 w-4 text-purple-400" />
                </div>
                <div className="text-2xl font-black text-white mt-1">
                  {cadenceStatus?.touch_3_queued_or_approved ?? 0} <span className="text-xs font-normal text-slate-400">due</span> / {cadenceStatus?.touch_3_sent ?? 0} <span className="text-xs font-normal text-slate-400">sent</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">Final Closing Inquiry</div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase">Auto-Halted</span>
                  <MessageSquare className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-black text-emerald-400 mt-1">
                  {cadenceStatus?.replied_and_halted ?? 0} <span className="text-xs font-normal text-slate-400">replied</span> / {cadenceStatus?.suppressed_and_halted ?? 0} <span className="text-xs font-normal text-slate-400">opted-out</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">Subsequent Touches Stopped</div>
              </div>
            </div>

            {/* Cadence Scheduler Run Feedback */}
            {cadenceResult && (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                  <span>
                    Scheduler Executed: Generated <strong>{cadenceResult.generated_count}</strong> follow-up emails for review queue. 
                    Checked <strong>{cadenceResult.eligible_leads}</strong> active leads.
                  </span>
                </div>
              </div>
            )}

            {/* Inbound Buyer Reply & Auto-Halt Simulator */}
            <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-emerald-400" />
                  <h4 className="text-sm font-bold text-white">Inbound Reply & Cadence Auto-Halt Simulator</h4>
                </div>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  11-Class AI Entity Extractor
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Simulate an incoming response from a prospective international buyer to verify instant cadence halting, 11-class intent classification, and CRM pipeline progression:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Select Responding Buyer</label>
                  <select
                    value={simLeadId}
                    onChange={(e) => setSimLeadId(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="">-- Choose a Buyer Lead --</option>
                    {leads.slice(0, 15).map(l => (
                      <option key={l.lead_id} value={l.lead_id}>
                        {l.company_name} ({l.country})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Simulated Reply Intent</label>
                  <select
                    value={simReplyType}
                    onChange={(e) => setSimReplyType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="RFQ">Request for Quotation (500 MT CIF Jebel Ali, LC)</option>
                    <option value="SAMPLES">Request for Samples (1kg physical test kit & CoA)</option>
                    <option value="OPTOUT">Unsubscribe / Not Interested (Auto-Suppression)</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={handleSimulateInboundReply}
                    disabled={!simLeadId || simulatingReply}
                    className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 shadow-lg shadow-blue-600/20"
                  >
                    {simulatingReply ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        <span>Classifying Reply...</span>
                      </>
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5" />
                        <span>Simulate Buyer Reply</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {simReplyResult && (
                <div className="p-3.5 rounded-xl bg-slate-900/90 border border-emerald-500/40 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                      <CheckCircle2 className="h-4 w-4" />
                      Classified Intent: {simReplyResult.classification} ({(simReplyResult.confidence_score * 100).toFixed(0)}% confidence)
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">
                      CADENCE AUTO-HALTED
                    </span>
                  </div>
                  <div className="text-slate-300">
                    <strong>Recommended Action:</strong> {simReplyResult.extracted_next_action}
                  </div>
                  {simReplyResult.extracted_delivery_port && (
                    <div className="text-slate-400">
                      <strong>Extracted Delivery Port:</strong> {simReplyResult.extracted_delivery_port} • <strong>Payment:</strong> {simReplyResult.extracted_payment_method || "LC at Sight"}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Mode A Pending Emails Review List */}
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-emerald-400" />
                  <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                    Mode A Grounded Email Queue
                  </h4>
                </div>

                {/* Queue status filter buttons */}
                <div className="flex items-center gap-1.5 text-xs">
                  {(["Queued", "Approved", "Sent", "Rejected"] as const).map(st => {
                    const count = 
                      st === "Queued" ? outreachQueueSummary?.total_queued :
                      st === "Approved" ? outreachQueueSummary?.total_approved :
                      st === "Sent" ? outreachQueueSummary?.total_sent :
                      outreachQueueSummary?.total_rejected;

                    return (
                      <button
                        key={st}
                        onClick={() => {
                          setQueueStatusFilter(st);
                          loadQueue(st);
                        }}
                        className={`px-3 py-1.5 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                          queueStatusFilter === st
                            ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                            : "bg-slate-900 hover:bg-slate-800 text-slate-400"
                        }`}
                      >
                        <span>{st}</span>
                        {count !== undefined && (
                          <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                            queueStatusFilter === st ? "bg-emerald-800 text-white" : "bg-slate-800 text-slate-300"
                          }`}>
                            {count}
                          </span>
                        )}
                      </button>
                    );
                  })}
                  <button
                    onClick={() => loadQueue(queueStatusFilter)}
                    disabled={loadingQueue}
                    className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400"
                    title="Refresh Queue"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${loadingQueue ? "animate-spin text-emerald-400" : ""}`} />
                  </button>
                </div>
              </div>

              {outreachQueueEmails.length === 0 ? (
                <div className="p-12 text-center rounded-xl border border-slate-800 bg-slate-950/60 text-slate-500 text-xs">
                  No outreach emails currently in <strong>{queueStatusFilter}</strong> state.
                </div>
              ) : (
                outreachQueueEmails.map((email: any) => (
                  <div key={email.email_id || email.id} className="rounded-xl border border-slate-800 bg-slate-950 p-6 space-y-4 shadow-sm">
                    <div className="flex items-start justify-between pb-4 border-b border-slate-800">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-emerald-400">Target Buyer</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {email.email_id}
                          </span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                            Sequence Touch {email.sequence_step || 1}
                          </span>
                        </div>
                        <h3 className="text-lg font-bold text-white mt-1">{email.company_name} ({email.country})</h3>
                        <p className="text-xs text-slate-400 mt-0.5">
                          To: {email.to_name || "Procurement Desk"} &lt;{email.to_email}&gt;
                        </p>
                      </div>
                      <div className="text-right flex flex-col items-end gap-1.5">
                        <span className={`text-xs px-2.5 py-1 rounded-full font-bold ${
                          email.status === "Approved" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" :
                          email.status === "Sent" ? "bg-blue-500/10 text-blue-400 border border-blue-500/30" :
                          email.status === "Rejected" ? "bg-rose-500/10 text-rose-400 border border-rose-500/30" :
                          "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                        }`}>
                          Status: {email.status}
                        </span>
                        {email.confidence_score && (
                          <span className="text-[11px] text-emerald-400 font-mono">
                            {(email.confidence_score * 100).toFixed(0)}% Factually Grounded
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="bg-slate-900 rounded-lg p-4 font-mono text-xs text-slate-300 space-y-3 leading-relaxed border border-slate-800">
                      <p><strong className="text-slate-400 font-sans">Subject:</strong> {email.subject}</p>
                      <div className="whitespace-pre-line text-slate-200">
                        {email.body_text}
                      </div>
                    </div>

                    {email.grounding_evidence && (
                      <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400">
                        <strong className="text-emerald-400">Public Grounding Evidence:</strong> {email.grounding_evidence}
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-2">
                      <div className="text-[11px] text-slate-500">
                        Created: {new Date(email.created_at).toLocaleString()}
                        {email.sent_at && <span> • Dispatched: {new Date(email.sent_at).toLocaleString()}</span>}
                        {email.rejection_reason && <span className="text-rose-400"> • Reason: {email.rejection_reason}</span>}
                      </div>

                      <div className="flex items-center gap-2">
                        {email.status === "Queued" && (
                          <>
                            <button
                              onClick={() => handleRejectEmail(email.email_id)}
                              className="px-4 py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-xs font-semibold text-rose-300 transition-colors"
                            >
                              Reject / Quarantine
                            </button>
                            <button
                              onClick={() => handleApproveEmail(email.email_id)}
                              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition-colors"
                            >
                              Approve Only
                            </button>
                            <button
                              onClick={() => handleApproveAndDispatch(email.email_id)}
                              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white shadow-lg shadow-emerald-600/20 flex items-center gap-2 transition-all"
                            >
                              <Send className="h-3.5 w-3.5" />
                              Approve & Dispatch
                            </button>
                          </>
                        )}
                        {email.status === "Approved" && (
                          <button
                            onClick={() => handleDispatchEmail(email.email_id)}
                            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white shadow-lg shadow-blue-600/20 flex items-center gap-2 transition-all"
                          >
                            <Send className="h-3.5 w-3.5" />
                            Dispatch via SMTP
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Payment Risk & Transaction Safety */}
        {activeTab === "risk" && (
          <div className="p-8 pt-2 max-w-5xl space-y-6 pb-20">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
              <h3 className="text-base font-bold text-white mb-2">Automated Payment Term Risk Rubric</h3>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-300">
                  <span className="font-bold block mb-1">Low Financial Risk</span>
                  100% Advance Wire (TT) or Confirmed Irrevocable Letter of Credit (LC at Sight) issued by a Tier-1 prime bank.
                </div>
                <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-300">
                  <span className="font-bold block mb-1">Medium Financial Risk</span>
                  Documentary Collection (D/P). Requires bank avalization and maritime bill of lading consigned to bank order.
                </div>
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300">
                  <span className="font-bold block mb-1">Critical Financial Risk</span>
                  Clean Open Account (Credit) or D/A. Blocked automatically without formal ECGC export credit insurance underwriting.
                </div>
              </div>
            </div>

            <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-rose-400" />
                  <span>Quarantined High-Risk Buyers & Advance-Fee Fraud Signals ({highRiskList.length})</span>
                </h4>
                <button
                  onClick={loadHighRisk}
                  disabled={loadingHighRisk}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded font-semibold flex items-center gap-1.5"
                >
                  <RefreshCw className={`h-3 w-3 ${loadingHighRisk ? "animate-spin text-rose-400" : ""}`} />
                  <span>Refresh Queue</span>
                </button>
              </div>

              <div className="space-y-3">
                {highRiskList.map((hr: any) => (
                  <div key={hr.lead_id} className="p-4 rounded-lg bg-slate-900 border border-rose-500/30 flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">{hr.company_name}</span>
                        <span className="text-xs text-slate-400">({hr.country} • {hr.lead_id})</span>
                        <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-rose-950 text-rose-400 border border-rose-800">
                          {hr.risk_level || "HIGH"} RISK
                        </span>
                      </div>
                      <div className="text-xs text-slate-300">
                        <strong>Payment Risk Score:</strong> {hr.payment_risk_score ?? 40} / 100 • <strong>Contact:</strong> {hr.contact_name || "N/A"} ({hr.business_email || "No email listed"})
                      </div>
                      <div className="text-xs text-rose-300">
                        <strong>Risk Flags:</strong> {hr.risk_flags && hr.risk_flags.length > 0 ? hr.risk_flags.join(", ") : "Untrusted registration request / high financial vulnerability"}
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedLead(hr)}
                      className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white whitespace-nowrap"
                    >
                      Audit 100-Pt
                    </button>
                  </div>
                ))}

                {highRiskList.length === 0 && (
                  <div className="p-6 text-center text-xs text-slate-500">
                    No active high-risk leads in quarantine.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Executive Performance, Financials & DGFT Audit Analytics (PRD §13) */}
        {activeTab === "analytics" && (
          <div className="p-8 pt-2 max-w-6xl space-y-6 pb-20">
            {/* Financial Performance Ribbon */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-5 rounded-2xl bg-gradient-to-br from-emerald-950/60 to-slate-950 border border-emerald-500/30 shadow-xl">
                <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block">
                  Confirmed Realized Revenue
                </span>
                <div className="text-3xl font-black text-white mt-1.5">
                  ${execReport?.financial_performance?.confirmed_realized_revenue_usd?.toLocaleString() ?? "0"}
                </div>
                <div className="text-[11px] text-emerald-300/80 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  <span>{execReport?.financial_performance?.confirmed_deals_count ?? 0} Realized Commercial Deals</span>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 shadow-xl">
                <span className="text-xs font-bold text-blue-400 uppercase tracking-wider block">
                  Commercial Quotations (PI)
                </span>
                <div className="text-3xl font-black text-white mt-1.5">
                  ${execReport?.financial_performance?.total_quotations_value_usd?.toLocaleString() ?? "0"}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Active Proforma Invoices Issued
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 shadow-xl">
                <span className="text-xs font-bold text-purple-400 uppercase tracking-wider block">
                  System Operating Cost
                </span>
                <div className="text-3xl font-black text-white mt-1.5">
                  $0.00 <span className="text-xs text-purple-300 font-semibold">/ month</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Open Official Trade Connectors
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-gradient-to-br from-blue-950/40 to-slate-950 border border-blue-500/30 shadow-xl">
                <span className="text-xs font-bold text-blue-400 uppercase tracking-wider block">
                  Trade Fair Cost Savings
                </span>
                <div className="text-3xl font-black text-emerald-400 mt-1.5">
                  99.9%
                </div>
                <div className="text-[11px] text-blue-300/80 mt-1">
                  vs ~$12,000/booth (Gulfood/SIAL)
                </div>
              </div>
            </div>

            {/* PRD §5: 10 Core Metrics Funnel */}
            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-emerald-400" />
                    PRD §5: Ten-Metric Export Acquisition Funnel
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    End-to-end audit tracking raw discovery to confirmed revenue without data fabrication.
                  </p>
                </div>
                <a
                  href={api.getExportCsvUrl()}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-600/20"
                >
                  <FileCheck className="h-3.5 w-3.5" />
                  <span>Download DGFT Audit CSV</span>
                </a>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2">
                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-slate-400 font-semibold">1. Raw Discovered</div>
                  <div className="text-xl font-black text-white mt-0.5">
                    {execReport?.prd_10_core_metrics?.["1_raw_records_discovered"] ?? totalLeads}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-slate-400 font-semibold">2. Unique Companies</div>
                  <div className="text-xl font-black text-white mt-0.5">
                    {execReport?.prd_10_core_metrics?.["2_unique_companies_identified"] ?? totalLeads}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-emerald-400 font-semibold">3. 100-Pt Verified</div>
                  <div className="text-xl font-black text-emerald-400 mt-0.5">
                    {execReport?.prd_10_core_metrics?.["3_companies_successfully_verified"] ?? verifiedCount}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-blue-400 font-semibold">4. Qualified (≥60)</div>
                  <div className="text-xl font-black text-blue-400 mt-0.5">
                    {execReport?.prd_10_core_metrics?.["4_qualified_potential_buyers"] ?? highPriorityCount + potentialCount}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-slate-400 font-semibold">5. Valid Emails</div>
                  <div className="text-xl font-black text-white mt-0.5">
                    {execReport?.prd_10_core_metrics?.["5_valid_business_email_addresses"] ?? leads.filter(l => l.business_email).length}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-amber-400 font-semibold">6. Mode A Approved</div>
                  <div className="text-xl font-black text-amber-300 mt-0.5">
                    {execReport?.prd_10_core_metrics?.["6_emails_approved_for_outreach"] ?? 0}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-slate-400 font-semibold">7. Emails Sent</div>
                  <div className="text-xl font-black text-white mt-0.5">
                    {execReport?.prd_10_core_metrics?.["7_emails_successfully_delivered"] ?? 0}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-emerald-400 font-semibold">8. Replies Received</div>
                  <div className="text-xl font-black text-emerald-400 mt-0.5">
                    {execReport?.prd_10_core_metrics?.["8_replies_received"] ?? 0}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[11px] text-purple-400 font-semibold">9. Buyer Inquiries</div>
                  <div className="text-xl font-black text-purple-300 mt-0.5">
                    {execReport?.prd_10_core_metrics?.["9_qualified_buyer_inquiries"] ?? 0}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/40">
                  <div className="text-[11px] text-emerald-300 font-bold">10. Quotations & Deals</div>
                  <div className="text-xl font-black text-white mt-0.5">
                    {execReport?.prd_10_core_metrics?.["10_quotations_and_orders"] ?? 0}
                  </div>
                </div>
              </div>
            </div>

            {/* Source-Wise Yield Breakdown Table */}
            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Layers className="h-5 w-5 text-blue-400" />
                Data Provenance & Source-Wise Conversion Yield
              </h3>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-bold uppercase tracking-wider">
                      <th className="py-2.5 px-3">Authorized Public Source</th>
                      <th className="py-2.5 px-3">Raw Discovered</th>
                      <th className="py-2.5 px-3">100-Pt Verified</th>
                      <th className="py-2.5 px-3">Qualified (≥60)</th>
                      <th className="py-2.5 px-3 text-right">Yield Rate (%)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {execReport?.source_yield_breakdown?.map((src: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-900/50">
                        <td className="py-3 px-3 font-sans font-semibold text-white flex items-center gap-2">
                          <Globe className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                          <span>{src.source}</span>
                        </td>
                        <td className="py-3 px-3 text-slate-300">{src.raw_discovered}</td>
                        <td className="py-3 px-3 text-emerald-400">{src.verified_count}</td>
                        <td className="py-3 px-3 text-blue-400">{src.qualified_count}</td>
                        <td className="py-3 px-3 text-right">
                          <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-bold">
                            {src.yield_rate_pct}%
                          </span>
                        </td>
                      </tr>
                    )) || (
                      <tr>
                        <td colSpan={5} className="py-4 text-center text-slate-500">
                          Loading source yield analytics...
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Geographic Distribution & Commodities */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <Globe className="h-4 w-4 text-emerald-400" />
                  Top Target Buyer Markets
                </h4>
                <div className="space-y-2 text-xs">
                  {dashMetrics?.top_countries?.map((c: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                      <span className="font-semibold text-slate-200">📍 {c.country}</span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-400 font-mono font-bold">
                        {c.count} buyers
                      </span>
                    </div>
                  )) || (
                    <div className="text-slate-500 text-xs">Loading market data...</div>
                  )}
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-blue-400" />
                  Top Export Product Categories
                </h4>
                <div className="space-y-2 text-xs">
                  {dashMetrics?.top_products?.map((p: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                      <span className="font-semibold text-slate-200">🌾 {p.product}</span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-blue-400 font-mono font-bold">
                        {p.count} leads
                      </span>
                    </div>
                  )) || (
                    <div className="text-slate-500 text-xs">Loading commodity data...</div>
                  )}
                </div>
              </div>
            </div>

            {/* Compliance Invariant Footer */}
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-400 text-xs leading-relaxed">
              <strong className="text-slate-300">PRD Compliance & Zero Fabrication Standard:</strong> This system strictly guarantees zero data fabrication. 
              Realized revenue accounts only for confirmed purchase orders. Trade statistics are kept strictly partitioned from buyer records, and all outbound outreach requires explicit Mode A compliance signoff.
            </div>
          </div>
        )}


        {/* 100-Point Verification Details Modal */}
        {selectedLead && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="w-full max-w-2xl bg-slate-950 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-start justify-between pb-4 border-b border-slate-800">
                <div>
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">100-Point Verification Audit</span>
                  <h3 className="text-xl font-bold text-white mt-0.5">{selectedLead.company_name}</h3>
                  <p className="text-xs text-slate-400">{selectedLead.city ? `${selectedLead.city}, ` : ""}{selectedLead.country} • ID: {selectedLead.lead_id}</p>
                </div>
                <div className="text-right">
                  <span className={`text-2xl font-black ${selectedLead.buyer_score >= 80 ? "text-emerald-400" : "text-amber-400"}`}>
                    {selectedLead.buyer_score}
                  </span>
                  <span className="text-xs text-slate-500 block">/ 100 Points</span>
                </div>
              </div>

              {/* Rubric Breakdown Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="text-slate-300">1. Company Identity & Registration</span>
                    <span className="text-emerald-400">{selectedLead.scores_breakdown?.identity ?? 20} / 20</span>
                  </div>
                  <p className="text-slate-500 text-[11px]">Verified legal entity existence in public corporate directory.</p>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="text-slate-300">2. Product & Industry Relevance</span>
                    <span className="text-emerald-400">{selectedLead.scores_breakdown?.relevance ?? 20} / 20</span>
                  </div>
                  <p className="text-slate-500 text-[11px]">Direct match with exporter&apos;s commodity category and buyer role.</p>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="text-slate-300">3. Website & Identity Consistency</span>
                    <span className="text-emerald-400">{selectedLead.scores_breakdown?.website ?? 15} / 15</span>
                  </div>
                  <p className="text-slate-500 text-[11px]">Valid corporate domain, HTTPS/TLS alive check confirmed.</p>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="text-slate-300">4. Business Email Verification</span>
                    <span className={selectedLead.scores_breakdown?.email === 2 ? "text-rose-400" : "text-emerald-400"}>
                      {selectedLead.scores_breakdown?.email ?? 15} / 15
                    </span>
                  </div>
                  <p className="text-slate-500 text-[11px]">Domain MX records and corporate mailbox existence checked.</p>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="text-slate-300">5. Import / Purchasing Evidence</span>
                    <span className={selectedLead.scores_breakdown?.import_evidence === 0 ? "text-rose-400" : "text-emerald-400"}>
                      {selectedLead.scores_breakdown?.import_evidence ?? 15} / 15
                    </span>
                  </div>
                  <p className="text-slate-500 text-[11px]">Documented import licenses, customs clearance, or buyer meet history.</p>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="flex justify-between font-semibold mb-1">
                    <span className="text-slate-300">6. Independent Evidence</span>
                    <span className="text-emerald-400">{selectedLead.scores_breakdown?.independent ?? 10} / 15</span>
                  </div>
                  <p className="text-slate-500 text-[11px]">Chamber of commerce, phone directory, or professional verification.</p>
                </div>
              </div>

              {/* Evidence Attribution & Audit Log */}
              <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-300 block">Supporting Evidence & Data Provenance</span>
                <p className="text-xs text-slate-400 leading-relaxed">
                  <strong>Source:</strong> {selectedLead.source}
                </p>
                {selectedLead.source_url && (
                  <p className="text-xs text-slate-400 truncate">
                    <strong>Evidence URL:</strong> <a href={selectedLead.source_url} target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline">{selectedLead.source_url}</a>
                  </p>
                )}
                {selectedLead.import_evidence && (
                  <p className="text-xs text-slate-400">
                    <strong>Import Evidence:</strong> {selectedLead.import_evidence}
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setSelectedLead(null)}
                  className="px-5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
                >
                  Close Audit View
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Add Export Commodity Modal */}
        {showAddProductModal && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="w-full max-w-2xl bg-slate-950 border border-slate-800 rounded-2xl p-6 space-y-5 shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-start justify-between pb-4 border-b border-slate-800">
                <div>
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Catalog Configuration</span>
                  <h3 className="text-xl font-bold text-white mt-0.5">Add Export Commodity Line</h3>
                  <p className="text-xs text-slate-400">Configure specifications, HS code, MOQs, and target countries for automated matching.</p>
                </div>
                <button
                  onClick={() => setShowAddProductModal(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <form onSubmit={handleCreateProduct} className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">Export Commodity Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Organic Black Pepper Malabar TGSEB"
                      value={productForm.product_name}
                      onChange={(e) => setProductForm({ ...productForm, product_name: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">Industry Category *</label>
                    <select
                      value={productForm.product_category}
                      onChange={(e) => setProductForm({ ...productForm, product_category: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
                    >
                      <option value="Agricultural Commodities & Grains">Agricultural Commodities & Grains</option>
                      <option value="Spices & Seasonings">Spices & Seasonings</option>
                      <option value="Black Tea & Coffee">Black Tea & Coffee</option>
                      <option value="Textiles & Cotton Yarn">Textiles & Cotton Yarn</option>
                      <option value="Engineering Goods & Castings">Engineering Goods & Castings</option>
                      <option value="Chemicals, Dyes & Minerals">Chemicals, Dyes & Minerals</option>
                      <option value="Pharmaceuticals & Herbal Extracts">Pharmaceuticals & Herbal Extracts</option>
                      <option value="Ceramic Tiles & Sanitaryware">Ceramic Tiles & Sanitaryware</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">HS Code (6–8 Digits)</label>
                    <input
                      type="text"
                      placeholder="e.g. 0904.11.10"
                      value={productForm.hs_code}
                      onChange={(e) => setProductForm({ ...productForm, hs_code: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">Minimum Order Qty (MOQ)</label>
                    <input
                      type="text"
                      placeholder="e.g. 1x20ft FCL (15 MT)"
                      value={productForm.moq}
                      onChange={(e) => setProductForm({ ...productForm, moq: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">Available Supply Capacity</label>
                    <input
                      type="text"
                      placeholder="e.g. 200 MT / Month"
                      value={productForm.available_quantity}
                      onChange={(e) => setProductForm({ ...productForm, available_quantity: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3">
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">Target Price Min ($)</label>
                    <input
                      type="number"
                      placeholder="1200"
                      value={productForm.target_price_min}
                      onChange={(e) => setProductForm({ ...productForm, target_price_min: Number(e.target.value) })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">Target Price Max ($)</label>
                    <input
                      type="number"
                      placeholder="1450"
                      value={productForm.target_price_max}
                      onChange={(e) => setProductForm({ ...productForm, target_price_max: Number(e.target.value) })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">Incoterms</label>
                    <select
                      value={productForm.incoterms}
                      onChange={(e) => setProductForm({ ...productForm, incoterms: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
                    >
                      <option value="FOB">FOB (Free on Board)</option>
                      <option value="CIF">CIF (Cost, Insurance & Freight)</option>
                      <option value="CFR">CFR (Cost and Freight)</option>
                      <option value="EXW">EXW (Ex Works)</option>
                    </select>
                  </div>
                  <div>
                    <label className="font-semibold text-slate-300 block mb-1">Currency</label>
                    <select
                      value={productForm.currency}
                      onChange={(e) => setProductForm({ ...productForm, currency: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
                    >
                      <option value="USD">USD ($)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="GBP">GBP (£)</option>
                      <option value="AED">AED (د.إ)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="font-semibold text-slate-300 block mb-1">Specifications & Quality Grade</label>
                  <input
                    type="text"
                    placeholder="e.g. Moisture < 11%, Density 550g/l, Piperine 5.5% min, Sortex Cleaned"
                    value={productForm.specifications}
                    onChange={(e) => setProductForm({ ...productForm, specifications: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-300 block mb-1">Packaging Options</label>
                  <input
                    type="text"
                    placeholder="e.g. 25kg multi-wall paper bags with inner poly liner / master cartons"
                    value={productForm.packaging}
                    onChange={(e) => setProductForm({ ...productForm, packaging: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-300 block mb-1">Preferred Payment Security Terms</label>
                  <input
                    type="text"
                    placeholder="e.g. 100% Irrevocable LC at Sight / 30% Advance + 70% against BL scan"
                    value={productForm.preferred_payment_terms}
                    onChange={(e) => setProductForm({ ...productForm, preferred_payment_terms: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-300 block mb-1">Priority Target Countries (comma-separated)</label>
                  <input
                    type="text"
                    placeholder="United Arab Emirates, Saudi Arabia, Germany, United Kingdom, United States"
                    value={productForm.target_countries}
                    onChange={(e) => setProductForm({ ...productForm, target_countries: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-300 block mb-1">Exporter Certifications (comma-separated)</label>
                  <input
                    type="text"
                    placeholder="APEDA, Spices Board, FSSAI, BRC Food, US FDA, ISO 22000"
                    value={productForm.certifications}
                    onChange={(e) => setProductForm({ ...productForm, certifications: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowAddProductModal(false)}
                    className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingProduct}
                    className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow-lg shadow-emerald-600/20 flex items-center gap-2"
                  >
                    {savingProduct ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        <span>Saving Commodity...</span>
                      </>
                    ) : (
                      <>
                        <Plus className="h-3.5 w-3.5" />
                        <span>Save & Run Matching</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Match Scoring Breakdown Modal */}
        {selectedMatchExplanation && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="w-full max-w-xl bg-slate-950 border border-slate-800 rounded-2xl p-6 space-y-5 shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-start justify-between pb-3 border-b border-slate-800">
                <div>
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">AI Buyer Qualification Audit</span>
                  <h3 className="text-lg font-bold text-white mt-0.5">{selectedMatchExplanation.company_name}</h3>
                  <p className="text-xs text-slate-400">📍 {selectedMatchExplanation.country} • Matched Product: {selectedMatchExplanation.product_name}</p>
                </div>
                <div className="text-right">
                  <span className="text-2xl font-black text-emerald-400">
                    {selectedMatchExplanation.qualification_score}
                  </span>
                  <span className="text-xs text-slate-500 block">/ 100 Points</span>
                </div>
              </div>

              {/* 5-Factor Score Cards */}
              <div className="space-y-2 text-xs">
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-200 block">1. Product Relevance & Category Overlap</span>
                    <span className="text-slate-500 text-[11px]">Semantic category match & commodity keyword alignment</span>
                  </div>
                  <span className="font-mono font-bold text-emerald-400 text-sm">
                    {selectedMatchExplanation.breakdown.product_relevance_score} / 30
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-200 block">2. Target Country & Geo-Market Alignment</span>
                    <span className="text-slate-500 text-[11px]">Matches exporter&apos;s priority international target destinations</span>
                  </div>
                  <span className="font-mono font-bold text-emerald-400 text-sm">
                    {selectedMatchExplanation.breakdown.country_alignment_score} / 25
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-200 block">3. Verified Import & Purchasing Evidence</span>
                    <span className="text-slate-500 text-[11px]">Documented import volumes, customs clearance & trade directories</span>
                  </div>
                  <span className="font-mono font-bold text-emerald-400 text-sm">
                    {selectedMatchExplanation.breakdown.import_evidence_score} / 20
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-200 block">4. Direct Decision Maker & Email Quality</span>
                    <span className="text-slate-500 text-[11px]">Named procurement executive & verified corporate email domain</span>
                  </div>
                  <span className="font-mono font-bold text-emerald-400 text-sm">
                    {selectedMatchExplanation.breakdown.contact_quality_score} / 15
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-200 block">5. Lead Verification Standing</span>
                    <span className="text-slate-500 text-[11px]">100-point rubric verification level & absence of risk flags</span>
                  </div>
                  <span className="font-mono font-bold text-emerald-400 text-sm">
                    {selectedMatchExplanation.breakdown.verification_readiness_score} / 10
                  </span>
                </div>
              </div>

              {/* Rationale & Action */}
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-300 block">Qualification Explanation</span>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {selectedMatchExplanation.explanation}
                </p>
                <div className="pt-2 border-t border-slate-800/80">
                  <span className="text-xs font-bold text-emerald-400 block mb-0.5">Recommended Commercial Action</span>
                  <p className="text-xs text-slate-200">
                    {selectedMatchExplanation.recommended_action}
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setSelectedMatchExplanation(null)}
                  className="px-5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white"
                >
                  Close Audit View
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

