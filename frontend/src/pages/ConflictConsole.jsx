import React, { useState, useEffect } from 'react';
import client from '../api/client';

const ConflictConsole = () => {
  const [conflicts, setConflicts] = useState([]);
  const [stats, setStats] = useState({
    total_conflicts: 0,
    pending_reviews: 0,
    critical_conflicts: 0,
    resolved_conflicts: 0,
    average_similarity: 0.0,
    average_confidence: 0.0
  });
  
  const [loading, setLoading] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);
  const [actionProcessing, setActionProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  
  // Selection & Details Sidebar
  const [selectedConflict, setSelectedConflict] = useState(null);
  const [activeReview, setActiveReview] = useState(null);
  const [audits, setAudits] = useState([]);
  
  // Workflow form states
  const [comments, setComments] = useState('');
  const [decision, setDecision] = useState('CONFIRMED');
  const [customEditData, setCustomEditData] = useState('{\n  "notes": "Resolved discrepancy"\n}');
  
  // Search & Filter
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const res = await client.get('conflicts/statistics/');
      if (res.data && res.data.success) {
        setStats(res.data.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingStats(false);
    }
  };

  const fetchConflicts = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await client.get('conflicts/');
      if (res.data && res.data.success) {
        setConflicts(res.data.data);
      }
    } catch (err) {
      setErrorMsg('Failed to load conflict registry entries.');
    } finally {
      setLoading(false);
    }
  };

  const triggerDetection = async () => {
    setActionProcessing(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const res = await client.post('conflicts/');
      if (res.data && res.data.success) {
        setSuccessMsg(`Detection pipeline completed! Processed ${res.data.data.processed_candidates} pairs, generated ${res.data.data.generated_conflicts} conflicts.`);
        fetchConflicts();
        fetchStats();
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.errors?.[0] || 'Pipeline processing failed.');
    } finally {
      setActionProcessing(false);
    }
  };

  const selectConflict = async (conflict) => {
    setSelectedConflict(conflict);
    setActiveReview(null);
    setAudits([]);
    setComments('');
    setErrorMsg('');
    setSuccessMsg('');
    
    try {
      // Try to start/fetch review
      const res = await client.post(`conflicts/${conflict.conflict_id}/review/`, { action: "start" });
      if (res.data && res.data.success) {
        setActiveReview(res.data.data);
      }
    } catch (err) {
      console.error("Failed to start/fetch review context");
    }
  };

  const handleSubmitReview = async (statusType) => {
    if (!activeReview) return;
    setActionProcessing(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const res = await client.post(`conflicts/${selectedConflict.conflict_id}/review/`, {
        action: "submit",
        review_id: activeReview.review_id,
        decision: decision,
        status: statusType,
        comments: comments
      });
      
      if (res.data && res.data.success) {
        setSuccessMsg(`Review decision submitted: ${statusType}`);
        setActiveReview(res.data.data);
        // Refresh details
        const detailsRes = await client.get(`conflicts/${selectedConflict.conflict_id}/`);
        if (detailsRes.data && detailsRes.data.success) {
          setSelectedConflict(detailsRes.data.data);
        }
        fetchConflicts();
        fetchStats();
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.errors?.[0] || 'Submission failed.');
    } finally {
      setActionProcessing(false);
    }
  };

  const handleResolve = async (resolutionType) => {
    if (!activeReview) return;
    setActionProcessing(true);
    setErrorMsg('');
    setSuccessMsg('');
    
    let editPayload = null;
    if (resolutionType === 'MANUAL_EDIT') {
      try {
        editPayload = JSON.parse(customEditData);
      } catch (err) {
        setErrorMsg('Invalid custom edit JSON format.');
        setActionProcessing(false);
        return;
      }
    }
    
    try {
      const res = await client.post(`conflicts/${selectedConflict.conflict_id}/resolve/`, {
        review_id: activeReview.review_id,
        resolution: resolutionType,
        custom_edit_data: editPayload
      });
      
      if (res.data && res.data.success) {
        setSuccessMsg(`Conflict resolved successfully using: ${resolutionType}`);
        // Refresh details
        const detailsRes = await client.get(`conflicts/${selectedConflict.conflict_id}/`);
        if (detailsRes.data && detailsRes.data.success) {
          setSelectedConflict(detailsRes.data.data);
          setActiveReview(null);
        }
        fetchConflicts();
        fetchStats();
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.errors?.[0] || 'Resolution action failed.');
    } finally {
      setActionProcessing(false);
    }
  };

  useEffect(() => {
    fetchConflicts();
    fetchStats();
  }, []);

  // Filter logic
  const filteredConflicts = conflicts.filter(c => {
    const matchesSearch = 
      c.source_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.target_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.conflict_type?.toLowerCase().includes(searchTerm.toLowerCase());
      
    const matchesSeverity = severityFilter === 'ALL' || c.severity === severityFilter;
    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;
    
    return matchesSearch && matchesSeverity && matchesStatus;
  });

  const parseFields = (text) => {
    if (!text) return {};
    const fields = {};
    const parts = text.split('|');
    parts.forEach(part => {
      const idx = part.indexOf(':');
      if (idx !== -1) {
        const k = part.substring(0, idx).trim();
        const v = part.substring(idx + 1).trim();
        fields[k] = v;
      }
    });
    return fields;
  };

  const renderDiffTable = (sourceText, targetText) => {
    const srcFields = parseFields(sourceText);
    const tgtFields = parseFields(targetText);
    const allKeys = Array.from(new Set([...Object.keys(srcFields), ...Object.keys(tgtFields)]));
    
    // Mismatched fields
    const diffKeys = allKeys.filter(k => {
      const srcVal = srcFields[k] || '';
      const tgtVal = tgtFields[k] || '';
      return srcVal.toLowerCase() !== tgtVal.toLowerCase() && k.toLowerCase() !== 'entity type' && k.toLowerCase() !== 'record id';
    });

    if (diffKeys.length === 0) {
      return (
        <div className="alert alert-info py-2 px-3 small border-0 bg-light text-dark">
          No specific field differences found. Check original records.
        </div>
      );
    }

    return (
      <div className="table-responsive rounded border border-secondary mb-3 bg-white">
        <table className="table table-striped table-hover align-middle mb-0 text-dark small">
          <thead className="table-light">
            <tr>
              <th className="fw-bold">Field</th>
              <th className="text-danger fw-bold">Uploaded Record</th>
              <th className="text-success fw-bold">Current Record</th>
            </tr>
          </thead>
          <tbody>
            {diffKeys.map(k => (
              <tr key={k}>
                <td className="fw-bold text-dark font-monospace">{k}</td>
                <td className="text-danger font-monospace">{srcFields[k] || <span className="text-muted small">None</span>}</td>
                <td className="text-success font-monospace">{tgtFields[k] || <span className="text-muted small">None</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderFlagReason = (conflict) => {
    const srcFields = parseFields(conflict.source_text);
    const idKey = Object.keys(srcFields).find(k => k.toLowerCase().includes('id'));
    const idVal = idKey ? srcFields[idKey] : '';

    return (
      <div className="card border-warning bg-warning bg-opacity-10 mb-3 text-dark">
        <div className="card-body p-3">
          <h6 className="card-title fw-bold text-warning-emphasis mb-2">Why was this flagged?</h6>
          <p className="card-text small mb-0">
            {idVal ? (
              `The same identifier (${idVal}) was found in both records, but the details in the uploaded file conflict with the database.`
            ) : (
              "The system matched these records but found conflicting field values."
            )}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="container-fluid p-0 bg-light text-dark">
      <div className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom border-secondary">
        <div>
          <h3 className="fw-bold text-success mb-1">Check Data Conflicts</h3>
          <p className="text-secondary small mb-0">Review and resolve differences between newly uploaded files and database records.</p>
        </div>
        <button 
          className="btn btn-success py-2 px-4 fw-bold font-monospace"
          onClick={triggerDetection}
          disabled={actionProcessing}
        >
          {actionProcessing ? (
            <>
              <span className="spinner-border spinner-border-sm me-2"></span>
              Scanning...
            </>
          ) : 'Scan for Conflicts'}
        </button>
      </div>

      {errorMsg && <div className="alert alert-danger font-monospace py-2 px-3 small border-0 card bg-danger bg-opacity-10 text-danger mb-3">{errorMsg}</div>}
      {successMsg && <div className="alert alert-success font-monospace py-2 px-3 small border-0 card bg-success bg-opacity-10 text-success mb-3">{successMsg}</div>}

      {/* Analytics statistics cards grid */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-4 col-lg-2">
          <div className="card border-0 shadow-sm p-3 text-center text-md-start h-100 bg-white">
            <span className="text-secondary small font-monospace">Total Issues</span>
            <h3 className="fw-bold text-dark mb-0 mt-1">{stats.total_conflicts}</h3>
          </div>
        </div>
        <div className="col-6 col-md-4 col-lg-2">
          <div className="card border-0 shadow-sm p-3 text-center text-md-start h-100 bg-white" style={{ borderLeft: '3px solid #ffc107' }}>
            <span className="text-warning small font-monospace">Needs Review</span>
            <h3 className="fw-bold text-dark mb-0 mt-1">{stats.pending_reviews}</h3>
          </div>
        </div>
        <div className="col-6 col-md-4 col-lg-2">
          <div className="card border-0 shadow-sm p-3 text-center text-md-start h-100 bg-white" style={{ borderLeft: '3px solid #dc3545' }}>
            <span className="text-danger small font-monospace">Critical Issues</span>
            <h3 className="fw-bold text-dark mb-0 mt-1">{stats.critical_conflicts}</h3>
          </div>
        </div>
        <div className="col-6 col-md-4 col-lg-2">
          <div className="card border-0 shadow-sm p-3 text-center text-md-start h-100 bg-white" style={{ borderLeft: '3px solid #198754' }}>
            <span className="text-success small font-monospace">Resolved</span>
            <h3 className="fw-bold text-dark mb-0 mt-1">{stats.resolved_conflicts}</h3>
          </div>
        </div>
        <div className="col-6 col-md-4 col-lg-2">
          <div className="card border-0 shadow-sm p-3 text-center text-md-start h-100 bg-white">
            <span className="text-secondary small font-monospace">Match Similarity</span>
            <h3 className="fw-bold text-dark mb-0 mt-1">{(stats.average_similarity * 100).toFixed(1)}%</h3>
          </div>
        </div>
        <div className="col-6 col-md-4 col-lg-2">
          <div className="card border-0 shadow-sm p-3 text-center text-md-start h-100 bg-white">
            <span className="text-secondary small font-monospace">Confidence Scale</span>
            <h3 className="fw-bold text-dark mb-0 mt-1">{(stats.average_confidence * 100).toFixed(1)}%</h3>
          </div>
        </div>
      </div>

      <div className="row g-4">
        {/* Registry Table List Column */}
        <div className="col-12 col-lg-7">
          <div className="card border-0 shadow-sm p-4 bg-white text-dark">
            <h5 className="fw-bold text-dark mb-3">Detected Conflicts</h5>

            {/* Filters */}
            <div className="row g-2 mb-3">
              <div className="col-12 col-md-5">
                <input 
                  type="text" 
                  className="form-control bg-white border-secondary text-dark" 
                  placeholder="Search by title, type..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <div className="col-6 col-md-3">
                <select 
                  className="form-select bg-white border-secondary text-dark"
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                >
                  <option value="ALL">All Severities</option>
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="CRITICAL">Critical</option>
                </select>
              </div>
              <div className="col-6 col-md-4">
                <select 
                  className="form-select bg-white border-secondary text-dark"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="ALL">All Statuses</option>
                  <option value="NEW">New</option>
                  <option value="PROCESSING">Processing</option>
                  <option value="REVIEW_PENDING">Review Pending</option>
                  <option value="VERIFIED">Verified</option>
                  <option value="REJECTED">Rejected</option>
                  <option value="ARCHIVED">Archived</option>
                </select>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-5 text-secondary">
                <span className="spinner-border spinner-border-sm me-2"></span>
                Loading conflicts...
              </div>
            ) : filteredConflicts.length > 0 ? (
              <div className="table-responsive">
                <table className="table table-striped table-hover align-middle mb-0 text-dark">
                  <thead className="table-light text-secondary font-monospace" style={{ fontSize: '0.8rem' }}>
                    <tr>
                      <th>Type</th>
                      <th>Records Compare</th>
                      <th>Severity</th>
                      <th>Similarity</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredConflicts.map((c) => (
                      <tr 
                        key={c.id} 
                        onClick={() => selectConflict(c)}
                        style={{ cursor: 'pointer' }}
                        className={selectedConflict?.id === c.id ? 'table-active' : ''}
                      >
                        <td className="font-monospace text-success fw-bold small">{c.conflict_type}</td>
                        <td className="small text-truncate" style={{ maxWidth: '220px' }}>
                          <div className="fw-semibold text-dark">{c.source_title}</div>
                          <div className="text-muted" style={{ fontSize: '0.75rem' }}>vs {c.target_title}</div>
                        </td>
                        <td>
                          <span className={`badge ${
                            c.severity === 'CRITICAL' ? 'bg-danger font-monospace' :
                            c.severity === 'HIGH' ? 'bg-warning text-dark font-monospace' :
                            c.severity === 'MEDIUM' ? 'bg-info text-dark font-monospace' : 'bg-secondary font-monospace'
                          }`} style={{ fontSize: '0.65rem' }}>
                            {c.severity}
                          </span>
                        </td>
                        <td className="font-monospace fw-bold text-dark">{(c.overall_similarity * 100).toFixed(0)}%</td>
                        <td>
                          <span className="badge bg-light border border-secondary text-secondary" style={{ fontSize: '0.65rem' }}>
                            {c.status === 'REVIEW_PENDING' ? 'Needs Review' : c.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-5 text-muted small">
                No conflicts matched active filter parameters.
              </div>
            )}
          </div>
        </div>

        {/* Human review workflow control Panel Column */}
        <div className="col-12 col-lg-5">
          <div className="card border-0 shadow-sm p-4 bg-white text-dark h-100 d-flex flex-column justify-content-between" style={{ maxHeight: 'calc(100vh - 120px)', overflowY: 'auto' }}>
            {selectedConflict ? (
              <div>
                <div className="d-flex justify-content-between align-items-start pb-3 border-bottom border-secondary mb-3">
                  <div>
                    <h5 className="fw-bold text-dark mb-1">How should we fix it?</h5>
                    <span className="text-muted font-monospace small" style={{ fontSize: '0.7rem' }}>
                      ID: {selectedConflict.conflict_id.substring(0, 8)}
                    </span>
                  </div>
                  <span className="badge bg-success px-3 py-1 font-monospace" style={{ fontSize: '0.7rem' }}>
                    SIMILARITY: {(selectedConflict.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>

                {/* Review Timeline Milestone progress */}
                <div className="mb-4 bg-light rounded p-3 border border-secondary">
                  <h6 className="text-secondary small font-monospace mb-3">Review Progress Status</h6>
                  <div className="d-flex justify-content-between align-items-center position-relative">
                    {/* Progress line */}
                    <div className="position-absolute w-100 bg-secondary" style={{ height: '2px', top: '10px', left: 0, zIndex: 1 }}></div>
                    <div className="position-absolute bg-success" style={{ 
                      height: '2px', 
                      top: '10px', 
                      left: 0, 
                      zIndex: 2, 
                      width: selectedConflict.status === 'VERIFIED' ? '100%' : 
                             selectedConflict.status === 'REVIEW_PENDING' ? '75%' : 
                             selectedConflict.status === 'PROCESSING' ? '50%' : '25%'
                    }}></div>

                    {['NEW', 'PROCESSING', 'REVIEW_PENDING', 'VERIFIED'].map((step, idx) => (
                      <div key={step} className="d-flex flex-column align-items-center position-relative" style={{ zIndex: 10 }}>
                        <div className={`rounded-circle d-flex align-items-center justify-content-center ${
                          selectedConflict.status === step ? 'bg-success text-white fw-bold' : 'bg-light text-secondary border border-secondary'
                        }`} style={{ width: '22px', height: '22px', fontSize: '0.7rem' }}>
                          {idx + 1}
                        </div>
                        <span className="text-secondary font-monospace mt-1" style={{ fontSize: '0.6rem' }}>
                          {step === 'REVIEW_PENDING' ? 'Needs Review' : step}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Why Flagged Explanation */}
                {renderFlagReason(selectedConflict)}

                {/* Data Integrity check */}
                {(() => {
                  const srcEmpId = selectedConflict.source_record?.employee_id;
                  const tgtEmpId = selectedConflict.target_record?.employee_id;
                  if (srcEmpId && tgtEmpId && srcEmpId !== tgtEmpId) {
                    console.error(`Data Inconsistency Detected: Mismatched Employee IDs! Source: ${srcEmpId} vs Target: ${tgtEmpId}`);
                    return (
                      <div className="alert alert-danger font-monospace border-0 bg-danger bg-opacity-10 text-danger mb-3 p-3 small">
                        <strong className="d-block mb-1">⚠️ DATA INCONSISTENCY DETECTED</strong>
                        Mismatched Employee IDs paired! [Source: {srcEmpId} vs Target: {tgtEmpId}]. Please contact your system administrator.
                      </div>
                    );
                  }
                  return null;
                })()}

                {/* Employee Summary Card */}
                {selectedConflict.source_record && (
                  <div className="card bg-success bg-opacity-10 border-success border-0 mb-3 p-3 text-dark">
                    <span className="text-success fw-bold font-monospace small text-uppercase">Employee Details</span>
                    <h5 className="fw-bold text-dark mb-0 mt-1">{selectedConflict.source_record.name || 'N/A'}</h5>
                    <span className="text-secondary small font-monospace mt-1 d-block">
                      <strong>ID:</strong> {selectedConflict.source_record.employee_id || 'N/A'} | 
                      <strong> Role:</strong> {selectedConflict.source_record.role || 'N/A'} | 
                      <strong> Department:</strong> {selectedConflict.source_record.department || 'N/A'}
                    </span>
                  </div>
                )}

                {/* Source and Target Records Stacked Display */}
                {selectedConflict.source_record && selectedConflict.target_record && (
                  <div className="row g-2 mb-3">
                    <div className="col-12 col-md-6">
                      <div className="card bg-light border-secondary h-100">
                        <div className="card-header bg-secondary text-white py-1 px-3 fw-bold small font-monospace">Uploaded Record</div>
                        <div className="card-body p-2" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                          <table className="table table-sm table-borderless mb-0 small font-monospace text-dark" style={{ fontSize: '0.75rem' }}>
                            <tbody>
                              {Object.entries(selectedConflict.source_record).map(([k, v]) => (
                                v !== null && v !== undefined && k !== 'notes' && (
                                  <tr key={k}>
                                    <td className="text-secondary fw-semibold py-0" style={{ width: '45%' }}>{k.replace('_', ' ').toUpperCase()}</td>
                                    <td className="text-dark fw-bold py-0">{String(v)}</td>
                                  </tr>
                                )
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                    <div className="col-12 col-md-6">
                      <div className="card bg-light border-secondary h-100">
                        <div className="card-header bg-secondary text-white py-1 px-3 fw-bold small font-monospace">Current Record</div>
                        <div className="card-body p-2" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                          <table className="table table-sm table-borderless mb-0 small font-monospace text-dark" style={{ fontSize: '0.75rem' }}>
                            <tbody>
                              {Object.entries(selectedConflict.target_record).map(([k, v]) => (
                                v !== null && v !== undefined && k !== 'notes' && (
                                  <tr key={k}>
                                    <td className="text-secondary fw-semibold py-0" style={{ width: '45%' }}>{k.replace('_', ' ').toUpperCase()}</td>
                                    <td className="text-dark fw-bold py-0">{String(v)}</td>
                                  </tr>
                                )
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Changed Fields Table */}
                <h6 className="text-secondary fw-bold mb-2 small font-monospace text-uppercase">Changed Fields</h6>
                {(() => {
                  const src = selectedConflict.source_record || {};
                  const tgt = selectedConflict.target_record || {};
                  const diffs = [];
                  
                  const keys = Array.from(new Set([...Object.keys(src), ...Object.keys(tgt)]));
                  keys.forEach(k => {
                    if (k === 'notes') return;
                    const srcVal = src[k] !== null && src[k] !== undefined ? String(src[k]).trim() : '';
                    const tgtVal = tgt[k] !== null && tgt[k] !== undefined ? String(tgt[k]).trim() : '';
                    if (srcVal.toLowerCase() !== tgtVal.toLowerCase()) {
                      diffs.push({
                        field: k.replace(/_/g, ' ').toUpperCase(),
                        src: src[k],
                        tgt: tgt[k]
                      });
                    }
                  });

                  if (diffs.length === 0 && selectedConflict.source_text && selectedConflict.target_text) {
                    const parseKv = (txt) => {
                      const kv = {};
                      (txt || '').split('|').forEach(part => {
                        if (part.includes(':')) {
                          const [k, v] = part.split(':', 2);
                          kv[k.trim()] = v.trim();
                        }
                      });
                      return kv;
                    };
                    const kv1 = parseKv(selectedConflict.source_text);
                    const kv2 = parseKv(selectedConflict.target_text);
                    const kvKeys = Array.from(new Set([...Object.keys(kv1), ...Object.keys(kv2)]));
                    kvKeys.forEach(k => {
                      if (k.toLowerCase() === 'entity type') return;
                      const v1 = kv1[k] || '';
                      const v2 = kv2[k] || '';
                      if (v1.toLowerCase() !== v2.toLowerCase()) {
                        diffs.push({
                          field: k.toUpperCase(),
                          src: kv1[k] || 'N/A',
                          tgt: kv2[k] || 'N/A'
                        });
                      }
                    });
                  }

                  if (diffs.length > 0) {
                    return (
                      <div className="table-responsive rounded border border-secondary mb-3 bg-white">
                        <table className="table table-striped table-hover align-middle mb-0 text-dark small">
                          <thead className="table-light">
                            <tr>
                              <th className="fw-bold">Field</th>
                              <th className="text-danger fw-bold">Uploaded Record</th>
                              <th className="text-success fw-bold">Current Record</th>
                            </tr>
                          </thead>
                          <tbody>
                            {diffs.map((d, idx) => (
                              <tr key={idx}>
                                <td className="fw-bold text-dark font-monospace">{d.field}</td>
                                <td className="text-danger font-monospace fw-bold">{d.src !== null && d.src !== undefined ? String(d.src) : <span className="text-muted small">None</span>}</td>
                                <td className="text-success font-monospace fw-bold">{d.tgt !== null && d.tgt !== undefined ? String(d.tgt) : <span className="text-muted small">None</span>}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    );
                  } else {
                    return (
                      <div className="alert alert-info py-2 px-3 small border-0 bg-light text-dark font-monospace mb-3">
                        {selectedConflict.explanation || "No property differences identified between these compared entries."}
                      </div>
                    );
                  }
                })()}

                {/* Extra metrics hidden in collapsed Technical Details Accordion */}
                <div className="accordion accordion-flush bg-white border border-secondary rounded mb-4" id="detailsAccordion">
                  <div className="accordion-item bg-white border-secondary">
                    <h2 className="accordion-header">
                      <button className="accordion-button bg-light text-success fw-bold small font-monospace py-2 collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne">
                        Technical Details
                      </button>
                    </h2>
                    <div id="collapseOne" className="accordion-collapse collapse" data-bs-parent="#detailsAccordion">
                      <div className="accordion-body font-monospace p-3 text-dark bg-white">
                        <div className="small mb-2"><strong>Model Used:</strong> SBERT MiniLM</div>
                        <div className="small mb-2"><strong>Match Similarity:</strong> {(selectedConflict.overall_similarity * 100).toFixed(2)}%</div>
                        <div className="small mb-2"><strong>Severity Level:</strong> {selectedConflict.severity}</div>
                        <div className="small mb-3"><strong>Conflict Classification:</strong> {selectedConflict.conflict_type}</div>
                        <hr className="my-2 border-secondary" />
                        <span className="text-secondary small d-block mb-1">Raw Trace JSON:</span>
                        <pre className="text-dark mb-0 small overflow-auto p-2 bg-light rounded" style={{ maxHeight: '150px', fontSize: '0.7rem' }}>
                          {JSON.stringify(selectedConflict.processing_trace, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Workflow Controls Panel Form */}
                {activeReview ? (
                  <div className="border-top border-secondary pt-3">
                    <h6 className="text-dark fw-bold mb-3 font-monospace">Review Verdict</h6>
                    
                    <div className="mb-3">
                      <label className="form-label text-secondary small font-monospace">Decision Classification</label>
                      <select 
                        className="form-select bg-white border-secondary text-success font-monospace"
                        value={decision}
                        onChange={(e) => setDecision(e.target.value)}
                      >
                        <option value="CONFIRMED">Confirmed Conflict</option>
                        <option value="FALSE_POSITIVE">False Positive</option>
                        <option value="NEEDS_MORE_REVIEW">Needs More Review</option>
                      </select>
                    </div>

                    <div className="mb-3">
                      <label className="form-label text-secondary small font-monospace">Comments & Explanations</label>
                      <textarea 
                        className="form-control bg-white border-secondary text-dark small" 
                        rows="2"
                        placeholder="Explain rationale for validation decision..."
                        value={comments}
                        onChange={(e) => setComments(e.target.value)}
                      />
                    </div>

                    {/* Action buttons */}
                    <div className="d-flex gap-2 mb-3">
                      <button 
                        className="btn btn-sm btn-success flex-grow-1 fw-bold" 
                        onClick={() => handleSubmitReview('APPROVED')}
                        disabled={actionProcessing}
                      >Approve Review</button>
                      <button 
                        className="btn btn-sm btn-danger flex-grow-1 fw-bold" 
                        onClick={() => handleSubmitReview('REJECTED')}
                        disabled={actionProcessing}
                      >Reject Candidate</button>
                    </div>

                    {/* Resolution Section (Enabled only after approval or in decision mode) */}
                    {activeReview.review_status === 'APPROVED' && (
                      <div className="border-top border-secondary pt-3 mt-3">
                        <h6 className="text-dark fw-bold mb-3 font-monospace">Choose Resolution Option</h6>
                        
                        <div className="row g-2 mb-3">
                          <div className="col-6">
                            <button className="btn btn-sm btn-outline-success w-100 fw-bold" onClick={() => handleResolve('KEEP_SOURCE')}>Keep Uploaded</button>
                          </div>
                          <div className="col-6">
                            <button className="btn btn-sm btn-outline-success w-100 fw-bold" onClick={() => handleResolve('KEEP_TARGET')}>Keep Existing</button>
                          </div>
                          <div className="col-6">
                            <button className="btn btn-sm btn-outline-warning w-100 fw-bold text-dark" onClick={() => handleResolve('MERGE')}>Merge Data</button>
                          </div>
                          <div className="col-6">
                            <button className="btn btn-sm btn-outline-danger w-100 fw-bold" onClick={() => handleResolve('IGNORE')}>Ignore / Dismiss</button>
                          </div>
                        </div>

                        <div className="mb-3">
                          <label className="form-label text-secondary small font-monospace">Manual Edit Record Fields (JSON)</label>
                          <textarea 
                            className="form-control bg-white border-secondary text-success font-monospace small" 
                            rows="4"
                            value={customEditData}
                            onChange={(e) => setCustomEditData(e.target.value)}
                          />
                          <button 
                            className="btn btn-sm btn-success w-100 mt-2 py-2 fw-bold font-monospace" 
                            onClick={() => handleResolve('MANUAL_EDIT')}
                          >
                            Execute Manual Resolve
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-4 text-secondary small">
                    Initializing workflow action panel...
                  </div>
                )}
              </div>
            ) : (
              <div className="d-flex flex-column justify-content-center align-items-center flex-grow-1 text-center text-muted py-5">
                <svg width="68" height="68" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mb-3 text-success opacity-50">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <p className="fw-bold text-dark fs-5 mb-1">Awaiting Conflict Selection</p>
                <p className="small text-secondary px-4">Select a conflict pair from the table on the left to verify details, compare values, and select resolution actions.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConflictConsole;
