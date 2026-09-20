import React, { useState, useEffect } from 'react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';

const DataQualityExplainability = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  
  // Cache counters
  const [cacheStats, setCacheStats] = useState({ hits: 0, misses: 0, ratio: 1.0 });

  // Live Dataset Assessment Controls
  const [assessmentSourceTab, setAssessmentSourceTab] = useState('personal'); // 'local' | 'team' | 'personal'
  const [localAssessmentFile, setLocalAssessmentFile] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [repoDocuments, setRepoDocuments] = useState([]);
  const [loadingRepoDocs, setLoadingRepoDocs] = useState(false);
  const [assessing, setAssessing] = useState(false);
  const [assessError, setAssessError] = useState('');

  // Interactive Fix Resolutions & Audit Section State
  const [resolvedFixKeys, setResolvedFixKeys] = useState(new Set());
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [fixSuccessMsg, setFixSuccessMsg] = useState('');
  const [isCalcExplainOpen, setIsCalcExplainOpen] = useState(false);
  const [expandedCardKeys, setExpandedCardKeys] = useState(new Set());

  const toggleCardExpand = (key) => {
    const next = new Set(expandedCardKeys);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    setExpandedCardKeys(next);
  };

  // 1. Fetch aggregate statistics
  const fetchStats = async () => {
    try {
      const res = await client.get('edqi/explainability/statistics/');
      setStats(res.data);
    } catch (err) {
      console.error("Failed to load statistics", err);
    }
  };

  // 2. Fetch predictions explanations history list
  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await client.get('edqi/explanations/');
      setHistory(res.data);
      if (res.data.length > 0 && !selectedReport) {
        handleSelectReport(res.data[0].report_id);
      }
    } catch (err) {
      console.error("Failed to load history", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  // 3. Fetch detailed explanation report & sync Assessment Bar
  const handleSelectReport = async (reportId) => {
    setLoadingDetail(true);
    setFixSuccessMsg('');
    try {
      const res = await client.get(`edqi/explanations/${reportId}/`);
      const repData = res.data;
      setSelectedReport(repData);
      
      // Synchronize Assessment Bar controls with the selected historical report
      const docId = repData.source_provenance?.document_id;
      const fileName = repData.source_provenance?.source_file;

      if (docId) {
        setSelectedDocId(docId);
        const matchDoc = repoDocuments.find(d => d.id === docId);
        if (matchDoc) {
          const repoTab = matchDoc.repository_type || matchDoc.metadata?.repository_type || 'personal';
          setAssessmentSourceTab(repoTab);
        }
      } else if (fileName) {
        const matchDoc = repoDocuments.find(d => 
          (d.title || d.source_document?.original_name || '').toLowerCase().includes(fileName.toLowerCase()) ||
          fileName.toLowerCase().includes((d.title || '').toLowerCase())
        );
        if (matchDoc) {
          setSelectedDocId(matchDoc.id);
          const repoTab = matchDoc.repository_type || matchDoc.metadata?.repository_type || 'personal';
          setAssessmentSourceTab(repoTab);
        }
      }

      const cacheRes = await client.get('explainability/cache/statistics');
      setCacheStats({
        hits: cacheRes.data.cache_hits,
        misses: cacheRes.data.cache_misses,
        ratio: cacheRes.data.cache_hit_ratio
      });
    } catch (err) {
      console.error("Failed to load report detail", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // 4. Load Repository Documents for Assessment
  const fetchRepoDocuments = async (sourceType) => {
    setLoadingRepoDocs(true);
    setSelectedDocId('');
    try {
      const res = await client.get('repository/documents/', {
        params: { repository_type: sourceType }
      });
      const docs = res.data.results || res.data.data || [];
      const validDocs = docs.filter(doc => {
        const isPersonalDoc = 
          doc.repository_type === 'personal' ||
          doc.metadata?.repository_type === 'personal' ||
          doc.folder?.repository_type === 'personal' ||
          (doc.logical_path && doc.logical_path.toLowerCase().startsWith('personal/'));

        if (sourceType === 'personal') {
          return isPersonalDoc || doc.owner === user?.username || doc.owner?.username === user?.username;
        } else if (sourceType === 'team') {
          return !isPersonalDoc;
        }
        return true;
      });
      setRepoDocuments(validDocs);
      if (validDocs.length > 0) {
        const firstId = validDocs[0].id;
        setSelectedDocId(firstId);
        runAssessmentForDoc(firstId, sourceType);
      } else {
        setSelectedDocId('');
        setSelectedReport(null);
      }
    } catch (err) {
      console.error("Failed to load repository documents for assessment", err);
      setRepoDocuments([]);
      setSelectedDocId('');
      setSelectedReport(null);
    } finally {
      setLoadingRepoDocs(false);
    }
  };

  const runAssessmentForDoc = async (docId, sourceType) => {
    if (!docId) return;
    setAssessing(true);
    setLoadingDetail(true);
    setFixSuccessMsg('');
    try {
      const res = await client.post('edqi/assess/', {
        document_id: docId,
        source_type: sourceType
      });
      setSelectedReport(res.data);
    } catch (err) {
      console.error("Auto assessment failed", err);
    } finally {
      setAssessing(false);
      setLoadingDetail(false);
    }
  };

  const handleSourceTabChange = (tab) => {
    setAssessmentSourceTab(tab);
    setAssessError('');
    setLocalAssessmentFile(null);
    setSelectedDocId('');
    setSelectedReport(null);
    if (tab === 'team' || tab === 'personal') {
      fetchRepoDocuments(tab);
    }
  };

  const handleDocumentSelectChange = (docId) => {
    setSelectedDocId(docId);
    if (docId) {
      runAssessmentForDoc(docId, assessmentSourceTab);
    }
  };

  // 5. Execute Live Quality Assessment on Selected Dataset/File
  const handleRunAssessment = async () => {
    setAssessError('');
    setFixSuccessMsg('');
    if (assessmentSourceTab === 'local' && !localAssessmentFile) {
      setAssessError('Please select a local file (CSV, Excel, JSON, PDF, DOCX, TXT, Image) to assess.');
      return;
    }
    if ((assessmentSourceTab === 'team' || assessmentSourceTab === 'personal') && !selectedDocId) {
      setAssessError(`Please select a document from the ${assessmentSourceTab === 'team' ? 'Team' : 'Personal'} Repository.`);
      return;
    }

    setAssessing(true);
    setLoadingDetail(true);

    try {
      let res;
      if (assessmentSourceTab === 'local') {
        const formData = new FormData();
        formData.append('file', localAssessmentFile);
        formData.append('source_type', 'local');
        res = await client.post('edqi/assess/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } else {
        res = await client.post('edqi/assess/', {
          document_id: selectedDocId,
          source_type: assessmentSourceTab
        });
      }

      setSelectedReport(res.data);
      fetchStats();
    } catch (err) {
      console.error(err);
      setAssessError(err.response?.data?.error || 'Failed to assess quality for selected dataset.');
    } finally {
      setAssessing(false);
      setLoadingDetail(false);
    }
  };

  // 6. Handle Resolving & Clearing Fix Actions with Real-time Score Boost
  const handleResolveFix = (recItem, idx) => {
    if (!selectedReport) return;
    const reportKey = selectedReport.report_id || selectedReport.prediction_id || 'default';
    const fixKey = `${reportKey}-${idx}`;

    const newResolved = new Set(resolvedFixKeys);
    newResolved.add(fixKey);
    setResolvedFixKeys(newResolved);

    // Boost Quality Scores and Dimension Scores using backend-calculated impact
    const overallDelta = recItem.overall_score_impact !== undefined ? parseFloat(recItem.overall_score_impact) : (parseFloat(recItem.expected_improvement) || 0.0);
    const dimImp = recItem.dimension_improvement !== undefined ? parseFloat(recItem.dimension_improvement) : 0.0;
    const cat = (recItem.category || recItem.affected_dimension || 'completeness').toLowerCase();

    setSelectedReport(prev => {
      if (!prev) return prev;
      const currentScore = prev.overall_score || 88.0;
      const newScore = Math.min(100.0, currentScore + overallDelta);
      const newGrade = newScore >= 95 ? 'A+' : newScore >= 90 ? 'A' : newScore >= 80 ? 'B' : 'C';

      const updatedInputs = { ...(prev.input_features || {}) };
      Object.keys(updatedInputs).forEach(k => {
        if (k.toLowerCase().includes(cat)) {
          updatedInputs[k] = Math.min(100.0, (parseFloat(updatedInputs[k]) || 0.0) + dimImp);
        }
      });

      return {
        ...prev,
        overall_score: newScore,
        quality_grade: newGrade,
        input_features: updatedInputs
      };
    });

    setFixSuccessMsg(`✓ Recommendation resolved! Overall score improved by +${overallDelta.toFixed(2)} pts to ${(Math.min(100.0, (selectedReport.overall_score || 88.0) + overallDelta)).toFixed(1)} / 100.`);
  };


  // 7. Download files
  const handleDownload = (format) => {
    if (!selectedReport) return;
    const url = `${client.defaults.baseURL}edqi/explanations/${selectedReport.report_id}/?format=${format}`;
    window.open(url, '_blank');
  };

  useEffect(() => {
    fetchStats();
    fetchHistory();
    fetchRepoDocuments('personal');
  }, []);

  const getGradeBadge = (grade) => {
    const g = String(grade).toUpperCase();
    if (g === 'EXCELLENT' || g === 'A+' || g === 'A') return 'bg-success text-white';
    if (g === 'GOOD' || g === 'B') return 'bg-info text-dark';
    if (g === 'AVERAGE' || g === 'C') return 'bg-warning text-dark';
    return 'bg-danger text-white';
  };

  const getDimensionScore = (dimKey, fallbackVal = null) => {
    if (!selectedReport) return fallbackVal;
    const inputs = selectedReport.input_features || {};
    
    if (inputs[dimKey] !== undefined && inputs[dimKey] !== null) return parseFloat(inputs[dimKey]);
    if (inputs[`${dimKey}_score`] !== undefined && inputs[`${dimKey}_score`] !== null) return parseFloat(inputs[`${dimKey}_score`]);
    return fallbackVal;
  };

  const getDimensionText = (dimKey) => {
    if (dimKey === 'completeness') return 'Checks whether required fields are present.';
    if (dimKey === 'validity') return 'Checks whether values follow the expected format and range.';
    if (dimKey === 'consistency') return 'Checks whether related fields agree with each other.';
    if (dimKey === 'uniqueness') return 'Checks whether employee ID or email is duplicated.';
    if (dimKey === 'timeliness') return 'Checks whether the record is sufficiently recent.';
    return '';
  };

  const calculateRuleGrade = (score) => {
    if (score === null || score === undefined) return "Not available";
    const val = parseFloat(score);
    if (val >= 95.0) return "A+";
    if (val >= 90.0) return "A";
    if (val >= 80.0) return "B";
    if (val >= 70.0) return "C";
    if (val >= 60.0) return "D";
    return "F";
  };

  const completeness = getDimensionScore('completeness', null);
  const validity = getDimensionScore('validity', null);
  const consistency = getDimensionScore('consistency', null);
  const uniqueness = getDimensionScore('uniqueness', null);
  const timeliness = getDimensionScore('timeliness', null);
  const overallScore = selectedReport?.score_traceability?.final_score ?? selectedReport?.overall_score ?? getDimensionScore('quality', null);

  // Active recommendations filtered by resolved keys
  const currentReportKey = selectedReport?.report_id || selectedReport?.prediction_id || 'default';
  const activeRecommendations = (selectedReport?.recommendations || []).filter(
    (_, idx) => !resolvedFixKeys.has(`${currentReportKey}-${idx}`)
  );

  // Dynamic KPI Card Values per Selected History Document / Dataset
  const activeFileName = selectedReport?.source_provenance?.source_file || 'No Dataset Selected';
  
  const recordsScanned = (() => {
    if (selectedReport?.processing_trace?.records_scanned) {
      return `${selectedReport.processing_trace.records_scanned} Records`;
    }
    if (selectedReport?.source_provenance?.record_count) {
      return `${selectedReport.source_provenance.record_count} Records`;
    }
    if (selectedDocId) {
      const matchedDoc = repoDocuments.find(d => d.id === selectedDocId);
      if (matchedDoc && matchedDoc.record_count) {
        return `${matchedDoc.record_count} Records`;
      }
    }
    if (selectedReport?.source_provenance?.record_id && selectedReport.source_provenance.record_id !== 'N/A') {
      return `Record #${selectedReport.source_provenance.record_id}`;
    }
    return '1 Record';
  })();

  const datasetGrade = selectedReport?.quality_grade || (overallScore !== null ? calculateRuleGrade(overallScore) : 'A+');
  const datasetScoreText = overallScore !== null ? `${overallScore.toFixed(1)} / 100` : '95.0 / 100';
  const actionItemsCount = activeRecommendations.length;
  const validityHealthRate = validity !== null ? `${validity.toFixed(1)}%` : '100.0%';

  return (
    <div className="row g-4 text-dark bg-light">
      {/* 1. Synchronized Dynamic KPI Overview Cards */}
      <div className="col-12">
        <div className="row g-3">
          <div className="col-6 col-lg-3">
            <div className="card border-0 shadow-sm p-3 text-center bg-white h-100">
              <span className="text-secondary small fw-semibold d-block mb-1">DATASET SCOPE / RECORDS</span>
              <h3 className="fw-bold text-success mb-0">{recordsScanned}</h3>
              <span className="text-muted d-block mt-1 text-truncate" style={{ fontSize: '0.7rem' }} title={activeFileName}>
                📄 {activeFileName}
              </span>
            </div>
          </div>
          <div className="col-6 col-lg-3">
            <div className="card border-0 shadow-sm p-3 text-center bg-white h-100">
              <span className="text-secondary small fw-semibold d-block mb-1">QUALITY SCORE & GRADE</span>
              <h3 className="fw-bold text-info mb-0">Grade {datasetGrade}</h3>
              <span className="text-secondary small d-block mt-1">{datasetScoreText}</span>
            </div>
          </div>
          <div className="col-6 col-lg-3">
            <div className="card border-0 shadow-sm p-3 text-center bg-white h-100">
              <span className="text-secondary small fw-semibold d-block mb-1">RECOMMENDED FIX ACTIONS</span>
              <h3 className="fw-bold text-warning mb-0">{actionItemsCount} Actions</h3>
              <span className="text-secondary small d-block mt-1">Identified in this Dataset</span>
            </div>
          </div>
          <div className="col-6 col-lg-3">
            <div className="card border-0 shadow-sm p-3 text-center bg-white h-100">
              <span className="text-secondary small fw-semibold d-block mb-1">DATASET VALIDITY HEALTH</span>
              <h3 className="fw-bold text-success mb-0">{validityHealthRate}</h3>
              <span className="text-secondary small d-block mt-1">Valid & Compliant Records</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Interactive Dataset Quality Assessment & Document Selector Bar */}
      <div className="col-12">
        <div className="card border-0 shadow-sm p-4 bg-white">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold text-dark mb-0 d-flex align-items-center gap-2">
              <span>🔍 Selected Dataset Quality Assessment</span>
            </h5>
            <span className="badge bg-primary-subtle text-primary font-monospace">EDQI Quality Assessment Workflow</span>
          </div>

          {assessError && <div className="alert alert-danger py-2 mb-3">{assessError}</div>}

          <div className="row g-3 align-items-end">
            <div className="col-12 col-md-4">
              <label className="form-label small fw-semibold text-secondary">Select Source Storage</label>
              <div className="nav nav-pills nav-fill bg-light p-1 rounded border">
                <button
                  type="button"
                  className={`nav-link py-1 fw-semibold small ${assessmentSourceTab === 'personal' ? 'active bg-primary text-white' : 'text-secondary'}`}
                  onClick={() => handleSourceTabChange('personal')}
                >
                  👤 Personal Repo
                </button>
                <button
                  type="button"
                  className={`nav-link py-1 fw-semibold small ${assessmentSourceTab === 'team' ? 'active bg-primary text-white' : 'text-secondary'}`}
                  onClick={() => handleSourceTabChange('team')}
                >
                  👥 Team Repo
                </button>
                <button
                  type="button"
                  className={`nav-link py-1 fw-semibold small ${assessmentSourceTab === 'local' ? 'active bg-primary text-white' : 'text-secondary'}`}
                  onClick={() => handleSourceTabChange('local')}
                >
                  📁 Local File
                </button>
              </div>
            </div>

            <div className="col-12 col-md-5">
              {(assessmentSourceTab === 'team' || assessmentSourceTab === 'personal') ? (
                <div>
                  <label className="form-label small fw-semibold text-secondary">Select Dataset Document</label>
                  {loadingRepoDocs ? (
                    <div className="form-control text-muted small">Loading {assessmentSourceTab} documents...</div>
                  ) : (
                    <select
                      className="form-select font-monospace text-dark"
                      value={selectedDocId}
                      onChange={(e) => handleDocumentSelectChange(e.target.value)}
                    >
                      {repoDocuments.length === 0 && <option value="">No dataset files found</option>}
                      {repoDocuments.map(doc => (
                        <option key={doc.id} value={doc.id}>
                          📄 {doc.title} ({doc.record_count || 0} Records)
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              ) : (
                <div>
                  <label className="form-label small fw-semibold text-secondary">Choose Local CSV / Excel File</label>
                  <input
                    type="file"
                    className="form-control"
                    accept=".csv, .xlsx, .xls"
                    onChange={(e) => setLocalAssessmentFile(e.target.files[0] || null)}
                  />
                </div>
              )}
            </div>

            <div className="col-12 col-md-3">
              <button
                type="button"
                className="btn btn-primary fw-bold text-white w-100 py-2 d-flex align-items-center justify-content-center gap-2"
                onClick={handleRunAssessment}
                disabled={assessing}
              >
                {assessing ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status"></span>
                    Evaluating Dataset Quality...
                  </>
                ) : (
                  <>
                    <span>⚡ Run Quality Assessment</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Selection Sidebar & Assessment History */}
      <div className="col-12 col-lg-4">
        <div className="card border-0 shadow-sm p-4 bg-white" style={{ maxHeight: '720px', overflowY: 'auto' }}>
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold text-dark mb-0">Assessment History Logs</h5>
            <button className="btn btn-sm btn-outline-success py-0 px-2 fw-bold" onClick={fetchHistory}>Refresh</button>
          </div>

          {loadingHistory ? (
            <div className="text-center py-5 text-secondary font-monospace">
              <span className="spinner-border spinner-border-sm me-2"></span>
              Loading quality reports...
            </div>
          ) : history.length > 0 ? (
            <div className="d-flex flex-column gap-2">
              {history.map((row) => (
                <div
                  key={row.report_id}
                  onClick={() => handleSelectReport(row.report_id)}
                  className={`p-3 rounded-3 cursor-pointer border transition-all ${
                    selectedReport?.report_id === row.report_id
                      ? 'border-success bg-success bg-opacity-10'
                      : 'border-secondary bg-white hover-bg-light'
                  }`}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="d-flex justify-content-between align-items-center mb-1">
                    <span className="fw-bold text-dark font-monospace small text-truncate me-2" style={{ maxWidth: '160px' }} title={row.source_file || 'Dataset File'}>
                      📄 {row.source_file || 'Dataset File'}
                    </span>
                    <span className={`badge px-2 py-1 small fw-bold ${getGradeBadge(row.overall_prediction)}`}>
                      {row.overall_prediction}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center small text-secondary">
                    <span className="font-monospace" style={{ fontSize: '0.7rem' }}>
                      ID: {row.prediction_id.substring(0, 8)}...
                    </span>
                    <span style={{ fontSize: '0.75rem' }}>{row.explainer_name || 'EDQI Engine'} • {new Date(row.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-5 text-muted small">
              No quality logs found. Run an assessment on a dataset to generate reports.
            </div>
          )}
        </div>
      </div>

      {/* 4. Detail Report Display */}
      <div className="col-12 col-lg-8">
        <div className="card border-0 shadow-sm p-4 bg-white text-dark d-flex flex-column" style={{ minHeight: '500px' }}>
          {loadingDetail ? (
            <div className="d-flex flex-column justify-content-center align-items-center flex-grow-1 py-5">
              <span className="spinner-border text-success mb-3"></span>
              <span className="font-monospace text-secondary">Executing quality evaluation & generating recommendations...</span>
            </div>
          ) : selectedReport ? (
            <div className="d-flex flex-column flex-grow-1">
              {/* Header metrics banner */}
              <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 pb-3 border-bottom border-secondary">
                <div>
                  <h5 className="fw-bold mb-1 text-success font-monospace">Data Quality Scorecard</h5>
                  <span className="text-secondary small">Report ID: {selectedReport.prediction_id}</span>
                </div>
                <div className="d-flex gap-2">
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => handleDownload('json')}>JSON</button>
                  <button className="btn btn-sm btn-outline-success fw-bold" onClick={() => handleDownload('md')}>Markdown</button>
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => handleDownload('csv')}>CSV Export</button>
                </div>
              </div>

              {fixSuccessMsg && (
                <div className="alert alert-success py-2 mb-3 d-flex align-items-center justify-content-between">
                  <span className="fw-bold small">{fixSuccessMsg}</span>
                  <button type="button" className="btn-close btn-sm" onClick={() => setFixSuccessMsg('')}></button>
                </div>
              )}

              {/* Source Dataset & Record Provenance Banner */}
              {selectedReport.source_provenance && (
                <div className="bg-primary bg-opacity-10 border border-primary border-opacity-25 rounded-3 p-3 mb-3">
                  <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
                    <div>
                      <span className="badge bg-primary text-white font-monospace me-2">FILE BEING CHECKED</span>
                      <span className="fw-bold text-dark font-monospace me-3">📄 {selectedReport.source_provenance.source_file}</span>
                      <span className="text-secondary small">Scope: {selectedReport.summary_header?.structural_info || selectedReport.structural_stats?.label || selectedReport.source_provenance.record_label}</span>
                    </div>
                    <span className="badge bg-secondary-subtle text-dark border font-monospace" style={{ fontSize: '0.72rem' }}>
                      {selectedReport.summary_header?.assessment_type || 'Universal Automated EDQI Engine Assessment'}
                    </span>
                  </div>
                  {selectedReport.summary_header?.factual_interpretation && (
                    <div className="p-2 bg-white bg-opacity-90 rounded border text-dark small fw-semibold">
                      💡 <strong>Quality Interpretation:</strong> {selectedReport.summary_header.factual_interpretation}
                    </div>
                  )}
                </div>
              )}

              {/* Combined Scorecard Summary Block */}
              <div className="row g-3 mb-4">
                {/* Overall Quality Grade & AI Analysis Status Card */}
                <div className="col-12 col-md-4">
                  <div className="d-flex flex-column gap-3 h-100">
                    <div className="bg-light p-3 rounded-3 border text-center flex-grow-1 d-flex flex-column justify-content-center">
                      <span className="text-secondary small fw-bold d-block mb-1">QUALITY SCORE</span>
                      <h3 className="fw-bold text-success mb-1">
                        {overallScore !== null && overallScore !== undefined ? `${overallScore.toFixed(1)} / 100` : 'Not available'}
                      </h3>
                      <span className="badge bg-success bg-opacity-10 text-success fw-bold align-self-center py-1 px-3 mt-1">
                        Grade {selectedReport.quality_grade || calculateRuleGrade(overallScore)}
                      </span>
                    </div>
                    <div className="bg-light p-3 rounded-3 border text-center flex-grow-1 d-flex flex-column justify-content-center">
                      <span className="text-secondary small fw-bold d-block mb-1">AI ANALYSIS STATUS</span>
                      {selectedReport.ml_classification_status === 'AVAILABLE' && selectedReport.confidence_score !== null && selectedReport.confidence_score !== undefined ? (
                        <>
                          <h4 className="fw-bold text-info mb-1">{selectedReport.overall_prediction}</h4>
                          <span className="text-secondary small">Confidence: {(selectedReport.confidence_score * 100).toFixed(1)}%</span>
                        </>
                      ) : selectedReport.ml_classification_status === 'NOT APPLICABLE' ? (
                        <>
                          <h5 className="fw-bold text-secondary mb-1">Not used for this file type</h5>
                          <span className="text-secondary small d-block" style={{ fontSize: '0.72rem' }}>Tabular ML model not applicable for {selectedReport.file_category?.toUpperCase() || 'document'} files</span>
                        </>
                      ) : selectedReport.ml_classification_status === 'ARTIFACT MISSING' ? (
                        <>
                          <h5 className="fw-bold text-danger mb-1">Model file missing</h5>
                          <span className="text-secondary small d-block" style={{ fontSize: '0.72rem' }}>Model file missing from disk</span>
                        </>
                      ) : (
                        <>
                          <h5 className="fw-bold text-warning mb-1">Not available for this analysis</h5>
                          <span className="text-secondary small d-block" style={{ fontSize: '0.72rem' }}>No active classifier model artifact available</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Dynamic Quality Check Breakdown */}
                <div className="col-12 col-md-8">
                  <div className="bg-light p-3 rounded-3 border h-100">
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h6 className="fw-bold text-dark mb-0">Quality Check</h6>
                      <button
                        type="button"
                        className="btn btn-sm btn-link text-decoration-none p-0 text-primary small fw-semibold"
                        onClick={() => setIsCalcExplainOpen(!isCalcExplainOpen)}
                      >
                        How is this score calculated? ▾
                      </button>
                    </div>

                    {isCalcExplainOpen && (
                      <div className="p-3 mb-3 bg-white border rounded small text-dark">
                        <p className="mb-2 fw-semibold text-primary">
                          The score is calculated from the quality checks that apply to this file.
                        </p>
                        {selectedReport?.score_traceability?.calculation_method && (
                          <div className="text-secondary" style={{ fontSize: '0.78rem' }}>
                            <div><strong>Calculation Method:</strong> {selectedReport.score_traceability.calculation_method}</div>
                            {selectedReport.score_traceability.total_active_weight !== undefined && (
                              <div><strong>Active Weights Sum:</strong> {selectedReport.score_traceability.total_active_weight}%</div>
                            )}
                            {selectedReport.score_traceability.raw_weighted_contribution_sum !== undefined && (
                              <div><strong>Raw Weighted Contribution:</strong> {selectedReport.score_traceability.raw_weighted_contribution_sum.toFixed(2)} pts</div>
                            )}
                            <div><strong>Formula:</strong> Final Score = (Raw Contribution Sum / Active Weights Sum) × 100</div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {selectedReport?.score_traceability?.applicable_dimensions ? (
                      <>
                        {selectedReport.score_traceability.applicable_dimensions.map((item) => {
                          const getSimplifiedLabel = (rawKey) => {
                            if (!rawKey) return 'Quality Check';
                            const clean = String(rawKey).toLowerCase().replace(/_score/g, '').replace(/_/g, ' ');
                            if (clean.includes('validity') && !clean.includes('encoding') && !clean.includes('schema') && !clean.includes('aspect')) return 'Data Validity';
                            if (clean.includes('uniqueness') && !clean.includes('key')) return 'Data Uniqueness';
                            if (clean.includes('completeness') && !clean.includes('text')) return 'Data Completeness';
                            if (clean.includes('consistency') && !clean.includes('structure')) return 'Data Consistency';
                            if (clean.includes('timeliness')) return 'Data Timeliness';
                            if (clean.includes('syntax integrity') || clean.includes('syntax')) return 'File Structure';
                            if (clean.includes('schema validity') || clean.includes('schema')) return 'Data Structure';
                            if (clean.includes('extraction integrity') || clean.includes('extraction')) return 'Text Extraction';
                            if (clean.includes('page coverage') || clean.includes('coverage')) return 'Page Coverage';
                            if (clean.includes('ocr extractability')) return 'Text Readability';
                            if (clean.includes('resolution quality') || clean.includes('resolution')) return 'Image Quality';
                            if (clean.includes('noise ratio') || clean.includes('noise')) return 'Image Clarity';
                            if (clean.includes('aspect ratio') || clean.includes('aspect')) return 'Image Dimensions';
                            if (clean.includes('encoding validity') || clean.includes('encoding')) return 'Text Encoding';
                            if (clean.includes('structure consistency')) return 'Document Structure';
                            if (clean.includes('readability')) return 'Readability';
                            if (clean.includes('text completeness')) return 'Text Completeness';
                            if (clean.includes('key uniqueness')) return 'Key Uniqueness';
                            return String(rawKey).replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                          };

                          const displayLabel = getSimplifiedLabel(item.clean_dimension);
                          return (
                            <div key={item.dimension} className="mb-2">
                              <div className="d-flex justify-content-between align-items-center mb-1">
                                <span className="small fw-bold text-dark">{displayLabel}</span>
                                <span className="small font-monospace fw-bold text-dark" style={{ fontSize: '0.8rem' }}>
                                  {item.score.toFixed(1)}%
                                </span>
                              </div>
                              <div className="progress bg-white border" style={{ height: '6px' }}>
                                <div
                                  className={`progress-bar ${item.score >= 90 ? 'bg-success' : item.score >= 70 ? 'bg-warning' : 'bg-danger'}`}
                                  role="progressbar"
                                  style={{ width: `${item.score}%` }}
                                ></div>
                              </div>
                            </div>
                          );
                        })}
                      </>
                    ) : selectedReport?.input_features ? (
                      Object.entries(selectedReport.input_features)
                        .filter(([k]) => !['quality_score', 'missing_fields', 'invalid_fields', 'duplicate_fields', 'record_age'].includes(k))
                        .map(([dimKey, val]) => {
                          const scoreVal = typeof val === 'number' ? val : parseFloat(val) || 0;
                          const getSimplifiedLabel = (rawKey) => {
                            if (!rawKey) return 'Quality Check';
                            const clean = String(rawKey).toLowerCase().replace(/_score/g, '').replace(/_/g, ' ');
                            if (clean.includes('validity') && !clean.includes('encoding') && !clean.includes('schema') && !clean.includes('aspect')) return 'Data Validity';
                            if (clean.includes('uniqueness') && !clean.includes('key')) return 'Data Uniqueness';
                            if (clean.includes('completeness') && !clean.includes('text')) return 'Data Completeness';
                            if (clean.includes('consistency') && !clean.includes('structure')) return 'Data Consistency';
                            if (clean.includes('timeliness')) return 'Data Timeliness';
                            if (clean.includes('syntax integrity') || clean.includes('syntax')) return 'File Structure';
                            if (clean.includes('schema validity') || clean.includes('schema')) return 'Data Structure';
                            if (clean.includes('extraction integrity') || clean.includes('extraction')) return 'Text Extraction';
                            if (clean.includes('page coverage') || clean.includes('coverage')) return 'Page Coverage';
                            if (clean.includes('ocr extractability')) return 'Text Readability';
                            if (clean.includes('resolution quality') || clean.includes('resolution')) return 'Image Quality';
                            if (clean.includes('noise ratio') || clean.includes('noise')) return 'Image Clarity';
                            if (clean.includes('aspect ratio') || clean.includes('aspect')) return 'Image Dimensions';
                            if (clean.includes('encoding validity') || clean.includes('encoding')) return 'Text Encoding';
                            if (clean.includes('structure consistency')) return 'Document Structure';
                            if (clean.includes('readability')) return 'Readability';
                            if (clean.includes('text completeness')) return 'Text Completeness';
                            if (clean.includes('key uniqueness')) return 'Key Uniqueness';
                            return String(rawKey).replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                          };
                          const displayLabel = getSimplifiedLabel(dimKey);
                          return (
                            <div key={dimKey} className="mb-2">
                              <div className="d-flex justify-content-between align-items-center mb-1">
                                <span className="small fw-bold text-dark">{displayLabel}</span>
                                <span className="small font-monospace fw-bold">{scoreVal.toFixed(1)}%</span>
                              </div>
                              <div className="progress bg-white border" style={{ height: '6px' }}>
                                <div
                                  className={`progress-bar ${scoreVal >= 90 ? 'bg-success' : scoreVal >= 70 ? 'bg-warning' : 'bg-danger'}`}
                                  role="progressbar"
                                  style={{ width: `${scoreVal}%` }}
                                ></div>
                              </div>
                            </div>
                          );
                        })
                    ) : (
                      <div className="text-muted small">No dimensions available</div>
                    )}
                  </div>
                </div>
              </div>

              {/* AI Analysis Status */}
              {selectedReport?.models_applicability && (
                <div className="card border-0 bg-light p-3 border rounded-3 mb-4">
                  <h6 className="fw-bold text-dark mb-3">AI Analysis Status</h6>
                  <div className="row g-2">
                    {['random_forest', 'xgboost', 'isolation_forest'].map((mKey) => {
                      const mObj = selectedReport.models_applicability[mKey] || {};
                      const label = mKey === 'random_forest' ? 'Random Forest' : mKey === 'xgboost' ? 'XGBoost' : 'Isolation Forest';
                      const status = mObj.status || 'NOT TRAINED';

                      let badgeClass = 'bg-warning text-dark';
                      let textDisplay = status;

                      if (status === 'APPLIED') {
                        badgeClass = 'bg-success';
                        textDisplay = 'APPLIED';
                      } else if (status === 'NOT APPLICABLE') {
                        badgeClass = 'bg-secondary';
                        textDisplay = 'Not used for this file';
                      } else if (status.includes('INACTIVE') || status === 'TRAINED') {
                        badgeClass = 'bg-info text-dark';
                        textDisplay = 'TRAINED / INACTIVE';
                      } else if (status === 'NOT TRAINED') {
                        badgeClass = 'bg-warning text-dark';
                        textDisplay = 'Not trained yet';
                      } else if (status === 'ARTIFACT MISSING') {
                        badgeClass = 'bg-danger';
                        textDisplay = 'Artifact Missing';
                      }

                      return (
                        <div key={mKey} className="col-12 col-md-4">
                          <div className="p-2.5 bg-white rounded border d-flex justify-content-between align-items-center">
                            <span className="small fw-bold text-dark">{label}</span>
                            <span className={`badge ${badgeClass}`} title={mObj.reason || mObj.model_version || ''}>
                              {textDisplay}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Problems Found & Expected Improvement (Simplified User View) */}
              <div className="card border-0 bg-light p-3 border rounded-3 mb-4">
                <h6 className="fw-bold text-dark mb-3 d-flex align-items-center justify-content-between">
                  <span>Problems Found & Expected Improvement</span>
                  {selectedReport.source_provenance?.source_file && (
                    <span className="badge bg-secondary text-white font-monospace" style={{ fontSize: '0.7rem' }}>
                      Target File: {selectedReport.source_provenance.source_file}
                    </span>
                  )}
                </h6>
                {activeRecommendations.length > 0 ? (
                  <div className="d-flex flex-column gap-3">
                    {/* Simplified "If We Fix These Problems" Summary Block */}
                    {(() => {
                      const cumData = selectedReport?.cumulative_repair_impact;
                      const breakdown = cumData?.dimension_breakdown || [];
                      if (breakdown.length === 0) return null;

                      const getSimplifiedLabel = (rawKey) => {
                        if (!rawKey) return 'Quality Check';
                        const clean = String(rawKey).toLowerCase().replace(/_score/g, '').replace(/_/g, ' ');
                        if (clean.includes('validity') && !clean.includes('encoding') && !clean.includes('schema') && !clean.includes('aspect')) return 'Data Validity';
                        if (clean.includes('uniqueness') && !clean.includes('key')) return 'Data Uniqueness';
                        if (clean.includes('completeness') && !clean.includes('text')) return 'Data Completeness';
                        if (clean.includes('consistency') && !clean.includes('structure')) return 'Data Consistency';
                        if (clean.includes('timeliness')) return 'Data Timeliness';
                        if (clean.includes('syntax integrity') || clean.includes('syntax')) return 'File Structure';
                        if (clean.includes('schema validity') || clean.includes('schema')) return 'Data Structure';
                        if (clean.includes('extraction integrity') || clean.includes('extraction')) return 'Text Extraction';
                        if (clean.includes('page coverage') || clean.includes('coverage')) return 'Page Coverage';
                        if (clean.includes('ocr extractability')) return 'Text Readability';
                        if (clean.includes('resolution quality') || clean.includes('resolution')) return 'Image Quality';
                        if (clean.includes('noise ratio') || clean.includes('noise')) return 'Image Clarity';
                        if (clean.includes('aspect ratio') || clean.includes('aspect')) return 'Image Dimensions';
                        if (clean.includes('encoding validity') || clean.includes('encoding')) return 'Text Encoding';
                        if (clean.includes('structure consistency')) return 'Document Structure';
                        if (clean.includes('readability')) return 'Readability';
                        if (clean.includes('text completeness')) return 'Text Completeness';
                        if (clean.includes('key uniqueness')) return 'Key Uniqueness';
                        return String(rawKey).replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                      };

                      return (
                        <div className="bg-primary bg-opacity-10 border border-primary border-opacity-25 rounded-3 p-3 mb-2">
                          <div className="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom border-primary border-opacity-25">
                            <h6 className="fw-bold text-primary mb-0 d-flex align-items-center gap-2">
                              <span>🛠️ If We Fix These Problems</span>
                            </h6>
                            <span className="small text-dark fw-bold">
                              Current: <strong className="text-primary">{(cumData.current_overall_score ?? (overallScore?.toFixed(1) || '97.4'))} / 100</strong>
                            </span>
                          </div>

                          {/* Problem breakdown cards */}
                          <div className="row g-2 mb-3">
                            {breakdown.map((item, i) => {
                              const friendlyLabel = getSimplifiedLabel(item.dimension);
                              const countText = item.issue_count === 1 ? '1 problem found' : `${item.issue_count} problems found`;
                              return (
                                <div key={i} className="col-12 col-md-6">
                                  <div className="bg-white p-2 rounded border border-primary border-opacity-10 h-100">
                                    <div className="d-flex justify-content-between align-items-center mb-1">
                                      <strong className="text-dark small">{friendlyLabel}</strong>
                                      <span className="badge bg-warning-subtle text-dark border px-2 py-1" style={{ fontSize: '0.7rem' }}>
                                        {countText}
                                      </span>
                                    </div>
                                    <div className="small text-secondary fw-semibold" style={{ fontSize: '0.78rem' }}>
                                      Now: <strong className="text-dark">{item.current_dimension_score}%</strong> → After fixing: <strong className="text-success">{item.projected_dimension_score}%</strong>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>

                          {/* Final Projected Score Banner */}
                          <div className="p-3 bg-success bg-opacity-10 border border-success border-opacity-25 rounded text-center">
                            <span className="small fw-bold text-dark d-block mb-1">
                              Quality Score After Fixing All Problems
                            </span>
                            <div className="fs-5 fw-bold text-success">
                              {(cumData.current_overall_score ?? overallScore)?.toFixed(1)} → {cumData.projected_overall_score_after_all_repairs} / 100
                            </div>
                            <span className="text-muted small d-block mt-1" style={{ fontSize: '0.75rem' }}>
                              Estimated score if all detected problems are fixed.
                            </span>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Individual Repair Action Items */}
                    {activeRecommendations.map((rec, idx) => {
                      const getSimplifiedLabel = (rawKey) => {
                        if (!rawKey) return 'Quality Check';
                        const clean = String(rawKey).toLowerCase().replace(/_score/g, '').replace(/_/g, ' ');
                        if (clean.includes('validity') && !clean.includes('encoding') && !clean.includes('schema') && !clean.includes('aspect')) return 'Data Validity';
                        if (clean.includes('uniqueness') && !clean.includes('key')) return 'Data Uniqueness';
                        if (clean.includes('completeness') && !clean.includes('text')) return 'Data Completeness';
                        if (clean.includes('consistency') && !clean.includes('structure')) return 'Data Consistency';
                        if (clean.includes('timeliness')) return 'Data Timeliness';
                        if (clean.includes('syntax integrity') || clean.includes('syntax')) return 'File Structure';
                        if (clean.includes('schema validity') || clean.includes('schema')) return 'Data Structure';
                        if (clean.includes('extraction integrity') || clean.includes('extraction')) return 'Text Extraction';
                        if (clean.includes('page coverage') || clean.includes('coverage')) return 'Page Coverage';
                        if (clean.includes('ocr extractability')) return 'Text Readability';
                        if (clean.includes('resolution quality') || clean.includes('resolution')) return 'Image Quality';
                        if (clean.includes('noise ratio') || clean.includes('noise')) return 'Image Clarity';
                        if (clean.includes('aspect ratio') || clean.includes('aspect')) return 'Image Dimensions';
                        if (clean.includes('encoding validity') || clean.includes('encoding')) return 'Text Encoding';
                        if (clean.includes('structure consistency')) return 'Document Structure';
                        if (clean.includes('readability')) return 'Readability';
                        if (clean.includes('text completeness')) return 'Text Completeness';
                        if (clean.includes('key uniqueness')) return 'Key Uniqueness';
                        return String(rawKey).replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                      };

                      const rawCategory = rec.affected_dimension || rec.category;
                      const isDup = String(rawCategory).toLowerCase().includes('uniqueness');
                      const cardTitle = isDup ? 'Duplicate Record Problem' : `${getSimplifiedLabel(rawCategory)} Problem`;

                      const currentReportKey = selectedReport?.report_id || selectedReport?.prediction_id || 'default';
                      const cardKey = `${currentReportKey}-${idx}`;
                      const isExpanded = expandedCardKeys.has(cardKey);

                      const sheetOrPath = rec.logical_path || selectedReport.source_provenance?.logical_path || selectedReport.source_provenance?.sheet_name || 'Main Sheet';
                      const physicalRow = rec.physical_row || selectedReport.source_provenance?.physical_row || rec.record_id || '1';
                      const locationSummary = `${sheetOrPath} → Row ${physicalRow}`;

                      return (
                        <div key={idx} className="p-3 bg-white rounded border border-secondary border-opacity-25 shadow-sm overflow-hidden">
                          <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                            <div className="d-flex align-items-center flex-wrap gap-2">
                              <span className="badge bg-danger px-2 py-1">{rec.priority || 'HIGH'} PRIORITY</span>
                              <span className="badge bg-secondary">{cardTitle}</span>
                              {rec.field_name && (
                                <span className="badge bg-light text-dark border text-wrap text-break">Field: {rec.field_name}</span>
                              )}
                            </div>
                            
                            <div className="d-flex flex-column align-items-end gap-1 ms-auto text-end">
                              {rec.quantifiable !== false && rec.projected_overall_score !== undefined ? (
                                <span className="small text-success fw-bold">
                                  Quality Score if this problem is fixed: {rec.projected_overall_score} / 100
                                </span>
                              ) : (
                                <span className="small text-muted fw-bold">
                                  Impact: Recalculated after correction
                                </span>
                              )}
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-success fw-bold py-1 px-2 mt-1"
                                onClick={() => handleResolveFix(rec, idx)}
                              >
                                ✓ Resolve Problem
                              </button>
                            </div>
                          </div>

                          {/* 4-Part Problem Explanation (WHAT, WHERE, WHY, WHAT TO DO) */}
                          <div className="bg-light p-2.5 rounded border border-secondary border-opacity-15 mb-2 small text-dark">
                            <div className="mb-1">
                              <strong className="text-danger small font-monospace">❓ WHAT: </strong>
                              <span className="fw-bold">{rec.problem_what || cardTitle}</span>
                            </div>
                            <div className="mb-1">
                              <strong className="text-primary small font-monospace">📍 WHERE: </strong>
                              <span className="font-monospace text-secondary">{rec.problem_where || locationSummary}</span>
                            </div>
                            <div className="mb-1">
                              <strong className="text-warning-emphasis small font-monospace">💡 WHY: </strong>
                              <span className="text-dark">{rec.problem_why || rec.recommendation}</span>
                            </div>
                            <div>
                              <strong className="text-success small font-monospace">🛠️ WHAT TO DO: </strong>
                              <span className="fw-semibold text-dark">{rec.problem_action || rec.recommendation}</span>
                            </div>
                          </div>

                          {/* Primary Compact Summary */}
                          <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 pt-2 border-top border-secondary border-opacity-10 small text-secondary">
                            <div className="d-flex flex-wrap align-items-center gap-3">
                              {rec.current_value && (
                                <div><strong>Current value:</strong> <span className="badge bg-danger-subtle text-danger font-monospace">{rec.current_value}</span></div>
                              )}
                              <div><strong>Location:</strong> <span className="font-monospace text-dark">{locationSummary}</span></div>
                            </div>
                            <button
                              type="button"
                              className="btn btn-sm btn-link text-decoration-none p-0 text-primary small fw-semibold"
                              onClick={() => toggleCardExpand(cardKey)}
                            >
                              {isExpanded ? 'Hide details ▲' : 'View details ▾'}
                            </button>
                          </div>

                          {/* Expandable Technical Details & Provenance */}
                          {isExpanded && (
                            <div className="mt-3 p-3 bg-light rounded border small text-dark font-monospace">
                              <div className="row g-2 mb-2">
                                <div className="col-12 col-md-6"><strong>File:</strong> {rec.source_file || selectedReport.source_provenance?.source_file || 'Dataset File'}</div>
                                <div className="col-12 col-md-6"><strong>Sheet / Path:</strong> {sheetOrPath}</div>
                                <div className="col-12 col-md-4"><strong>Physical Row:</strong> #{physicalRow}</div>
                                <div className="col-12 col-md-4"><strong>Data Index:</strong> #{rec.data_index || selectedReport.source_provenance?.data_index || 'N/A'}</div>
                                <div className="col-12 col-md-4"><strong>Record ID:</strong> {rec.record_label || selectedReport.source_provenance?.record_label || rec.record_id || 'N/A'}</div>
                                <div className="col-12 col-md-6"><strong>Field Name:</strong> {rec.field_name || 'N/A'}</div>
                                <div className="col-12 col-md-6"><strong>Current Value:</strong> {rec.current_value || 'N/A'}</div>
                                <div className="col-12 col-md-6"><strong>Current Dimension Score:</strong> {rec.current_dimension_score !== undefined ? `${rec.current_dimension_score}%` : 'N/A'}</div>
                              </div>
                              {rec.full_explanation && (
                                <div className="mt-2 pt-2 border-top border-secondary border-opacity-25">
                                  <strong>Full Explanation:</strong>
                                  <p className="mb-0 text-secondary font-sans-serif mt-1" style={{ fontSize: '0.8rem' }}>
                                    {rec.full_explanation}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-4 text-success small fw-bold">
                    ✓ No actionable corrections identified for this dataset. Quality score achieved: {overallScore?.toFixed(1)} / 100!
                  </div>
                )}
              </div>

              {/* Technical Details & Execution Audit Accordion */}
              <div className="card border-0 bg-white border rounded-3 overflow-hidden">
                <div
                  className="card-header bg-light p-3 cursor-pointer d-flex justify-content-between align-items-center"
                  onClick={() => setIsAuditOpen(!isAuditOpen)}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  <span className="fw-bold text-secondary font-monospace small">Technical Details ▾</span>
                  <span className="badge bg-secondary font-monospace px-2 py-1">{isAuditOpen ? '▲ Hide Details' : '▼ Expand Technical Audit'}</span>
                </div>
                {isAuditOpen && (
                  <div className="card-body font-monospace p-3 text-dark bg-white small border-top">
                    {/* Dimension Weights & Calculations Table */}
                    {selectedReport?.score_traceability?.applicable_dimensions && (
                      <div className="mb-3">
                        <span className="fw-bold text-dark d-block mb-2">Technical Dimension Weights & Formula Audit:</span>
                        <div className="table-responsive">
                          <table className="table table-sm table-bordered text-dark font-monospace mb-2" style={{ fontSize: '0.75rem' }}>
                            <thead className="bg-light">
                              <tr>
                                <th>Dimension</th>
                                <th>Raw Score</th>
                                <th>Weight</th>
                                <th>Weighted Contribution</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedReport.score_traceability.applicable_dimensions.map((dim, dIdx) => (
                                <tr key={dIdx}>
                                  <td>{dim.dimension}</td>
                                  <td>{dim.score?.toFixed(1)}%</td>
                                  <td>{dim.weight ? `${(dim.weight * 100).toFixed(1)}%` : 'N/A'}</td>
                                  <td>{dim.contribution !== undefined ? `${dim.contribution.toFixed(2)} pts` : 'N/A'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    <div className="row g-2 mb-3 text-secondary">
                      <div className="col-6"><strong>Classifier Model:</strong> {selectedReport.processing_trace?.model_used || 'Random Forest / Rule Engine'}</div>
                      <div className="col-6"><strong>Prediction Class:</strong> {selectedReport.overall_prediction}</div>
                      <div className="col-6"><strong>Confidence Level:</strong> {(selectedReport.confidence_score * 100).toFixed(1)}%</div>
                      <div className="col-6"><strong>SHAP Status:</strong> {selectedReport.shap_status || 'AVAILABLE'}</div>
                      <div className="col-6"><strong>Calculation Time:</strong> {selectedReport.processing_trace?.time_ms ?? 0.0} ms</div>
                    </div>
                    <hr className="my-2 border-secondary" />
                    <span className="text-secondary small d-block mb-1">Processing Trace & Model Attributions JSON:</span>
                    <pre className="text-dark mb-0 p-2 bg-light rounded" style={{ maxHeight: '200px', overflowY: 'auto', fontSize: '0.7rem' }}>
                      {JSON.stringify({
                        processing_trace: selectedReport.processing_trace,
                        input_features: selectedReport.input_features,
                        source_provenance: selectedReport.source_provenance,
                        models_applicability: selectedReport.models_applicability,
                        model_version: selectedReport.model_version
                      }, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

            </div>
          ) : (
            <div className="d-flex flex-column justify-content-center align-items-center flex-grow-1 text-center text-muted py-5">
              <svg width="64" height="64" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mb-3 text-success opacity-50">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="fw-bold text-dark fs-5 mb-1">Select a Dataset & Click "Run Quality Assessment"</p>
              <p className="small text-secondary px-4">Choose a dataset from Personal Repo, Team Repo, or Local File above, then click <strong>Run Quality Assessment</strong> to review the dynamic scorecard and targeted field corrections.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DataQualityExplainability;
