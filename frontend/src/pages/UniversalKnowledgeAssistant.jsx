import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1/knowledge-assistant';

export default function UniversalKnowledgeAssistant() {
  const [query, setQuery] = useState('');
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [activeMessage, setActiveMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('answer');
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [answerDepth, setAnswerDepth] = useState('direct');
  const [deleteModalSession, setDeleteModalSession] = useState(null);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const getAuthHeader = () => {
    const token = localStorage.getItem('access_token');
    return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
  };

  const fetchSessions = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/sessions/`, getAuthHeader());
      if (resp.data) {
        setSessions(resp.data);
        if (resp.data.length > 0 && !activeSessionId) {
          loadSession(resp.data[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to fetch assistant sessions:', err);
    }
  };

  const loadSession = async (sessionId) => {
    try {
      setActiveSessionId(sessionId);
      const resp = await axios.get(`${API_BASE}/sessions/${sessionId}/`, getAuthHeader());
      const sData = resp.data;
      setMessages(sData.messages || []);
      if (sData.messages && sData.messages.length > 0) {
        const lastAssistant = [...sData.messages].reverse().find(m => m.role === 'assistant');
        setActiveMessage(lastAssistant || null);
      } else {
        setActiveMessage(null);
      }
    } catch (err) {
      console.error(`Failed to load session ${sessionId}:`, err);
    }
  };

  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setActiveMessage(null);
    setQuery('');
  };

  const handleDeleteSessionConfirm = async () => {
    if (!deleteModalSession) return;
    const targetId = deleteModalSession.id;
    try {
      await axios.delete(`${API_BASE}/sessions/${targetId}/`, getAuthHeader());
      setDeleteModalSession(null);
      
      const updatedList = sessions.filter(s => s.id !== targetId);
      setSessions(updatedList);
      
      if (activeSessionId === targetId) {
        if (updatedList.length > 0) {
          loadSession(updatedList[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      console.error(`Failed to delete session ${targetId}:`, err);
      alert('Failed to delete conversation.');
    }
  };

  const handleSendQuery = async (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userText = query;
    setQuery('');
    setLoading(true);

    const tempUserMsg = { role: 'user', content: userText, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const resp = await axios.post(`${API_BASE}/chat/`, {
        query: userText,
        session_id: activeSessionId
      }, getAuthHeader());

      const data = resp.data;
      setActiveSessionId(data.session_id);

      const assistantMsg = {
        role: 'assistant',
        query_text: userText,
        content: data.answer,
        response_levels: data.response_levels || {},
        evidence_and_sources: data.evidence_and_sources || {},
        kg_path: data.kg_path || data.knowledge_paths || [],
        claims_mapping: data.claims_mapping || [],
        observed_patterns: data.observed_patterns || [],
        intent_category: data.intent_category,
        retrieval_method: data.retrieval_method,
        evidence_chunks: data.evidence_chunks || [],
        knowledge_paths: data.knowledge_paths || [],
        sources: data.sources || [],
        model_used: data.model_used,
        latency_seconds: data.latency_seconds,
        created_at: data.created_at
      };

      setMessages(prev => [...prev, assistantMsg]);
      setActiveMessage(assistantMsg);
      setActiveTab('answer');
      setAnswerDepth('direct');

      // Refresh session sidebar list to reflect new title/count
      fetchSessions();
    } catch (err) {
      console.error('Chat execution failed:', err);
      const detailMsg = err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || err.message;
      const errorMsg = {
        role: 'assistant',
        content: detailMsg ? `Failed to process query: ${detailMsg}` : 'Failed to process query. Ensure local Ollama daemon and Django backend are running.',
        evidence_chunks: [],
        knowledge_paths: [],
        sources: []
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    try {
      const resp = await axios.post(`${API_BASE}/reindex/`, {}, getAuthHeader());
      alert(`Re-index complete!\nVector chunks: ${resp.data.vector_chunks}\nGraph nodes: ${resp.data.graph_nodes}`);
    } catch (err) {
      console.error('Re-index failed:', err);
      alert('Failed to re-index dataset library.');
    } finally {
      setReindexing(false);
    }
  };

  // Active Session Title
  const activeSessionObj = sessions.find(s => s.id === activeSessionId);
  const activeSessionTitle = activeSessionObj ? activeSessionObj.title : 'New Conversation';

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden', backgroundColor: '#f8fafc', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* LEFT SIDEBAR: ChatGPT-Style Conversations */}
      <div style={{ width: '280px', height: '100vh', flexShrink: 0, backgroundColor: '#0f172a', color: '#f8fafc', display: 'flex', flexDirection: 'column', borderRight: '1px solid #1e293b', overflow: 'hidden' }}>
        
        {/* Sidebar Header + New Chat Button */}
        <div style={{ padding: '16px', borderBottom: '1px solid #1e293b', flexShrink: 0 }}>
          <div style={{ fontSize: '14px', fontWeight: '700', color: '#93c5fd', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🧠</span> Enterprise Assistant
          </div>
          <button
            onClick={handleNewChat}
            style={{
              width: '100%',
              backgroundColor: '#2563eb',
              color: '#fff',
              border: 'none',
              padding: '10px 14px',
              borderRadius: '8px',
              fontWeight: '600',
              fontSize: '14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
            }}
          >
            <span>+</span> New Chat
          </button>
        </div>

        {/* Conversation History List */}
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '12px 8px' }}>
          <div style={{ fontSize: '11px', fontWeight: '700', color: '#64748b', textTransform: 'uppercase', padding: '0 8px 8px 8px' }}>
            Recent Conversations
          </div>

          {sessions.length === 0 ? (
            <div style={{ fontSize: '13px', color: '#64748b', padding: '12px 8px', fontStyle: 'italic' }}>
              No previous conversations.
            </div>
          ) : (
            sessions.map(s => {
              const isActive = s.id === activeSessionId;
              return (
                <div
                  key={s.id}
                  onClick={() => loadSession(s.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    marginBottom: '4px',
                    cursor: 'pointer',
                    backgroundColor: isActive ? '#1e293b' : 'transparent',
                    borderLeft: isActive ? '3px solid #3b82f6' : '3px solid transparent',
                    color: isActive ? '#fff' : '#cbd5e1',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13px', fontWeight: isActive ? '600' : '400', flex: 1, marginRight: '6px' }}>
                    {s.title}
                  </div>
                  
                  {/* Delete Conversation Action */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteModalSession(s);
                    }}
                    title="Delete Conversation"
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#64748b',
                      cursor: 'pointer',
                      fontSize: '14px',
                      padding: '2px 4px',
                      borderRadius: '4px'
                    }}
                    onMouseEnter={(e) => e.target.style.color = '#ef4444'}
                    onMouseLeave={(e) => e.target.style.color = '#64748b'}
                  >
                    🗑️
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Sidebar Footer */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid #1e293b', fontSize: '11px', color: '#64748b', textAlign: 'center', flexShrink: 0 }}>
          Phase 6 • Universal Enterprise Assistant
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div style={{ flex: 1, minWidth: 0, height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        
        {/* Header Bar */}
        <div style={{ height: '64px', flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#fff', padding: '0 24px', borderBottom: '1px solid #e2e8f0', boxShadow: '0 1px 2px rgba(0,0,0,0.03)' }}>
          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            <h2 style={{ margin: 0, fontSize: '17px', color: '#0f172a', fontWeight: '700', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {activeSessionTitle}
            </h2>
            <p style={{ margin: '2px 0 0 0', color: '#64748b', fontSize: '12px' }}>
              Evidence-Grounded Adaptive Intelligence • Local Phi-3.5 Mini (3.8B Q4)
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexShrink: 0 }}>
            <span style={{ backgroundColor: '#e0f2fe', color: '#0369a1', padding: '6px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: '600' }}>
              🤖 Active LLM: Phi-3.5 Mini (3.8B Q4)
            </span>
            <button
              onClick={handleReindex}
              disabled={reindexing}
              style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', padding: '8px 14px', borderRadius: '6px', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}
            >
              {reindexing ? 'Re-indexing...' : '⚡ Re-index Datasets'}
            </button>
          </div>
        </div>

        {/* MAIN WORKSPACE GRID: Conversation Stream + Grounded Console */}
        <div style={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: '1fr 440px', overflow: 'hidden' }}>
          
          {/* Left Panel: Conversation Stream & Input */}
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, overflow: 'hidden', backgroundColor: '#fff', borderRight: '1px solid #e2e8f0' }}>
            
            {/* Messages Scroll Container */}
            <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '24px' }}>
              {messages.length === 0 ? (
                <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '100px' }}>
                  <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔍</div>
                  <h3 style={{ margin: 0, color: '#334155', fontSize: '18px' }}>Ask Anything About Your Enterprise Datasets</h3>
                  <p style={{ fontSize: '13px', maxWidth: '460px', margin: '8px auto', color: '#64748b', lineHeight: '1.5' }}>
                    Ask questions across HR, Sales, Procurement, Annual Reports, SEC 10-Ks, NIST Policies, Internship Reports, and OCR Receipts.
                  </p>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div key={idx} style={{ marginBottom: '20px', display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                    <div style={{
                      maxWidth: '85%',
                      backgroundColor: msg.role === 'user' ? '#2563eb' : '#f1f5f9',
                      color: msg.role === 'user' ? '#fff' : '#0f172a',
                      padding: '14px 18px',
                      borderRadius: '12px',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                      cursor: msg.role === 'assistant' ? 'pointer' : 'default',
                      border: activeMessage === msg ? '2px solid #3b82f6' : '1px solid transparent'
                    }}
                    onClick={() => msg.role === 'assistant' && setActiveMessage(msg)}
                    >
                      <div style={{ fontWeight: '600', fontSize: '11px', marginBottom: '4px', opacity: 0.8, textTransform: 'uppercase' }}>
                        {msg.role === 'user' ? 'You' : 'Enterprise Knowledge Assistant'}
                      </div>
                      <div style={{ fontSize: '14px', lineHeight: '1.6', whitespace: 'pre-wrap' }}>
                        {msg.content}
                      </div>

                      {msg.role === 'assistant' && (
                        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #cbd5e1', fontSize: '11px', color: '#64748b', display: 'flex', justifyContent: 'space-between' }}>
                          <span>Method: {msg.retrieval_method || 'HYBRID'}</span>
                          <span>Latency: {msg.latency_seconds || 0}s</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div style={{ padding: '12px', color: '#64748b', fontStyle: 'italic', fontSize: '13px' }}>
                  Evaluating vector evidence & traversing Knowledge Graph...
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div style={{ flexShrink: 0, padding: '16px 24px', backgroundColor: '#fff', borderTop: '1px solid #e2e8f0' }}>
              <form onSubmit={handleSendQuery} style={{ display: 'flex', gap: '12px' }}>
                <input
                  type="text"
                  placeholder="Ask an enterprise question (e.g. enterprise_sales_dirty_100_rows.csv, highest sold item)..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '14px', outline: 'none' }}
                />
                <button
                  type="submit"
                  disabled={loading}
                  style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', padding: '12px 22px', borderRadius: '8px', fontWeight: '600', fontSize: '14px', cursor: 'pointer' }}
                >
                  Send
                </button>
              </form>
            </div>
          </div>

          {/* Right Panel: Grounded Explanation Console */}
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, overflow: 'hidden', backgroundColor: '#fff', padding: '20px' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#0f172a', flexShrink: 0 }}>
              Grounded Response Console {activeMessage?.query_text ? `— "${activeMessage.query_text.substring(0, 25)}..."` : ''}
            </h3>

            {/* Module Navigation Tabs */}
            <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', marginBottom: '14px', flexShrink: 0 }}>
              {[
                { id: 'answer', label: 'Answer' },
                { id: 'evidence', label: 'Evidence & Sources' },
                { id: 'graph', label: 'KG Path' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    flex: 1,
                    padding: '8px 2px',
                    border: 'none',
                    borderBottom: activeTab === tab.id ? '2px solid #2563eb' : 'none',
                    color: activeTab === tab.id ? '#2563eb' : '#64748b',
                    fontWeight: activeTab === tab.id ? '600' : '400',
                    fontSize: '12px',
                    cursor: 'pointer',
                    backgroundColor: 'transparent'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Contents Container */}
            <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
              {!activeMessage ? (
                <p style={{ color: '#94a3b8', fontSize: '13px', textAlign: 'center', marginTop: '100px' }}>
                  Select an assistant response to inspect grounded answer depth, evidence, and KG paths.
                </p>
              ) : (
                <>
                  {/* TAB 1: ANSWER DEPTH SELECTOR */}
                  {activeTab === 'answer' && (
                    <div>
                      <div style={{ display: 'flex', gap: '4px', marginBottom: '14px', backgroundColor: '#f1f5f9', padding: '4px', borderRadius: '8px' }}>
                        {[
                          { key: 'direct', label: 'Direct Answer' },
                          { key: 'detailed', label: 'Detailed' },
                          { key: 'indepth', label: 'In-depth' },
                          { key: 'comprehensive', label: 'Comprehensive' }
                        ].map(d => (
                          <button
                            key={d.key}
                            onClick={() => setAnswerDepth(d.key)}
                            style={{
                              flex: 1,
                              padding: '6px 2px',
                              borderRadius: '6px',
                              border: 'none',
                              fontSize: '11px',
                              fontWeight: '600',
                              cursor: 'pointer',
                              backgroundColor: answerDepth === d.key ? '#fff' : 'transparent',
                              color: answerDepth === d.key ? '#2563eb' : '#64748b',
                              boxShadow: answerDepth === d.key ? '0 1px 2px rgba(0,0,0,0.08)' : 'none'
                            }}
                          >
                            {d.label}
                          </button>
                        ))}
                      </div>

                      <div style={{ fontSize: '13px', color: '#334155', lineHeight: '1.6', whitespace: 'pre-wrap' }}>
                        {answerDepth === 'direct' && (
                          <p style={{ fontWeight: '500', color: '#0f172a', margin: 0 }}>
                            {activeMessage.response_levels?.level_1 || activeMessage.content}
                          </p>
                        )}
                        {answerDepth === 'detailed' && (
                          <p style={{ color: '#1e293b', margin: 0 }}>
                            {activeMessage.response_levels?.level_2 || activeMessage.content}
                          </p>
                        )}
                        {answerDepth === 'indepth' && (
                          <p style={{ color: '#1e293b', margin: 0 }}>
                            {activeMessage.response_levels?.level_3 || activeMessage.content}
                          </p>
                        )}
                        {answerDepth === 'comprehensive' && (
                          <p style={{ color: '#1e293b', margin: 0 }}>
                            {activeMessage.response_levels?.level_4 || activeMessage.content}
                          </p>
                        )}
                      </div>

                      <div style={{ marginTop: '20px', paddingTop: '12px', borderTop: '1px solid #e2e8f0', fontSize: '12px', color: '#64748b' }}>
                        <div>Intent Category: <strong>{activeMessage.intent_category}</strong></div>
                        <div>Retrieval Strategy: <strong>{activeMessage.retrieval_method}</strong></div>
                      </div>
                    </div>
                  )}

                  {/* TAB 2: EVIDENCE & SOURCES */}
                  {activeTab === 'evidence' && (
                    <div>
                      <h4 style={{ margin: '0 0 10px 0', color: '#1e293b', fontSize: '13px' }}>Claim-to-Evidence Traceability</h4>
                      {activeMessage.claims_mapping && activeMessage.claims_mapping.length > 0 && (
                        <div style={{ marginBottom: '14px' }}>
                          {activeMessage.claims_mapping.map((cMap, idx) => (
                            <div key={idx} style={{ backgroundColor: '#eff6ff', border: '1px solid #bfdbfe', padding: '10px', borderRadius: '8px', marginBottom: '8px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                <span style={{ fontSize: '10px', fontWeight: '700', color: '#1e40af', backgroundColor: '#dbeafe', padding: '2px 6px', borderRadius: '4px' }}>
                                  {cMap.claim_type || 'GROUNDED_CLAIM'}
                                </span>
                                <span style={{ fontSize: '10px', color: '#3b82f6', fontWeight: '600' }}>
                                  Confidence: {cMap.confidence || '95.0%'}
                                </span>
                              </div>
                              <div style={{ fontSize: '12px', fontWeight: '600', color: '#1e293b', marginBottom: '4px' }}>
                                Claim: {cMap.claim}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      <h5 style={{ margin: '10px 0 6px 0', color: '#475569', fontSize: '12px' }}>Retrieved Evidence Chunks</h5>
                      {(!activeMessage.evidence_chunks || activeMessage.evidence_chunks.length === 0) ? (
                        <p style={{ fontSize: '12px', color: '#94a3b8' }}>No direct evidence chunks available for this query.</p>
                      ) : (
                        activeMessage.evidence_chunks.map((chunk, i) => (
                          <div key={i} style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', padding: '10px', borderRadius: '8px', marginBottom: '10px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: '600', color: '#2563eb' }}>
                              <span>{chunk.evidence_id ? `[${chunk.evidence_id}] ${chunk.title || 'Evidence'}` : (chunk.title || 'Evidence')}</span>
                              <span style={{ backgroundColor: '#dbeafe', color: '#1e40af', padding: '2px 6px', borderRadius: '10px', fontSize: '10px' }}>
                                {chunk.source_type || 'DOCUMENT'} • {chunk.confidence || '100%'}
                              </span>
                            </div>
                            <p style={{ fontSize: '11px', color: '#334155', margin: '6px 0 0 0', backgroundColor: '#fff', padding: '8px', borderRadius: '6px', border: '1px dashed #cbd5e1', maxHeight: '160px', overflowY: 'auto' }}>
                              {chunk.text}
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* TAB 3: KG PATH */}
                  {activeTab === 'graph' && (
                    <div>
                      <h4 style={{ margin: '0 0 10px 0', color: '#1e293b', fontSize: '13px' }}>Universal Knowledge Graph Path</h4>
                      {(!activeMessage.kg_path || activeMessage.kg_path.length === 0) ? (
                        <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', padding: '12px', borderRadius: '8px', color: '#64748b', fontSize: '12px' }}>
                          No Knowledge Graph relationship was identified for this query.
                        </div>
                      ) : (
                        activeMessage.kg_path.map((path, i) => (
                          <div key={i} style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', padding: '12px', borderRadius: '8px', marginBottom: '10px' }}>
                            {path.source_entity && path.target_entity ? (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '6px' }}>
                                <span style={{ backgroundColor: '#dcfce7', color: '#166534', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: '600' }}>
                                  {path.source_entity}
                                </span>
                                <span style={{ backgroundColor: '#166534', color: '#fff', padding: '2px 4px', borderRadius: '4px', fontSize: '10px', fontWeight: '700' }}>
                                  --[{path.relationship || 'RELATED_TO'}]--&gt;
                                </span>
                                <span style={{ backgroundColor: '#dcfce7', color: '#166534', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: '600' }}>
                                  {path.target_entity}
                                </span>
                              </div>
                            ) : (
                              <div style={{ fontWeight: '700', fontSize: '12px', color: '#166534', marginBottom: '4px' }}>
                                {path.path_string || 'Entity Connection'}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* DELETE CONFIRMATION MODAL */}
      {deleteModalSession && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: '#fff', borderRadius: '12px', width: '420px', padding: '24px', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}>
            <h3 style={{ margin: '0 0 12px 0', color: '#0f172a', fontSize: '16px' }}>
              Delete Conversation?
            </h3>
            <p style={{ margin: '0 0 20px 0', color: '#64748b', fontSize: '13px', lineHeight: '1.5' }}>
              Are you sure you want to delete <strong>"{deleteModalSession.title}"</strong>?
              This will remove the chat message history from your workspace. Source documents, FAISS index, and Knowledge Graph entities will remain intact.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={() => setDeleteModalSession(null)}
                style={{ backgroundColor: '#f1f5f9', color: '#475569', border: 'none', padding: '8px 16px', borderRadius: '6px', fontWeight: '600', fontSize: '13px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteSessionConfirm}
                style={{ backgroundColor: '#ef4444', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', fontWeight: '600', fontSize: '13px', cursor: 'pointer' }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
