import { useEffect, useState } from "react";

declare global {
  interface Window {
    api: {
      ping: () => Promise<string>;
      backendRequest: (
        cmd:
          | "ping"
          | "add_entry"
          | "list_entries"
          | "get_entry"
          | "update_entry"
          | "delete_entry"
          | "list_relations"
          | "upsert_relation"
          | "search_entries"
          | "add_record"
          | "update_record"
          | "get_record"
          | "list_records"
          | "link_record"
          | "unlink_record"
          | "resolve_entry"
          | "get_synonyms"
          | "semantic_status"
          | "rebuild_embeddings"
          | "ann_status"
          | "ann_apply_updates"
          | "rebuild_ann_index",
        payload: any
      ) => Promise<any>;
    };
    logs: {
      getPath: () => Promise<string>;
      getTail: () => Promise<{ path: string; ring: string[]; fileTail: string }>;
      openFolder: () => Promise<boolean>;
    };
  }
}

type Entry = {
  id: number;
  language: "en" | "zh";
  word: string;
  translation: string;
  notes?: string;
  deleted_at?: number | null;
};

type Relation = {
  id: number;
  from_id: number;
  to_id: number;
  type: string;
};

type Annotation = {
  start: number;
  end: number;
  surface: string;
  entry_id?: number | null;
  score?: number | null;
  match_type?: string | null;
  candidates?: { entry_id: number; word: string; language: string; score: number; match_type: string }[];
};

type RecordItem = {
  id: number;
  text: string;
  created_at?: number;
  updated_at?: number;
  annotations?: Annotation[];
};

type SynonymResult = {
  entry_id: number;
  word: string;
  language: string;
  translation?: string;
  distance?: number;
  via?: string;
  score?: number | null;
  match_type?: string;
};

function App() {
  const [status, setStatus] = useState("Click to ping main process");
  const [language, setLanguage] = useState<"en" | "zh">("en");
  const [word, setWord] = useState("");
  const [translation, setTranslation] = useState("");
  const [notes, setNotes] = useState("");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Entry | null>(null);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [editTranslation, setEditTranslation] = useState("");
  const [editWord, setEditWord] = useState("");
  const [editLanguage, setEditLanguage] = useState<"en" | "zh">("en");
  const [editNotes, setEditNotes] = useState("");
  const [query, setQuery] = useState("");
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [recordText, setRecordText] = useState("");
  const [selectedRecord, setSelectedRecord] = useState<RecordItem | null>(null);
  const [candidateAnn, setCandidateAnn] = useState<{ recordId: number; ann: Annotation } | null>(null);
  const [candidateLoading, setCandidateLoading] = useState(false);
  const [candidateResults, setCandidateResults] = useState<
    { entry_id: number; word: string; language: string; score: number; match_type: string }[]
  >([]);
  const [candidateError, setCandidateError] = useState<string | null>(null);
  const [searchMode, setSearchMode] = useState<"like" | "fts" | "fuzzy" | "semantic">("fts");
  const [logPath, setLogPath] = useState("");
  const [logTail, setLogTail] = useState<string[]>([]);
  const [logFileTail, setLogFileTail] = useState("");
  const [synGraph, setSynGraph] = useState<SynonymResult[]>([]);
  const [synFallback, setSynFallback] = useState<SynonymResult[]>([]);
  const [synCandidates, setSynCandidates] = useState<SynonymResult[]>([]);
  const [synLoading, setSynLoading] = useState(false);
  const [synError, setSynError] = useState<string | null>(null);

  const handlePing = async () => {
    const res = await window.api.ping();
    setStatus(`Received: ${res}`);
  };

  const loadEntries = async () => {
    const res = await window.api.backendRequest("list_entries", { limit: 100, offset: 0 });
    if (res?.ok) setEntries(res.data || []);
  };

  const handleAdd = async () => {
    if (!word.trim()) {
      alert("Please enter a word");
      return;
    }
    const res = await window.api
      .backendRequest("add_entry", {
        language,
        word: word.trim(),
        translation: translation.trim(),
        notes: notes.trim()
      })
      .catch((err) => {
        console.error("backendRequest add_entry failed", err);
        return null;
      });
    if (res?.ok) {
      setWord("");
      setTranslation("");
      setNotes("");
      await loadEntries();
    } else {
      const errMsg = res?.error?.message || res?.error?.code || "unknown error";
      alert(`Add failed: ${errMsg}`);
    }
  };

  const loadDetail = async (id: number) => {
    const res = await window.api.backendRequest("get_entry", { id });
    if (res?.ok) {
      setDetail(res.data);
      setEditLanguage(res.data.language);
      setEditWord(res.data.word);
      setEditTranslation(res.data.translation || "");
      setEditNotes(res.data.notes || "");
    }
    const rel = await window.api.backendRequest("list_relations", { id });
    if (rel?.ok) setRelations(rel.data || []);
  };

  const handleSelect = async (id: number) => {
    setSelectedId(id);
    await loadDetail(id);
    setSynGraph([]);
    setSynFallback([]);
    setSynCandidates([]);
    setSynError(null);
  };

  const handleUpdate = async () => {
    if (!detail) return;
    const res = await window.api
      .backendRequest("update_entry", {
        id: detail.id,
        language: editLanguage,
        word: editWord,
        translation: editTranslation,
        notes: editNotes
      })
      .catch((err) => {
        console.error("backendRequest update_entry failed", err);
        return null;
      });
    if (res?.ok) {
      await loadEntries();
      await loadDetail(detail.id);
    } else {
      const errMsg = res?.error?.message || res?.error?.code || "unknown error";
      alert(`Update failed: ${errMsg}`);
    }
  };

  const handleDelete = async () => {
    if (!detail) return;
    const res = await window.api
      .backendRequest("delete_entry", { id: detail.id })
      .catch((err) => {
        console.error("backendRequest delete_entry failed", err);
        return null;
      });
    if (res?.ok) {
      setSelectedId(null);
      setDetail(null);
      setRelations([]);
      await loadEntries();
    } else {
      const errMsg = res?.error?.message || res?.error?.code || "unknown error";
      alert(`Delete failed: ${errMsg}`);
    }
  };

  const loadRecords = async () => {
    const res = await window.api.backendRequest("list_records", { limit: 50, offset: 0 });
    if (res?.ok) {
      setRecords(res.data || []);
    }
  };

  const handleAddRecord = async () => {
    if (!recordText.trim()) {
      alert("Please enter record text");
      return;
    }
    const res = await window.api.backendRequest("add_record", { text: recordText.trim() });
    if (res?.ok) {
      setRecordText("");
      await loadRecords();
      if (res.data?.record_id) {
        await handleSelectRecord(res.data.record_id);
      }
    } else {
      const errMsg = res?.error?.message || res?.error?.code || "unknown error";
      alert(`Add record failed: ${errMsg}`);
    }
  };

  const handleSelectRecord = async (rid: number) => {
    const res = await window.api.backendRequest("get_record", { record_id: rid });
    if (res?.ok) {
      setSelectedRecord(res.data);
      setCandidateAnn(null);
      setCandidateResults([]);
      setCandidateError(null);
      setSynGraph([]);
      setSynFallback([]);
      setSynCandidates([]);
      setSynError(null);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!query) {
        loadEntries();
      } else {
        window.api
          .backendRequest("search_entries", { q: query, mode: searchMode, limit: 100, offset: 0 })
          .then((res) => {
            if (res?.ok) setEntries(res.data || []);
            else if (res?.error?.code === "SEMANTIC_DISABLED") {
              alert("Semantic search disabled or missing dependency.");
            }
          });
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [query, searchMode]);

  useEffect(() => {
    loadEntries();
    loadRecords();
    window.logs.getPath().then(setLogPath).catch(() => undefined);
    window.logs.getTail().then((res) => {
      setLogTail(res.ring || []);
      setLogFileTail(res.fileTail || "");
    });
  }, []);

  const highlight = (text: string, qstr: string) => {
    if (!qstr) return text;
    const lower = text.toLowerCase();
    const idx = lower.indexOf(qstr.toLowerCase());
    if (idx === -1) return text;
    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + qstr.length);
    const after = text.slice(idx + qstr.length);
    return (
      <>
        {before}
        <mark>{match}</mark>
        {after}
      </>
    );
  };

  const renderAnnotated = (rec: RecordItem) => {
    const anns = (rec.annotations || []).slice().sort((a, b) => a.start - b.start);
    const pieces: JSX.Element[] = [];
    let cursor = 0;
    for (const ann of anns) {
      if (cursor < ann.start) {
        pieces.push(<span key={`text-${cursor}`}>{rec.text.slice(cursor, ann.start)}</span>);
      }
      const tokenText = rec.text.slice(ann.start, ann.end);
      const linked = !!ann.entry_id;
      pieces.push(
        <mark
          key={`ann-${ann.start}-${ann.end}`}
          style={{
            cursor: "pointer",
            backgroundColor: linked ? "#ffe58f" : "#e6f4ff",
            padding: "0 3px",
            borderRadius: 3,
            display: "inline-block"
          }}
          role="button"
          tabIndex={0}
          onClick={() => handleTokenClick(rec.id, ann)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleTokenClick(rec.id, ann);
            }
          }}
          title={
            ann.entry_id
              ? `Linked entry #${ann.entry_id} (${ann.match_type || ""}, score ${ann.score?.toFixed(2) || "-"}) - click to see candidates`
              : "No link yet - click to resolve candidates"
          }
        >
          {tokenText}
        </mark>
      );
      cursor = ann.end;
    }
    if (cursor < rec.text.length) {
      pieces.push(<span key={`tail-${cursor}`}>{rec.text.slice(cursor)}</span>);
    }
    return pieces;
  };

  const guessLanguage = (surface: string): "en" | "zh" | undefined => {
    const hasEn = /[A-Za-z]/.test(surface);
    const hasZh = /[\u4e00-\u9fff]/.test(surface);
    if (hasEn && !hasZh) return "en";
    if (hasZh && !hasEn) return "zh";
    return undefined;
  };

  const handleTokenClick = async (recordId: number, ann: Annotation) => {
    console.log("token click", recordId, ann);
    setCandidateAnn({ recordId, ann });
    setCandidateLoading(true);
    setCandidateError(null);
    setCandidateResults([]);
    try {
      const lang = guessLanguage(ann.surface);
      const res = await window.api.backendRequest("resolve_entry", {
        q: ann.surface,
        language: lang,
        topK: 8
      });
      if (res?.ok) {
        setCandidateResults(res.data?.candidates || []);
      } else {
        setCandidateError(res?.error?.message || res?.error?.code || "resolve failed");
      }
    } catch (e: any) {
      setCandidateError(e?.message || String(e));
    } finally {
      setCandidateLoading(false);
    }
  };

  const handleLinkCandidate = async (entryId: number) => {
    if (!candidateAnn) return;
    try {
      const res = await window.api.backendRequest("link_record", {
        record_id: candidateAnn.recordId,
        entry_id: entryId,
        start: candidateAnn.ann.start,
        end: candidateAnn.ann.end,
        surface: candidateAnn.ann.surface
      });
      if (res?.ok) {
        await handleSelectRecord(candidateAnn.recordId);
        setCandidateAnn(null);
        setCandidateResults([]);
      } else {
        alert(res?.error?.message || res?.error?.code || "Link failed");
      }
    } catch (e: any) {
      alert(e?.message || String(e));
    }
  };

  const handleUnlink = async () => {
    if (!candidateAnn || !candidateAnn.ann.entry_id) return;
    try {
      const res = await window.api.backendRequest("unlink_record", {
        record_id: candidateAnn.recordId,
        entry_id: candidateAnn.ann.entry_id,
        start: candidateAnn.ann.start,
        end: candidateAnn.ann.end
      });
      if (res?.ok) {
        await handleSelectRecord(candidateAnn.recordId);
        setCandidateAnn(null);
        setCandidateResults([]);
      } else {
        alert(res?.error?.message || res?.error?.code || "Unlink failed");
      }
    } catch (e: any) {
      alert(e?.message || String(e));
    }
  };

  const handleFindSynonyms = async () => {
    if (!detail) return;
    setSynLoading(true);
    setSynError(null);
    try {
      const res = await window.api.backendRequest("get_synonyms", {
        q: detail.word,
        language: detail.language,
        depth: 2,
        topK: 20,
        fallback: true,
        includeTypes: ["synonym", "translation"]
      });
      if (res?.ok) {
        setSynGraph(res.data?.graph_results || []);
        setSynFallback(res.data?.fallback_results || []);
        setSynCandidates(res.data?.candidates || []);
      } else {
        setSynError(res?.error?.message || res?.error?.code || "get_synonyms failed");
      }
    } catch (e: any) {
      setSynError(e?.message || String(e));
    } finally {
      setSynLoading(false);
    }
  };

  const handleRunSynonymsWithCandidate = async (cand: SynonymResult) => {
    setSynLoading(true);
    setSynError(null);
    try {
      const res = await window.api.backendRequest("get_synonyms", {
        q: cand.word,
        language: cand.language,
        depth: 2,
        topK: 20,
        fallback: true,
        includeTypes: ["synonym", "translation"]
      });
      if (res?.ok) {
        setSynGraph(res.data?.graph_results || []);
        setSynFallback(res.data?.fallback_results || []);
        setSynCandidates(res.data?.candidates || []);
      } else {
        setSynError(res?.error?.message || res?.error?.code || "get_synonyms failed");
      }
    } catch (e: any) {
      setSynError(e?.message || String(e));
    } finally {
      setSynLoading(false);
    }
  };

  const handleAddSynonym = async (targetId: number) => {
    if (!detail) return;
    const res = await window.api.backendRequest("upsert_relation", {
      from_id: detail.id,
      to_id: targetId,
      type: "synonym"
    });
    if (res?.ok) {
      await handleFindSynonyms();
    } else {
      alert(res?.error?.message || res?.error?.code || "Add synonym failed");
    }
  };

  return (
    <div style={{ padding: "24px", fontFamily: "Inter, sans-serif", maxWidth: 900 }}>
      <h1>AI Vocab Notebook</h1>
      <p>Step 3: CRUD + relations +多页布局（简化版）。</p>
      <button onClick={handlePing}>Ping main</button>
      <p>{status}</p>

      <div style={{ marginTop: 16, padding: 12, border: "1px solid #ccc", borderRadius: 8 }}>
        <h3>Add entry</h3>
        <label>
          Language:
          <select value={language} onChange={(e) => setLanguage(e.target.value as "en" | "zh")}>
            <option value="en">English</option>
            <option value="zh">Chinese</option>
          </select>
        </label>
        <br />
        <label>
          Word: <input value={word} onChange={(e) => setWord(e.target.value)} />
        </label>
        <br />
        <label>
          Translation: <input value={translation} onChange={(e) => setTranslation(e.target.value)} />
        </label>
        <br />
        <label>
          Notes: <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <br />
        <button onClick={handleAdd}>Add</button>
      </div>

      <div style={{ marginTop: 24, padding: 12, border: "1px solid #ccc", borderRadius: 8 }}>
        <h3>Records (auto-link)</h3>
        <textarea
          value={recordText}
          onChange={(e) => setRecordText(e.target.value)}
          rows={3}
          style={{ width: "100%", marginBottom: 8 }}
          placeholder="输入中英混合文本，自动尝试链接到已有词条..."
        />
        <button onClick={handleAddRecord}>Save record</button>
        <button onClick={loadRecords} style={{ marginLeft: 8 }}>
          Refresh
        </button>
        <div style={{ marginTop: 12 }}>
          {records.map((r) => (
            <div key={r.id} style={{ marginBottom: 8 }}>
              <button onClick={() => handleSelectRecord(r.id)} style={{ marginRight: 8 }}>
                View
              </button>
              <span>#{r.id} </span>
              <span title={r.text}>{r.text.slice(0, 40)}{r.text.length > 40 ? "..." : ""}</span>
            </div>
          ))}
        </div>
        {selectedRecord && (
          <div style={{ marginTop: 12, padding: 8, border: "1px solid #ddd" }}>
            <h4>Record #{selectedRecord.id}</h4>
            <div style={{ lineHeight: 1.8 }}>
              {selectedRecord.annotations && selectedRecord.annotations.length > 0 ? (
                renderAnnotated(selectedRecord)
              ) : (
                <span style={{ color: "#888" }}>No tokens found in this record.</span>
              )}
            </div>
            <div style={{ marginTop: 6, color: "#666", fontSize: 12 }}>
              点击上方高亮词，弹出候选面板；黄色=已链接，浅蓝=未链接。
            </div>
          </div>
        )}
        {candidateAnn && (
          <div style={{ marginTop: 12, padding: 8, border: "2px solid #91caff", borderRadius: 6, background: "#fafafa" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>
                Candidates for "{candidateAnn.ann.surface}" (record #{candidateAnn.recordId})
              </strong>
              <div>
                {candidateAnn.ann.entry_id ? (
                  <button onClick={handleUnlink} style={{ marginRight: 8 }}>
                    Unlink current
                  </button>
                ) : null}
                <button onClick={() => setCandidateAnn(null)}>Close</button>
              </div>
            </div>
            {candidateLoading && <p>Loading...</p>}
            {candidateError && <p style={{ color: "red" }}>{candidateError}</p>}
            {!candidateLoading && !candidateError && (
              <ul>
                {candidateResults.length === 0 && <li>No candidates</li>}
                {candidateResults.map((c) => (
                  <li key={`${c.entry_id}-${c.match_type}`}>
                    #{c.entry_id} [{c.language}] {c.word} — score {c.score.toFixed(2)} ({c.match_type})
                    {c.entry_id ? (
                      <>
                        <button style={{ marginLeft: 8 }} onClick={() => handleSelect(c.entry_id)}>
                          View entry
                        </button>
                        <button style={{ marginLeft: 8 }} onClick={() => handleLinkCandidate(c.entry_id)}>
                          Link
                        </button>
                      </>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div style={{ marginTop: 16 }}>
        <h3>Entries</h3>
        <input
          placeholder="Search..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginRight: 8 }}
        />
        <select value={searchMode} onChange={(e) => setSearchMode(e.target.value as any)} style={{ marginRight: 8 }}>
          <option value="fts">FTS</option>
          <option value="like">Like</option>
          <option value="fuzzy">Fuzzy</option>
          <option value="semantic">Semantic</option>
        </select>
          <button onClick={loadEntries} style={{ marginBottom: 8 }}>
            Refresh
          </button>
        <ul>
          {entries.map((e) => (
            <li key={e.id}>
              <button onClick={() => handleSelect(e.id)} style={{ marginRight: 8 }}>
                View
              </button>
              [{e.language}] {highlight(e.word, query)} — {highlight(e.translation || "", query)}{" "}
              {e.deleted_at ? "(deleted)" : ""}
            </li>
          ))}
        </ul>
      </div>

      {detail && (
        <div style={{ marginTop: 16, padding: 12, border: "1px solid #ccc", borderRadius: 8 }}>
          <h3>Detail</h3>
          <p>
            ID: {detail.id} [{detail.language}] {detail.word} — {detail.translation}
          </p>
          <p>
            Notes: {detail.notes || "-"}
          </p>
          <h4>Edit</h4>
          <label>
            Language:
            <select value={editLanguage} onChange={(e) => setEditLanguage(e.target.value as "en" | "zh")}>
              <option value="en">English</option>
              <option value="zh">Chinese</option>
            </select>
          </label>
          <br />
          <label>
            Word: <input value={editWord} onChange={(e) => setEditWord(e.target.value)} />
          </label>
          <br />
          <label>
            Translation: <input value={editTranslation} onChange={(e) => setEditTranslation(e.target.value)} />
          </label>
          <br />
          <label>
            Notes: <input value={editNotes} onChange={(e) => setEditNotes(e.target.value)} />
          </label>
          <br />
          <button onClick={handleUpdate}>Save</button>
          <button onClick={handleDelete} style={{ marginLeft: 8 }}>
            Delete (soft)
          </button>

          <h4 style={{ marginTop: 12 }}>Relations</h4>
          <ul>
            {relations.map((r) => (
              <li key={r.id}>
                {r.type}: {r.from_id} → {r.to_id}
              </li>
            ))}
          </ul>

          <div style={{ marginTop: 16, padding: 10, border: "1px solid #ddd", borderRadius: 6 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <h4 style={{ margin: 0 }}>Synonyms / Related</h4>
              <button onClick={handleFindSynonyms} disabled={synLoading}>
                {synLoading ? "Loading..." : "Find synonyms"}
              </button>
            </div>
            {synError && <p style={{ color: "red" }}>{synError}</p>}
            {synCandidates.length > 0 && synGraph.length === 0 && (
              <div style={{ marginTop: 8 }}>
                <strong>No exact entry found. Pick a candidate to start:</strong>
                <ul>
                  {synCandidates.map((c) => (
                    <li key={`cand-${c.entry_id}-${c.word}`}>
                      #{c.entry_id} [{c.language}] {c.word}{" "}
                      <button style={{ marginLeft: 8 }} onClick={() => handleRunSynonymsWithCandidate(c)}>
                        Use this
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div style={{ marginTop: 8 }}>
              <strong>Graph results</strong>
              {synGraph.length === 0 ? (
                <p style={{ color: "#666" }}>No graph results yet.</p>
              ) : (
                <ul>
                  {synGraph.map((g) => (
                    <li key={`graph-${g.entry_id}`}>
                      #{g.entry_id} [{g.language}] {g.word} (dist {g.distance}, via {g.via || "-"})
                      <button style={{ marginLeft: 8 }} onClick={() => handleSelect(g.entry_id)}>
                        View entry
                      </button>
                      <button style={{ marginLeft: 8 }} onClick={() => handleAddSynonym(g.entry_id)}>
                        Add as synonym
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div style={{ marginTop: 8 }}>
              <strong>AI match candidates</strong>
              {synFallback.length === 0 ? (
                <p style={{ color: "#666" }}>No fallback candidates.</p>
              ) : (
                <ul>
                  {synFallback.map((g) => (
                    <li key={`fb-${g.entry_id}-${g.match_type}`}>
                      #{g.entry_id} [{g.language}] {g.word} (match {g.match_type}, score {g.score ?? "-"})
                      <button style={{ marginLeft: 8 }} onClick={() => handleSelect(g.entry_id)}>
                        View entry
                      </button>
                      <button style={{ marginLeft: 8 }} onClick={() => handleAddSynonym(g.entry_id)}>
                        Add as synonym
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      <div style={{ marginTop: 24, padding: 12, border: "1px solid #ccc", borderRadius: 8 }}>
        <h3>Diagnostics / Logs</h3>
        <p>Log path: <code>{logPath}</code></p>
        <button onClick={() => window.logs.openFolder()}>Open log folder</button>
        <button
          style={{ marginLeft: 8 }}
          onClick={async () => {
            const res = await window.logs.getTail();
            setLogTail(res.ring || []);
            setLogFileTail(res.fileTail || "");
          }}
        >
          Refresh logs
        </button>
        <div style={{ marginTop: 8 }}>
          <strong>Recent (ring buffer):</strong>
          <pre style={{ maxHeight: 200, overflow: "auto", background: "#f7f7f7", padding: 8 }}>
            {logTail.join("\n")}
          </pre>
        </div>
        <div style={{ marginTop: 8 }}>
          <strong>File tail:</strong>
          <pre style={{ maxHeight: 200, overflow: "auto", background: "#f7f7f7", padding: 8 }}>
            {logFileTail}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default App;
