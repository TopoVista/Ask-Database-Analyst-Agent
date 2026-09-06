"use client";

import { useRef, useState } from "react";
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

export function DocumentUpload() {
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
  const statusFetched = useRef(false);

  // Load specialist + security status once the user is known.
  const loadStatus = async () => {
    if (!isLoaded || !userId || statusFetched.current) return;
    statusFetched.current = true;
    const token = await getToken();
    try {
      setLoadingStatus("specialists");
      const specResult = await listSpecialists(token);
      setSpecialists(specResult.specialists);
    } catch {
      /* non-critical */
    }
    try {
      setLoadingStatus("audit");
      const auditResult = await runSecurityAudit(token);
      setAudit(auditResult);
    } catch {
      /* non-critical */
    }
    setLoadingStatus(null);
  };
  void loadStatus();

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setUploadResult(null);

    try {
      const token = await getToken();
      const result = await uploadDocument(file, token);
      setUploadResult(result);
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
    <div className="space-y-6">
      {/* Upload Section */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
        <h3 className="text-lg font-medium text-fg flex items-center gap-2">
          <FileUp className="h-5 w-5 text-accent" />
          Upload Document
        </h3>
        <p className="mt-2 text-sm text-fg/66">
          Upload PDF, TXT, Markdown, or HTML files for AI-powered search and analysis.
        </p>

        <div className="mt-4 flex items-center gap-3">
          <input
            type="file"
            accept=".txt,.md,.html,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="flex-1 text-sm text-fg/80 file:mr-4 file:rounded-lg file:border-0 file:bg-white/10 file:px-4 file:py-2 file:text-sm file:font-medium file:text-fg hover:file:bg-white/15"
          />
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-bg transition hover:bg-accent/90 disabled:opacity-50"
          >
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Upload"}
          </button>
        </div>

        {uploadResult && (
          <div className="mt-3 rounded-lg border border-green-500/20 bg-green-500/10 px-3 py-2 text-sm text-green-400">
            ✓ Document indexed: {uploadResult.num_chunks} chunks created
          </div>
        )}
      </div>

      {/* Search Section */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
        <h3 className="text-lg font-medium text-fg flex items-center gap-2">
          <Search className="h-5 w-5 text-accent" />
          Search Documents
        </h3>
        <p className="mt-2 text-sm text-fg/66">
          Ask questions about your uploaded documents.
        </p>

        <div className="mt-4 flex items-center gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="What would you like to know?"
            className="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-fg placeholder:text-fg/40 focus:border-accent focus:outline-none"
          />
          <button
            onClick={handleSearch}
            disabled={searching || !query.trim()}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-bg transition hover:bg-accent/90 disabled:opacity-50"
          >
            {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="mt-4 space-y-3">
            {searchResults.map((result, idx) => (
              <div key={idx} className="rounded-lg border border-white/10 bg-white/5 p-3">
                <p className="text-sm text-fg/80">{result.chunk_text}</p>
                <div className="mt-2 flex items-center gap-2 text-xs text-fg/50">
                  <span>Source: {result.source}</span>
                  <span>•</span>
                  <span>Score: {result.score.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}
