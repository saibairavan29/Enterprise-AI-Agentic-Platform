import React, { useState, useEffect } from 'react';
import client from '../api/client';

const DataQualityExplainability = () => {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeReportTab, setActiveReportTab] = useState('summary'); // 'summary' | 'attributions' | 'recommendations'
  
  // Cache counters
  const [cacheStats, setCacheStats] = useState({ hits: 0, misses: 0, ratio: 1.0 });

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
      // Auto-select first report if none selected
      if (res.data.length > 0 && !selectedReport) {
        handleSelectReport(res.data[0].report_id);
      }
    } catch (err) {
      console.error("Failed to load history", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  // 3. Fetch detailed explanation report
  const handleSelectReport = async (reportId) => {
    setLoadingDetail(true);
    try {
      const res = await client.get(`edqi/explanations/${reportId}/`);
      setSelectedReport(res.data);
      // Refresh cache indices
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

  // 4. Download files downloads
  const handleDownload = (format) => {
    if (!selectedReport) return;
    const url = `${client.defaults.baseURL}edqi/explanations/${selectedReport.report_id}/?format=${format}`;
    window.open(url, '_blank');
  };

  useEffect(() => {
    fetchStats();
    fetchHistory();
  }, []);

  // UI styling classes matching Dashboard
  const getGradeBadge = (grade) => {
    const g = String(grade).toUpperCase();
    if (g === 'EXCELLENT') return 'bg-success text-white';
    if (g === 'GOOD') return 'bg-info text-dark';
    if (g === 'AVERAGE') return 'bg-warning text-dark';
    return 'bg-danger text-white';
  };

  const getPriorityBadge = (priority) => {
    const p = String(priority).toUpperCase();
    if (p === 'HIGH') return 'bg-danger text-white';
    if (p === 'MEDIUM') return 'bg-warning text-dark';
    return 'bg-secondary text-white';
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
  const overallScore = getDimensionScore('quality', null);

  return (
    <div className="row g-4 text-dark bg-light">
      {/* 1. Header Overview Cards */}
      <div className="col-12">
        <div className="row g-3">
          <div className="col-6 col-lg-3">
            <div className="card border-0 shadow-sm p-3 text-center bg-white">
              <span className="text-secondary small d-block mb-1">REPORTS COMPILED</span>
              <h3 className="fw-bold text-success mb-0">{stats?.total_explanations ?? 0}</h3>
            </div>
          </div>
          <div className="col-6 col-lg-3">
            <div className="card border-0 shadow-sm p-3 text-center bg-white">
              <span className="text-secondary small d-block mb-1">AVERAGE CONFIDENCE</span>
              <h3 className="fw-bold text-success mb-0">{stats ? `${(stats.average_confidence * 100).toFixed(1)}%` : '0.0%'}</h3>
            </div>
          </div>
          <div className="col-6 col-lg-3">
            <div className="card border-0 shadow-sm p-3 text-center bg-white">
              <span className="text-secondary small d-block mb-1">RECOMMENDED ACTIONS</span>
              <h3 className="fw-bold text-warning mb-0">{stats?.total_recommendations ?? 0}</h3>
            </div>
          </div>
          <div className="col-6 col-lg-3">
            <div className="card border-0 shadow-sm p-3 text-center bg-white">
              <span className="text-secondary small d-block mb-1">EXPLANATION CACHE RATIO</span>
              <h3 className="fw-bold text-info mb-0">{cacheStats ? `${(cacheStats.ratio * 100).toFixed(1)}%` : '100%'}</h3>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Selection Sidebar & History */}
      <div className="col-12 col-lg-4">
        <div className="card border-0 shadow-sm p-4 bg-white" style={{ maxHeight: '720px', overflowY: 'auto' }}>
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold text-dark mb-0">Quality Reports</h5>
            <button className="btn btn-sm btn-outline-success py-0 px-2 fw-bold" onClick={fetchHistory}>Refresh</button>
          </div>

          {loadingHistory ? (
            <div className="text-center py-5 text-secondary font-monospace">
              <span className="spinner-border spinner-border-sm me-2"></span>
              Loading reports...
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
                    <span className="small font-monospace text-secondary" style={{ fontSize: '0.7rem' }}>
                      ID: {row.prediction_id.substring(0, 8)}...
                    </span>
                    <span className={`badge px-2 py-1 small fw-bold ${getGradeBadge(row.overall_prediction)}`}>
                      {row.overall_prediction}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between small text-secondary">
                    <span>{row.explainer_name}</span>
                    <span>{new Date(row.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-5 text-muted small">
              No quality logs found. Ingest a document to assess its parameters.
            </div>
          )}
        </div>
      </div>

      {/* 3. Detail Report Display */}
      <div className="col-12 col-lg-8">
        <div className="card border-0 shadow-sm p-4 bg-white text-dark d-flex flex-column" style={{ minHeight: '500px' }}>
          {loadingDetail ? (
            <div className="d-flex flex-column justify-content-center align-items-center flex-grow-1 py-5">
              <span className="spinner-border text-success mb-3"></span>
              <span className="font-monospace text-secondary">Loading quality details...</span>
            </div>
          ) : selectedReport ? (
            <div className="d-flex flex-column flex-grow-1">
              {/* Header metrics banner */}
              <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 pb-3 border-bottom border-secondary">
                <div>
                  <h5 className="fw-bold mb-1 text-success font-monospace">Data Quality Report</h5>
                  <span className="text-secondary small">Report ID: {selectedReport.prediction_id}</span>
                </div>
                <div className="d-flex gap-2">
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => handleDownload('json')}>JSON</button>
                  <button className="btn btn-sm btn-outline-success fw-bold" onClick={() => handleDownload('md')}>Markdown</button>
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => handleDownload('csv')}>CSV Export</button>
                </div>
              </div>

              {/* Combined Scorecard Summary Block */}
              <div className="row g-3 mb-4">
                {/* Overall Quality Grade & ML Assessment Card */}
                <div className="col-12 col-md-4">
                  <div className="d-flex flex-column gap-3 h-100">
                    <div className="bg-light p-3 rounded-3 border text-center flex-grow-1 d-flex flex-column justify-content-center">
                      <span className="text-secondary small fw-bold d-block mb-1">DATA QUALITY SCORE</span>
                      <h3 className="fw-bold text-success mb-1">
                        {overallScore !== null ? `${overallScore.toFixed(2)} / 100` : 'Not available'}
                      </h3>
                      <span className="badge bg-success bg-opacity-10 text-success fw-bold align-self-center py-1 px-3 mt-1">Grade {calculateRuleGrade(overallScore)}</span>
                    </div>
                    <div className="bg-light p-3 rounded-3 border text-center flex-grow-1 d-flex flex-column justify-content-center">
                      <span className="text-secondary small fw-bold d-block mb-1">MODEL ASSESSMENT</span>
                      <h4 className="fw-bold text-info mb-1">{selectedReport.overall_prediction}</h4>
                      <span className="text-secondary small">Confidence: {(selectedReport.confidence_score * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>

                {/* Dimensions Scorecard Breakdown */}
                <div className="col-12 col-md-8">
                  <div className="bg-light p-3 rounded-3 border h-100">
                    <h6 className="fw-bold text-dark mb-3 font-monospace">Quality Breakdown</h6>
                    
                    {[
                      { key: 'completeness', label: 'Completeness', score: completeness },
                      { key: 'validity', label: 'Validity', score: validity },
                      { key: 'consistency', label: 'Consistency', score: consistency },
                      { key: 'uniqueness', label: 'Uniqueness', score: uniqueness },
                      { key: 'timeliness', label: 'Timeliness', score: timeliness }
                    ].map(dim => {
                      const hasScore = dim.score !== null && dim.score !== undefined;
                      const displayScore = hasScore ? `${dim.score.toFixed(0)}%` : 'Not available';
                      const barWidth = hasScore ? dim.score : 0;
                      return (
                        <div key={dim.key} className="mb-2">
                          <div className="d-flex justify-content-between align-items-center mb-1">
                            <span className="small fw-bold text-dark">{dim.label}</span>
                            <span className="small font-monospace fw-bold">{displayScore}</span>
                          </div>
                          <div className="progress bg-white border" style={{ height: '6px' }} title={getDimensionText(dim.key)}>
                            <div
                              className={`progress-bar ${!hasScore ? 'bg-secondary' : dim.score >= 90 ? 'bg-success' : dim.score >= 70 ? 'bg-warning' : 'bg-danger'}`}
                              role="progressbar"
                              style={{ width: `${barWidth}%` }}
                            ></div>
                          </div>
                          <span className="text-muted d-block" style={{ fontSize: '0.65rem' }}>{getDimensionText(dim.key)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* ML Model Prediction Drivers Card */}
              {(() => {
                const positiveDrivers = (selectedReport.top_positive_features || []).filter(item => item.percentage > 0.01);
                const negativeDrivers = (selectedReport.top_negative_features || []).filter(item => item.percentage > 0.01);
                return (
                  <div className="card border-0 bg-light p-3 border rounded-3 mb-4">
                    <h6 className="fw-bold text-dark mb-1">ML Model Prediction Drivers</h6>
                    <p className="text-muted small mb-3">These factors show how the ML model assessed this record.</p>
                    <div className="row g-3">
                      <div className="col-12 col-md-6 border-end border-secondary border-opacity-25">
                        <h6 className="small text-success fw-bold font-monospace border-bottom pb-2 mb-3">✓ POSITIVE DRIVERS (ML Model)</h6>
                        {positiveDrivers.length > 0 ? (
                          <div className="d-flex flex-column gap-2 small">
                            {positiveDrivers.map((item, idx) => {
                              const featName = item.feature.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                              const val = selectedReport.input_features?.[item.feature] !== undefined && selectedReport.input_features?.[item.feature] !== null ? selectedReport.input_features[item.feature] : 'N/A';
                              return (
                                <div key={idx} className="p-2 bg-white rounded border d-flex flex-column gap-1">
                                  <div className="d-flex justify-content-between">
                                    <strong>{featName}</strong>
                                    <span className="text-success small font-monospace fw-bold">+{item.percentage}%</span>
                                  </div>
                                  <div className="text-muted d-flex justify-content-between" style={{ fontSize: '0.75rem' }}>
                                    <span>Value: {val}</span>
                                    <span>Positive model influence</span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="text-muted small">No distinct positive drivers computed.</p>
                        )}
                      </div>

                      <div className="col-12 col-md-6">
                        <h6 className="small text-danger fw-bold font-monospace border-bottom pb-2 mb-3">⚠ NEGATIVE DRIVERS (ML Model)</h6>
                        {negativeDrivers.length > 0 ? (
                          <div className="d-flex flex-column gap-2 small">
                            {negativeDrivers.map((item, idx) => {
                              const featName = item.feature.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                              const val = selectedReport.input_features?.[item.feature] !== undefined && selectedReport.input_features?.[item.feature] !== null ? selectedReport.input_features[item.feature] : 'N/A';
                              return (
                                <div key={idx} className="p-2 bg-white rounded border d-flex flex-column gap-1">
                                  <div className="d-flex justify-content-between">
                                    <strong>{featName}</strong>
                                    <span className="text-danger small font-monospace fw-bold">-{item.percentage}%</span>
                                  </div>
                                  <div className="text-muted d-flex justify-content-between" style={{ fontSize: '0.75rem' }}>
                                    <span>Value: {val}</span>
                                    <span>Negative model influence</span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="text-success small">✓ No negative quality violations flagged.</p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* What Should I Fix Card */}
              <div className="card border-0 bg-light p-3 border rounded-3 mb-4">
                <h6 className="fw-bold text-dark mb-3">What Should I Fix?</h6>
                {selectedReport.recommendations?.length > 0 ? (
                  <div className="d-flex flex-column gap-3">
                    {selectedReport.recommendations.map((rec, idx) => (
                      <div key={idx} className="d-flex align-items-start gap-3 p-2 bg-white rounded border">
                        <div className="bg-success text-white rounded-circle d-flex align-items-center justify-content-center font-monospace fw-bold" style={{ width: '24px', height: '24px', flexShrink: 0 }}>
                          {idx + 1}
                        </div>
                        <div className="flex-grow-1">
                          <div className="d-flex justify-content-between align-items-center mb-1">
                            <span className="badge bg-secondary font-monospace" style={{ fontSize: '0.65rem' }}>{rec.category}</span>
                            <span className="small text-success fw-bold font-monospace">Potential score improvement: up to +{rec.expected_improvement} points</span>
                          </div>
                          <p className="small text-dark mb-0 fw-semibold">{rec.recommendation}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-success small fw-bold">
                    ✓ All data dimensions are fully optimal. No recommendations logged.
                  </div>
                )}
              </div>

              {/* Expanded Technical Details Accordion */}
              <div className="accordion accordion-flush bg-white border rounded" id="detailsAccordion">
                <div className="accordion-item bg-white">
                  <h2 className="accordion-header">
                    <button className="accordion-button bg-light text-success fw-bold small font-monospace py-2 collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne">
                      Technical Details
                    </button>
                  </h2>
                  <div id="collapseOne" className="accordion-collapse collapse" data-bs-parent="#detailsAccordion">
                    <div className="accordion-body font-monospace p-3 text-dark bg-white small">
                      <div className="row g-2 mb-3 text-secondary">
                        <div className="col-6"><strong>Classifier Model:</strong> {selectedReport.processing_trace?.model_used || 'Random Forest'}</div>
                        <div className="col-6"><strong>Prediction Class:</strong> {selectedReport.overall_prediction}</div>
                        <div className="col-6"><strong>Confidence Level:</strong> {(selectedReport.confidence_score * 100).toFixed(1)}%</div>
                        <div className="col-6"><strong>Explanation Method:</strong> {selectedReport.explainer_name} v{selectedReport.explainer_version}</div>
                        <div className="col-6"><strong>Calculation Time:</strong> {selectedReport.processing_trace?.explanation_time_ms ?? 0.0} ms</div>
                        <div className="col-6"><strong>Cache hit ratio:</strong> {cacheStats ? `${(cacheStats.ratio * 100).toFixed(1)}%` : '100%'}</div>
                      </div>
                      
                      <hr className="my-2 border-secondary" />
                      
                      <h6 className="fw-bold mb-2">SHAP Feature Contributions</h6>
                      <div className="d-flex flex-column gap-2 mb-3">
                        {selectedReport.top_positive_features?.map((item, idx) => (
                          <div key={idx}>
                            <div className="d-flex justify-content-between text-secondary mb-1" style={{ fontSize: '0.7rem' }}>
                              <span>{item.feature}</span>
                              <span className="text-success">+{item.value.toFixed(4)}</span>
                            </div>
                            <div className="progress bg-light" style={{ height: '4px' }}>
                              <div className="progress-bar bg-success" style={{ width: `${item.percentage}%` }}></div>
                            </div>
                          </div>
                        ))}
                        {selectedReport.top_negative_features?.map((item, idx) => (
                          <div key={idx}>
                            <div className="d-flex justify-content-between text-secondary mb-1" style={{ fontSize: '0.7rem' }}>
                              <span>{item.feature}</span>
                              <span className="text-danger">-{item.value.toFixed(4)}</span>
                            </div>
                            <div className="progress bg-light" style={{ height: '4px' }}>
                              <div className="progress-bar bg-danger" style={{ width: `${item.percentage}%` }}></div>
                            </div>
                          </div>
                        ))}
                      </div>

                      <hr className="my-2 border-secondary" />
                      <span className="text-secondary small d-block mb-1">Trace Audit JSON:</span>
                      <pre className="text-dark mb-0 p-2 bg-light rounded" style={{ maxHeight: '150px', overflowY: 'auto', fontSize: '0.7rem' }}>
                        {JSON.stringify(selectedReport.processing_trace, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          ) : (
            <div className="d-flex flex-column justify-content-center align-items-center flex-grow-1 text-center text-muted py-5">
              <svg width="64" height="64" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mb-3 text-success opacity-50">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="fw-bold text-dark fs-5 mb-1">Awaiting Report Selection</p>
              <p className="small text-secondary px-4">Select an item from the logs list on the left to review the dynamic quality breakdown scorecard, drivers checklist, and recommended fixes.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DataQualityExplainability;
