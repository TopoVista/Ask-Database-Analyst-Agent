"use client";

import { useState } from "react";
import { FileUp, Loader2, Search, ShieldCheck, Users } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import {
  listSpecialists,
  runSecurityAudit,
  searchDocuments,
  uploadDocument,
  type AuditFinding,
  type DocumentSearchResult,
  type SpecialistInfo,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function DocumentsPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ source: string; num_chunks: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<DocumentSearchResult[]>([]);
  const [specialists, setSpecialists] = useState<SpecialistInfo[]>([]);
  const [audit, setAudit] = useState<{ passed: boolean; findings: AuditFinding[] } | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<"specialists" | "audit" | null>(null);

  const loadStatus = async () => {
    if (!isLoaded || !userId) return;
    const token = await getToken();
    try {
      setLoadingStatus("specialists");
      const specResult = await listSpecialists(token);
      setSpecialists(specResult.specialists);
    } catch { /* non-critical */ }
    try {
      setLoadingStatus("audit");
      const auditResult = await runSecurityAudit(token);
      setAudit(auditResult);
    } catch { /* non-critical */ }
    setLoadingStatus(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setUploadResult(null);
    try {
      const token = await getToken();
      const result = await uploadDocument(file, token);
      setUploadResult(result);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const token = await getToken();
      const result = await searchDocuments(query, token, 5);
      setSearchResults(result.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6 px-4 py-6 md:px-6 lg:px-8">
      <Card>
        <CardHeader className="border-b border-white/10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <Badge className="border-accent/20 bg-accent/10 text-accent">RAG & Document Intelligence</Badge>
              <CardTitle className="mt-4 text-3xl">Upload documents and query them</CardTitle>
              <CardDescription className="mt-3 text-base text-fg/72">
                Upload PDF, TXT, Markdown, or HTML files for semantic retrieval.
              </CardDescription>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <DocMetric label="Specialists" value={String(specialists.length)} icon={Users} />
              <DocMetric label="Audit" value={audit ? (audit.passed ? "Passed" : "Issues") : "Pending"} icon={ShieldCheck} />
              <DocMetric label="Status" value={loadingStatus ?? "Ready"} icon={FileUp} />
            </div>
          </div>
        </CardHeader>
      </Card>
      <div className="grid gap-6 xl:grid-cols-[1fr,1fr]">
        <UploadSection file={file} uploading={uploading} uploadResult={uploadResult} error={error} onFileChange={setFile} onUpload={handleUpload} />
        <SearchSection query={query} searching={searching} searchResults={searchResults} onQueryChange={setQuery} onSearch={handleSearch} />
      </div>
      {audit && <SecurityAuditSection audit={audit} />}
    </div>
  );
}

function DocMetric({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="rounded-[22px] border border-white/10 bg-[rgba(10,16,27,0.9)] px-4 py-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-accent" />
        <p className="text-[10px] uppercase tracking-[0.22em] text-muted-fg">{label}</p>
      </div>
      <p className="mt-3 text-lg font-semibold text-fg">{value}</p>
    </div>
  );
}

function UploadSection({ file, uploading, uploadResult, error, onFileChange, onUpload }: {
  file: File | null; uploading: boolean; uploadResult: { source: string; num_chunks: number } | null;
  error: string | null; onFileChange: (f: File | null) => void; onUpload: () => void;
}) {
  return (
    <Card>
      <CardHeader><CardTitle>Upload Document</CardTitle><CardDescription>Upload files for RAG indexing</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <Input type="file" accept=".txt,.md,.html,.pdf" onChange={(e) => onFileChange(e.target.files?.[0] || null)} className="flex-1" />
          <Button onClick={onUpload} disabled={!file || uploading}>
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Upload"}
          </Button>
        </div>
        {uploadResult && (
          <div className="rounded-lg border border-green-500/20 bg-green-500/10 px-3 py-2 text-sm text-green-400">
            Document indexed: {uploadResult.num_chunks} chunks created
          </div>
        )}
        {error && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>
        )}
      </CardContent>
    </Card>
  );
}

function SearchSection({ query, searching, searchResults, onQueryChange, onSearch }: {
  query: string; searching: boolean; searchResults: DocumentSearchResult[];
  onQueryChange: (q: string) => void; onSearch: () => void;
}) {
  return (
    <Card>
      <CardHeader><CardTitle>Search Documents</CardTitle><CardDescription>Ask questions about your documents</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <Input value={query} onChange={(e) => onQueryChange(e.target.value)} onKeyDown={(e) => e.key === "Enter" && onSearch()} placeholder="What would you like to know?" className="flex-1" />
          <Button onClick={onSearch} disabled={searching || !query.trim()}>
            {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </Button>
        </div>
        {searchResults.length > 0 && (
          <div className="space-y-3">
            {searchResults.map((result, idx) => (
              <div key={idx} className="rounded-[20px] border border-white/10 bg-[rgba(9,15,25,0.9)] p-4">
                <p className="text-sm text-fg/80">{result.chunk_text}</p>
                <div className="mt-2 flex items-center gap-2 text-xs text-fg/50">
                  <span>Source: {result.source}</span><span>-</span><span>Score: {result.score.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SecurityAuditSection({ audit }: { audit: { passed: boolean; findings: AuditFinding[] } }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Security Audit</CardTitle>
        <CardDescription>{audit.passed ? "All security checks passed." : `${audit.findings.length} findings detected.`}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {audit.findings.length ? audit.findings.map((finding, idx) => (
          <div key={idx} className="rounded-[20px] border border-white/10 bg-[rgba(9,15,25,0.9)] p-4">
            <div className="flex items-center gap-2">
              <Badge className={finding.severity === "critical" ? "border-danger/40 bg-danger/10 text-danger" : finding.severity === "high" ? "border-warning/40 bg-warning/10 text-warning" : "border-white/10 bg-white/6 text-fg/80"}>{finding.severity}</Badge>
              <span className="text-sm font-medium text-fg">{finding.category}</span>
            </div>
            <p className="mt-2 text-sm text-fg/70">{finding.message}</p>
          </div>
        )) : <p className="text-sm text-muted-fg">No security findings.</p>}
      </CardContent>
    </Card>
  );
}
