import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

// ----------------------------------------------------------------------
// CHART 1: Before vs After — Vertical Bar Chart
// ----------------------------------------------------------------------
const VerticalBarChart = ({ baselineRate, scenarioRate }) => {
  const maxVal = Math.max(20, Math.ceil((Math.max(baselineRate, scenarioRate) + 5) / 5) * 5);
  const chartHeight = 180;
  const chartWidth = 320;
  
  const baseBarHeight = (baselineRate / maxVal) * chartHeight;
  const scenBarHeight = (scenarioRate / maxVal) * chartHeight;

  const isLower = scenarioRate <= baselineRate;

  return (
    <div className="d-flex flex-column align-items-center w-100">
      <svg width="100%" height="240" viewBox={`0 0 ${chartWidth} 240`} preserveAspectRatio="xMidYMid meet">
        {/* Y-Axis Grid Lines & Labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
          const val = Math.round(maxVal * (1 - ratio));
          const y = 30 + ratio * chartHeight;
          return (
            <g key={idx}>
              <line x1="45" y1={y} x2={chartWidth - 15} y2={y} stroke="#e2e8f0" strokeDasharray="3 3" />
              <text x="38" y={y + 4} textAnchor="end" fontSize="11" fill="#64748b" fontFamily="monospace">
                {val}%
              </text>
            </g>
          );
        })}

        {/* X-Axis Base Line */}
        <line x1="45" y1={30 + chartHeight} x2={chartWidth - 15} y2={30 + chartHeight} stroke="#94a3b8" strokeWidth="1.5" />

        {/* Bar 1: Before Policy */}
        <g>
          <rect
            x="85"
            y={30 + chartHeight - baseBarHeight}
            width="55"
            height={baseBarHeight}
            fill="#64748b"
            rx="4"
          />
          <text
            x="112"
            y={Math.max(20, 30 + chartHeight - baseBarHeight - 8)}
            textAnchor="middle"
            fontSize="13"
            fontWeight="bold"
            fill="#334155"
            fontFamily="monospace"
          >
            {baselineRate}%
          </text>
          <text x="112" y={30 + chartHeight + 20} textAnchor="middle" fontSize="12" fontWeight="600" fill="#475569">
            Before Policy
          </text>
        </g>

        {/* Bar 2: After Policy */}
        <g>
          <rect
            x="205"
            y={30 + chartHeight - scenBarHeight}
            width="55"
            height={scenBarHeight}
            fill={isLower ? "#10b981" : "#ef4444"}
            rx="4"
          />
          <text
            x="232"
            y={Math.max(20, 30 + chartHeight - scenBarHeight - 8)}
            textAnchor="middle"
            fontSize="13"
            fontWeight="bold"
            fill={isLower ? "#047857" : "#b91c1c"}
            fontFamily="monospace"
          >
            {scenarioRate}%
          </text>
          <text x="232" y={30 + chartHeight + 20} textAnchor="middle" fontSize="12" fontWeight="600" fill="#475569">
            After Policy
          </text>
        </g>
      </svg>
    </div>
  );
};

// ----------------------------------------------------------------------
// CHART 2: Employee Risk — Side-by-Side SVG Donut Charts
// ----------------------------------------------------------------------
const SingleDonut = ({ title, count, total, color, label }) => {
  const pct = total > 0 ? (count / total) * 100 : 0;
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;

  return (
    <div className="d-flex flex-column align-items-center p-2">
      <div className="fw-bold text-dark mb-2 small text-uppercase">{title}</div>
      <div className="position-relative d-flex align-items-center justify-content-center" style={{ width: '120px', height: '120px' }}>
        <svg width="120" height="120" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={radius} fill="transparent" stroke="#e2e8f0" strokeWidth="12" />
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="transparent"
            stroke={color}
            strokeWidth="12"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            transform="rotate(-90 50 50)"
          />
        </svg>
        <div className="position-absolute text-center">
          <div className="fw-bold fs-5 leading-none" style={{ color }}>{count}</div>
          <div className="text-secondary extra-small font-monospace">{pct.toFixed(1)}%</div>
        </div>
      </div>
      <div className="mt-2 text-center">
        <span className="badge font-monospace" style={{ backgroundColor: color + '20', color: color, border: `1px solid ${color}40` }}>
          {count} {label}
        </span>
        <div className="text-muted extra-small mt-1">out of {total.toLocaleString()} total</div>
      </div>
    </div>
  );
};

const SideBySideDonutChart = ({ totalPop, baseHighRisk, scenHighRisk }) => {
  return (
    <div className="row g-3 justify-content-center align-items-center w-100">
      <div className="col-6 col-md-5">
        <SingleDonut
          title="BEFORE POLICY"
          count={baseHighRisk}
          total={totalPop}
          color="#64748b"
          label="Higher Risk"
        />
      </div>
      <div className="col-6 col-md-5">
        <SingleDonut
          title="AFTER POLICY"
          count={scenHighRisk}
          total={totalPop}
          color={scenHighRisk <= baseHighRisk ? "#10b981" : "#ef4444"}
          label="Higher Risk"
        />
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------
// CHART 3: Policy Factors — Horizontal SHAP Bar Chart
// ----------------------------------------------------------------------
const HorizontalSHAPChart = ({ topNegative, topPositive }) => {
  const allShaps = [
    ...topNegative.map(f => Math.abs(f.shap_value || 0)),
    ...topPositive.map(f => Math.abs(f.shap_value || 0))
  ];
  const maxShap = Math.max(0.05, ...allShaps);

  return (
    <div className="row g-4 w-100">
      <div className="col-md-6">
        <div className="p-3 bg-light rounded-3 border border-success border-opacity-25 h-100">
          <h6 className="fw-bold text-success mb-3 d-flex align-items-center gap-1 fs-6">
            <i className="bi bi-arrow-down-circle-fill text-success"></i> Factors linked with lower predicted risk
          </h6>
          <div className="d-flex flex-column gap-3">
            {topNegative.length > 0 ? (
              topNegative.map((item, idx) => {
                const absVal = Math.abs(item.shap_value || 0);
                const barWidth = Math.min(100, Math.max(8, (absVal / maxShap) * 100));
                return (
                  <div key={idx}>
                    <div className="d-flex justify-content-between small font-semibold text-dark mb-1">
                      <span>{item.feature} {item.value !== null ? `(${String(item.value)})` : ''}</span>
                      <span className="font-monospace text-success">{item.shap_value}</span>
                    </div>
                    <div className="progress" style={{ height: '14px', backgroundColor: '#e2e8f0' }}>
                      <div className="progress-bar bg-success rounded-pill" role="progressbar" style={{ width: `${barWidth}%` }}></div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-muted small">No significant risk-reducing factors identified.</div>
            )}
          </div>
        </div>
      </div>

      <div className="col-md-6">
        <div className="p-3 bg-light rounded-3 border border-danger border-opacity-25 h-100">
          <h6 className="fw-bold text-danger mb-3 d-flex align-items-center gap-1 fs-6">
            <i className="bi bi-arrow-up-circle-fill text-danger"></i> Factors linked with higher predicted risk
          </h6>
          <div className="d-flex flex-column gap-3">
            {topPositive.length > 0 ? (
              topPositive.map((item, idx) => {
                const absVal = Math.abs(item.shap_value || 0);
                const barWidth = Math.min(100, Math.max(8, (absVal / maxShap) * 100));
                return (
                  <div key={idx}>
                    <div className="d-flex justify-content-between small font-semibold text-dark mb-1">
                      <span>{item.feature} {item.value !== null ? `(${String(item.value)})` : ''}</span>
                      <span className="font-monospace text-danger">+{item.shap_value}</span>
                    </div>
                    <div className="progress" style={{ height: '14px', backgroundColor: '#e2e8f0' }}>
                      <div className="progress-bar bg-danger rounded-pill" role="progressbar" style={{ width: `${barWidth}%` }}></div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-muted small">No significant risk-increasing factors identified.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------
// EMPLOYEE RISK LIST SECTION WITH TREESHAP REASONS & CLIENT-SIDE PAGINATION
// ----------------------------------------------------------------------
const EmployeeRiskListSection = ({ riskList }) => {
  const [activeTab, setActiveTab] = useState('before_policy');
  const [expandedEmpIds, setExpandedEmpIds] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 25;

  if (!riskList) return null;

  const toggleExpandFactors = (empId) => {
    setExpandedEmpIds(prev => {
      const next = new Set(prev);
      if (next.has(empId)) next.delete(empId);
      else next.add(empId);
      return next;
    });
  };

  const handleTabChange = (cat) => {
    setActiveTab(cat);
    setCurrentPage(1);
  };

  const handleSearchChange = (val) => {
    setSearchQuery(val);
    setCurrentPage(1);
  };

  const rawEmployees = riskList[activeTab] || [];
  const filteredEmployees = rawEmployees.filter(e => 
    String(e.employee_id).includes(searchQuery) ||
    (e.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (e.department || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (e.designation || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalPages = Math.max(1, Math.ceil(filteredEmployees.length / itemsPerPage));
  const validCurrentPage = Math.min(currentPage, totalPages);
  const startIdx = (validCurrentPage - 1) * itemsPerPage;
  const pageEmployees = filteredEmployees.slice(startIdx, startIdx + itemsPerPage);

  const getTabLabel = (cat) => {
    switch(cat) {
      case 'before_policy': return `Before Policy (${riskList.before_policy?.length || 0})`;
      case 'after_policy': return `After Policy (${riskList.after_policy?.length || 0})`;
      case 'risk_reduced': return `Risk Reduced (${riskList.risk_reduced?.length || 0})`;
      case 'still_high_risk': return `Still Higher Risk (${riskList.still_high_risk?.length || 0})`;
      case 'newly_high_risk': return `Newly Higher Risk (${riskList.newly_high_risk?.length || 0})`;
      default: return cat;
    }
  };

  return (
    <div className="card shadow-sm border border-secondary border-opacity-25 bg-white rounded-3">
      <div className="card-header bg-white border-bottom border-secondary border-opacity-25 py-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div>
          <h5 className="fw-bold text-dark mb-0 d-flex align-items-center gap-2">
            <i className="bi bi-person-lines-fill text-primary"></i> Employee Risk List — IBM HR Dataset
          </h5>
          <small className="text-secondary">These predictions are generated for the 1,470 employees in the IBM HR dataset used by the trained model. They are not predictions for the separate Employee Directory dataset.</small>
        </div>
        <div className="w-auto">
          <input
            type="text"
            className="form-control form-control-sm bg-light text-dark border-secondary font-medium"
            placeholder="Search IBM employee number, job role, department..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            style={{ width: '280px' }}
          />
        </div>
      </div>

      <div className="card-body p-4">
        {/* Category Tabs */}
        <ul className="nav nav-tabs border-secondary border-opacity-25 mb-3 font-medium">
          {['before_policy', 'after_policy', 'risk_reduced', 'still_high_risk', 'newly_high_risk'].map(cat => (
            <li className="nav-item" key={cat}>
              <button
                className={`nav-link bg-transparent border-0 border-bottom text-dark py-2 px-3 ${activeTab === cat ? 'border-primary border-2 fw-bold text-primary' : 'text-secondary'}`}
                onClick={() => handleTabChange(cat)}
              >
                {getTabLabel(cat)}
              </button>
            </li>
          ))}
        </ul>

        {/* Note Disclaimer */}
        <div className="alert alert-light border border-secondary border-opacity-25 p-2.5 px-3 rounded-3 small text-secondary mb-3">
          <i className="bi bi-info-circle me-1.5 text-info fs-6"></i>
          <strong>Notice:</strong> The model predicts these IBM HR records as higher attrition risk under the selected scenario. These are model-based predictions from historical employee data; they do not guarantee that an employee will leave.
        </div>

        {/* Employee Cards List */}
        <div className="d-flex flex-column gap-3 mb-3" style={{ minHeight: '320px' }}>
          {pageEmployees.length > 0 ? (
            pageEmployees.map((emp) => {
              const isExpanded = expandedEmpIds.has(emp.employee_id);
              const isRiskReduced = activeTab === 'risk_reduced';

              return (
                <div key={emp.employee_id} className="card border border-secondary border-opacity-25 bg-white p-3 rounded-3 shadow-xs">
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <div>
                      <div className="d-flex align-items-center gap-2 flex-wrap">
                        <h6 className="fw-bold text-dark mb-0">{emp.name}</h6>
                        <span className="badge bg-light text-dark border font-monospace">ID: #{emp.employee_id}</span>
                        <span className="badge bg-secondary-subtle text-dark">{emp.department}</span>
                        <span className="badge bg-info-subtle text-info border border-info-subtle extra-small">Prediction source: IBM HR dataset</span>
                      </div>
                      <small className="text-secondary font-medium">{emp.designation}</small>
                    </div>

                    <div className="text-end">
                      {isRiskReduced ? (
                        <div>
                          <span className="badge bg-success font-monospace fs-6 px-2 py-1">
                            {emp.baseline_risk_pct}% → {emp.scenario_risk_pct}% ({emp.risk_change_pts} pts)
                          </span>
                        </div>
                      ) : (
                        <div>
                          <span className={`badge ${emp.risk_probability >= 0.5 ? 'bg-danger' : 'bg-success'} font-monospace fs-6 px-2 py-1`}>
                            {activeTab === 'before_policy' ? `${emp.baseline_risk_pct}% Risk` : `${emp.scenario_risk_pct || Math.round(emp.risk_probability * 100)}% Risk`}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Plain English Reason Box */}
                  <div className="p-2.5 rounded bg-light border border-secondary border-opacity-25 mb-2">
                    <div className="extra-small fw-bold text-secondary text-uppercase mb-1">
                      {activeTab === 'risk_reduced' ? 'What changed' : (activeTab === 'still_high_risk' ? 'Why risk remains high' : 'Why this employee is at higher risk')}
                    </div>
                    <div className="small text-dark fw-medium leading-normal">
                      {emp.reason}
                    </div>
                  </div>

                  {/* Expandable View Factors Button */}
                  <div className="d-flex justify-content-between align-items-center pt-1">
                    <button
                      className="btn btn-sm btn-link text-decoration-none p-0 text-primary fw-bold extra-small"
                      onClick={() => toggleExpandFactors(emp.employee_id)}
                    >
                      {isExpanded ? '▲ Hide factors' : '▼ View factors'}
                    </button>
                  </div>

                  {/* Expanded Top Contributing SHAP Factors */}
                  {isExpanded && (
                    <div className="mt-2 pt-2 border-top border-secondary border-opacity-25">
                      <div className="extra-small fw-bold text-secondary text-uppercase mb-2">Top Contributing Model Factors</div>
                      <div className="d-flex flex-wrap gap-2">
                        {emp.risk_reasons?.map((f, fIdx) => (
                          <span
                            key={fIdx}
                            className={`badge font-monospace py-1 px-2 ${f.direction === 'increases_risk' ? 'bg-danger-subtle text-danger border border-danger-subtle' : 'bg-success-subtle text-success border border-success-subtle'}`}
                          >
                            {f.direction === 'increases_risk' ? '↑' : '↓'} {f.clean_factor || f.factor} {f.value !== null ? `(${String(f.value)})` : ''} ({f.contribution > 0 ? `+${f.contribution}` : f.contribution})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <div className="text-center py-4 text-secondary font-monospace border rounded bg-light">
              No employee records match the selected filter.
            </div>
          )}
        </div>

        {/* Pagination Bar */}
        {filteredEmployees.length > 0 && (
          <div className="d-flex flex-wrap justify-content-between align-items-center pt-2 border-top border-secondary border-opacity-25 gap-2">
            <div className="small text-secondary font-medium">
              Showing <strong>{startIdx + 1}</strong>–<strong>{Math.min(startIdx + itemsPerPage, filteredEmployees.length)}</strong> of <strong>{filteredEmployees.length}</strong> records
            </div>

            <div className="d-flex gap-1 align-items-center">
              <button
                className="btn btn-sm btn-outline-secondary px-2.5 py-1"
                disabled={validCurrentPage <= 1}
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              >
                &laquo; Previous
              </button>

              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter(p => p === 1 || p === totalPages || Math.abs(p - validCurrentPage) <= 1)
                .reduce((acc, p, idx, arr) => {
                  if (idx > 0 && p - arr[idx - 1] > 1) acc.push('...');
                  acc.push(p);
                  return acc;
                }, [])
                .map((item, pIdx) => item === '...' ? (
                  <span key={`ellipsis-${pIdx}`} className="px-1 text-muted small">...</span>
                ) : (
                  <button
                    key={item}
                    className={`btn btn-sm ${item === validCurrentPage ? 'btn-primary fw-bold' : 'btn-outline-secondary'} px-2.5 py-1`}
                    onClick={() => setCurrentPage(item)}
                  >
                    {item}
                  </button>
                ))
              }

              <button
                className="btn btn-sm btn-outline-secondary px-2.5 py-1"
                disabled={validCurrentPage >= totalPages}
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              >
                Next &raquo;
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};


// ----------------------------------------------------------------------
// MAIN CONTAINER PAGE COMPONENT
// ----------------------------------------------------------------------
const PolicyImpactSimulator = () => {
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [configError, setConfigError] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);

  // Dedicated Policy Assistant Modal/Drawer State
  const [showAssistant, setShowAssistant] = useState(false);
  const [assistantMessages, setAssistantMessages] = useState([
    { sender: 'assistant', text: 'Hello! I am your Policy Assistant. I can help explain this workforce simulation, the predicted attrition changes, employee-level risk reasons, or the main factors driving the result. What would you like to know?' }
  ]);
  const [inputMsg, setInputMsg] = useState('');
  const [sendingAssistant, setSendingAssistant] = useState(false);

  // Form State for Policy Settings
  const [policyParams, setPolicyParams] = useState({
    OverTime: 'No',
    TrainingTimesLastYear: 3,
    WorkLifeBalance: 3,
    JobSatisfaction: 3,
    JobInvolvement: 3,
    PercentSalaryHike: 15,
    StockOptionLevel: 1
  });

  // 1. Fetch backend configuration on mount
  const fetchConfig = async () => {
    setLoadingConfig(true);
    setConfigError(null);
    try {
      const res = await client.get('policy-simulator/config/');
      setConfig(res.data);
      if (res.data.approved_policy_variables) {
        const approved = res.data.approved_policy_variables;
        const initialParams = {};
        Object.keys(approved).forEach(key => {
          const spec = approved[key];
          if (spec.data_type === 'categorical') {
            initialParams[key] = spec.allowed_values?.[0] || 'No';
          } else if (spec.data_type === 'integer' || spec.data_type === 'numerical') {
            const min = spec.min_val !== undefined ? spec.min_val : 0;
            const max = spec.max_val !== undefined ? spec.max_val : 10;
            initialParams[key] = Math.round((min + max) / 2);
          }
        });
        setPolicyParams(prev => ({ ...initialParams, ...prev }));
      }
    } catch (err) {
      console.error("Failed to load policy configuration:", err);
      setConfigError(err.response?.data?.error || err.message || "Failed to retrieve policy configuration from backend.");
    } finally {
      setLoadingConfig(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleInputChange = (field, value) => {
    setPolicyParams(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const runSimulation = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await client.post('policy-simulator/simulate/', {
        policy_changes: policyParams
      });

      const data = response.data;
      if (!data.success) {
        throw new Error(data.message || (data.errors ? data.errors.join(', ') : 'Simulation failed.'));
      }

      setSimulationResult(data);
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.errors?.[0] || err.message || 'Simulation execution failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!loadingConfig) {
      runSimulation();
    }
  }, [loadingConfig]);

  // Handle Policy Assistant Message Submission
  const handleSendAssistantMessage = async (e) => {
    e.preventDefault();
    if (!inputMsg.trim() || sendingAssistant) return;

    const userText = inputMsg.trim();
    setInputMsg('');
    setAssistantMessages(prev => [...prev, { sender: 'user', text: userText }]);
    setSendingAssistant(true);

    try {
      const res = await client.post('policy-simulator/assistant/', {
        message: userText,
        simulation_context: simulationResult
      });

      const reply = res.data?.reply || "I analyzed the simulation metrics. Let me know if you need further clarification.";
      setAssistantMessages(prev => [...prev, { sender: 'assistant', text: reply }]);
    } catch (err) {
      setAssistantMessages(prev => [...prev, { sender: 'assistant', text: "I'm having trouble connecting to the assistant right now. Please try again." }]);
    } finally {
      setSendingAssistant(false);
    }
  };

  if (loadingConfig) {
    return (
      <div className="p-5 text-center bg-white rounded-3 border border-secondary border-opacity-25 shadow-sm m-3">
        <div className="spinner-border text-success mb-3" role="status" style={{ width: '3rem', height: '3rem' }}></div>
        <h5 className="fw-bold text-dark">Loading Policy Simulator...</h5>
        <p className="text-secondary small mb-0">Retrieving workplace policy options from the server.</p>
      </div>
    );
  }

  const baselineRate = simulationResult?.baseline?.predicted_attrition_rate_pct || 14.15;
  const scenarioRate = simulationResult?.scenario?.predicted_attrition_rate_pct || 3.74;
  const baseHighRisk = simulationResult?.baseline?.predicted_attrition_count || 208;
  const scenHighRisk = simulationResult?.scenario?.predicted_attrition_count || 55;
  const totalPop = simulationResult?.simulation_summary?.population_evaluated || 1470;
  const countChange = Math.abs(simulationResult?.impact_differential?.estimated_attrition_count_change || 153);
  const diffPts = simulationResult?.impact_differential?.percentage_point_change || -10.41;

  const topNeg = simulationResult?.explainability?.sample_instance_explanation?.top_negative_factors || [];
  const topPos = simulationResult?.explainability?.sample_instance_explanation?.top_positive_factors || [];

  return (
    <div className="p-3" style={{ backgroundColor: '#f8fafc', color: '#1e293b', fontFamily: 'Inter, sans-serif' }}>
      {/* Header Bar */}
      <div className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom border-secondary border-opacity-25">
        <div>
          <h3 className="fw-bold text-dark mb-1 d-flex align-items-center gap-2">
            <i className="bi bi-sliders text-success"></i> Employee Workforce Policy Impact Simulator
          </h3>
          <p className="text-secondary small mb-0 fs-6">
            See how proposed employee policies may change predicted workforce attrition.
          </p>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-sm btn-outline-secondary fw-semibold" onClick={() => navigate('/')}>
            ← Back to Dashboard
          </button>
          <button 
            className="btn btn-sm btn-success fw-bold text-white d-flex align-items-center gap-1 shadow-sm"
            onClick={() => setShowAssistant(true)}
          >
            <i className="bi bi-chat-dots-fill"></i> Ask Policy Assistant
          </button>
        </div>
      </div>

      {configError && (
        <div className="alert alert-danger border border-danger-subtle d-flex justify-content-between align-items-center mb-4 shadow-sm">
          <div className="d-flex align-items-center">
            <i className="bi bi-exclamation-triangle-fill text-danger me-2 fs-5"></i>
            <span className="fw-semibold text-danger">{configError}</span>
          </div>
          <button className="btn btn-sm btn-outline-danger" onClick={fetchConfig}>Retry Connection</button>
        </div>
      )}

      {error && (
        <div className="alert alert-danger border border-danger-subtle d-flex align-items-center mb-4 shadow-sm" role="alert">
          <i className="bi bi-exclamation-triangle-fill text-danger me-2 fs-5"></i>
          <div className="fw-semibold text-danger">{error}</div>
        </div>
      )}

      <div className="row g-4">
        {/* Left Column: Policy Settings */}
        <div className="col-lg-4">
          <div className="card shadow-sm border border-secondary border-opacity-25 bg-white h-100 rounded-3">
            <div className="card-header bg-white border-bottom border-secondary border-opacity-25 py-3">
              <h5 className="fw-bold text-dark mb-0 d-flex align-items-center gap-2">
                <i className="bi bi-sliders2 text-success"></i> Policy Settings
              </h5>
              <small className="text-secondary">Adjust workplace policy options below</small>
            </div>
            <div className="card-body">
              {/* Dynamic Controls with Friendly Labels */}
              {config?.approved_policy_variables && Object.keys(config.approved_policy_variables).map(featKey => {
                const spec = config.approved_policy_variables[featKey];
                const val = policyParams[featKey] !== undefined ? policyParams[featKey] : (spec.data_type === 'categorical' ? 'No' : spec.min_val || 0);

                if (featKey === 'OverTime') {
                  return (
                    <div className="mb-3" key={featKey}>
                      <label className="form-label fw-bold text-dark small d-flex justify-content-between">
                        <span>How should overtime be handled?</span>
                        <span className="badge bg-success-subtle text-success">{val === 'No' ? 'Restricted' : 'Mandatory'}</span>
                      </label>
                      <select
                        className="form-select bg-white text-dark border-secondary font-medium"
                        value={val}
                        onChange={(e) => handleInputChange(featKey, e.target.value)}
                      >
                        <option value="No">No (Restricted / Zero Mandatory Overtime)</option>
                        <option value="Yes">Yes (Mandatory / Standard Overtime)</option>
                      </select>
                      <small className="text-secondary d-block mt-1">Restricting mandatory overtime or capping overtime assignments.</small>
                    </div>
                  );
                }

                if (featKey === 'TrainingTimesLastYear') {
                  return (
                    <div className="mb-3" key={featKey}>
                      <label className="form-label fw-bold text-dark small d-flex justify-content-between">
                        <span>Annual training programs</span>
                        <span className="text-success fw-bold">{val} programs/yr</span>
                      </label>
                      <input
                        type="range"
                        className="form-range"
                        min={spec.min_val ?? 0}
                        max={spec.max_val ?? 6}
                        value={val}
                        onChange={(e) => handleInputChange(featKey, parseInt(e.target.value))}
                      />
                      <small className="text-secondary d-block">Mandating annual skill development programs.</small>
                    </div>
                  );
                }

                if (featKey === 'WorkLifeBalance') {
                  return (
                    <div className="mb-3" key={featKey}>
                      <label className="form-label fw-bold text-dark small d-flex justify-content-between">
                        <span>Work-life balance support</span>
                        <span className="text-success fw-bold">Level {val}</span>
                      </label>
                      <select
                        className="form-select bg-white text-dark border-secondary font-medium"
                        value={val}
                        onChange={(e) => handleInputChange(featKey, parseInt(e.target.value))}
                      >
                        <option value="1">Level 1 - Low (Standard Hours)</option>
                        <option value="2">Level 2 - Moderate</option>
                        <option value="3">Level 3 - Good (Hybrid / Flexible)</option>
                        <option value="4">Level 4 - Best (Full Flexible & Remote)</option>
                      </select>
                      <small className="text-secondary d-block mt-1">Flexible work arrangements and wellness initiatives.</small>
                    </div>
                  );
                }

                if (featKey === 'JobSatisfaction') {
                  return (
                    <div className="mb-3" key={featKey}>
                      <label className="form-label fw-bold text-dark small d-flex justify-content-between">
                        <span>Job satisfaction support</span>
                        <span className="text-success fw-bold">Level {val}</span>
                      </label>
                      <select
                        className="form-select bg-white text-dark border-secondary font-medium"
                        value={val}
                        onChange={(e) => handleInputChange(featKey, parseInt(e.target.value))}
                      >
                        <option value="1">Level 1 - Low</option>
                        <option value="2">Level 2 - Medium</option>
                        <option value="3">Level 3 - High</option>
                        <option value="4">Level 4 - Very High</option>
                      </select>
                      <small className="text-secondary d-block mt-1">Role alignment and workplace environment support.</small>
                    </div>
                  );
                }

                if (featKey === 'JobInvolvement') {
                  return (
                    <div className="mb-3" key={featKey}>
                      <label className="form-label fw-bold text-dark small d-flex justify-content-between">
                        <span>Employee involvement</span>
                        <span className="text-success fw-bold">Level {val}</span>
                      </label>
                      <select
                        className="form-select bg-white text-dark border-secondary font-medium"
                        value={val}
                        onChange={(e) => handleInputChange(featKey, parseInt(e.target.value))}
                      >
                        <option value="1">Level 1 - Low</option>
                        <option value="2">Level 2 - Medium</option>
                        <option value="3">Level 3 - High</option>
                        <option value="4">Level 4 - Very High</option>
                      </select>
                      <small className="text-secondary d-block mt-1">Project ownership and recognition programs.</small>
                    </div>
                  );
                }

                if (featKey === 'PercentSalaryHike') {
                  return (
                    <div className="mb-3" key={featKey}>
                      <label className="form-label fw-bold text-dark small d-flex justify-content-between">
                        <span>Annual salary increase</span>
                        <span className="text-success fw-bold">{val}%</span>
                      </label>
                      <input
                        type="range"
                        className="form-range"
                        min={spec.min_val ?? 11}
                        max={spec.max_val ?? 25}
                        value={val}
                        onChange={(e) => handleInputChange(featKey, parseInt(e.target.value))}
                      />
                      <small className="text-secondary d-block">Adjusting compensation and salary increase policies.</small>
                    </div>
                  );
                }

                if (featKey === 'StockOptionLevel') {
                  return (
                    <div className="mb-3" key={featKey}>
                      <label className="form-label fw-bold text-dark small d-flex justify-content-between">
                        <span>Employee stock option level</span>
                        <span className="text-success fw-bold">Level {val}</span>
                      </label>
                      <select
                        className="form-select bg-white text-dark border-secondary font-medium"
                        value={val}
                        onChange={(e) => handleInputChange(featKey, parseInt(e.target.value))}
                      >
                        <option value="0">Level 0 - No Stock Options</option>
                        <option value="1">Level 1 - Standard Equity Grants</option>
                        <option value="2">Level 2 - Enhanced Equity Grants</option>
                        <option value="3">Level 3 - Executive Equity Tier</option>
                      </select>
                      <small className="text-secondary d-block mt-1">Equity grant eligibility and stock incentive plans.</small>
                    </div>
                  );
                }

                return null;
              })}

              <button
                className="btn btn-success w-100 fw-bold py-2 mt-3 text-white shadow-sm d-flex align-items-center justify-content-center gap-2"
                onClick={runSimulation}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status"></span>
                    Simulating Scenario...
                  </>
                ) : (
                  <>
                    <i className="bi bi-play-circle-fill"></i> Simulate Policy
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: 3 Visual Charts + Employee Risk List */}
        <div className="col-lg-8">
          {loading && !simulationResult && (
            <div className="text-center py-5 bg-white border border-secondary border-opacity-25 rounded-3 shadow-sm">
              <div className="spinner-border text-success mb-3" role="status" style={{ width: '3rem', height: '3rem' }}></div>
              <h5 className="fw-bold text-dark">Simulating Policy Impact...</h5>
              <p className="text-secondary small mb-0">Calculating workforce predictions for the selected policy settings.</p>
            </div>
          )}

          {simulationResult && (
            <div className="d-flex flex-column gap-4">

              {/* 4 TOP SUMMARY CARDS */}
              <div className="row g-3">
                <div className="col-6 col-md-3">
                  <div className="card border border-secondary border-opacity-25 bg-white p-3 shadow-sm rounded-3 h-100">
                    <div className="text-secondary small fw-bold text-uppercase mb-1">Employees Checked</div>
                    <div className="fs-3 fw-bold text-dark">{totalPop.toLocaleString()}</div>
                    <small className="text-muted extra-small">Employees in simulation</small>
                  </div>
                </div>

                <div className="col-6 col-md-3">
                  <div className="card border border-secondary border-opacity-25 bg-white p-3 shadow-sm rounded-3 h-100">
                    <div className="text-secondary small fw-bold text-uppercase mb-1">Current Predicted Attrition</div>
                    <div className="fs-3 fw-bold text-dark">{baselineRate}%</div>
                    <small className="text-muted extra-small fw-semibold">{baseHighRisk} employees</small>
                  </div>
                </div>

                <div className="col-6 col-md-3">
                  <div className="card border border-primary border-opacity-50 bg-white p-3 shadow-sm rounded-3 h-100">
                    <div className="text-primary small fw-bold text-uppercase mb-1">After Policy Change</div>
                    <div className="fs-3 fw-bold text-primary">{scenarioRate}%</div>
                    <small className="text-muted extra-small fw-semibold">{scenHighRisk} employees</small>
                  </div>
                </div>

                <div className="col-6 col-md-3">
                  <div className="card border border-secondary border-opacity-25 bg-white p-3 shadow-sm rounded-3 h-100">
                    <div className="text-secondary small fw-bold text-uppercase mb-1">Change</div>
                    <div className={`fs-3 fw-bold ${diffPts <= 0 ? 'text-success' : 'text-danger'}`}>
                      {diffPts > 0 ? '+' : ''}{diffPts} pts
                    </div>
                    <small className="text-muted extra-small">Predicted reduction</small>
                  </div>
                </div>
              </div>

              {/* CHART 1: BEFORE VS AFTER — VERTICAL BAR CHART */}
              <div className="card shadow-sm border border-secondary border-opacity-25 bg-white rounded-3">
                <div className="card-header bg-white border-bottom border-secondary border-opacity-25 py-3 d-flex justify-content-between align-items-center">
                  <div>
                    <h5 className="fw-bold text-dark mb-0 d-flex align-items-center gap-2">
                      <i className="bi bi-bar-chart-line-fill text-primary"></i> 1. Predicted Attrition (Before vs After)
                    </h5>
                    <small className="text-secondary">Question: Did the policy change the predicted attrition?</small>
                  </div>
                  <span className="badge bg-light text-dark border font-monospace">RESULT</span>
                </div>
                <div className="card-body p-4">
                  <VerticalBarChart baselineRate={baselineRate} scenarioRate={scenarioRate} />
                  
                  <div className="alert alert-info border border-info border-opacity-25 bg-white p-3 rounded-3 shadow-sm mb-0 mt-3">
                    <div className="d-flex align-items-start gap-2">
                      <i className="bi bi-info-circle-fill text-info fs-5 mt-1"></i>
                      <div>
                        <h6 className="fw-bold text-dark mb-1">What happened?</h6>
                        <p className="text-dark small mb-0">
                          The model predicts lower employee attrition after applying the selected policy. The predicted rate changes from <strong>{baselineRate}%</strong> to <strong>{scenarioRate}%</strong>.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* CHART 2: EMPLOYEE RISK — DONUT CHART (SIDE-BY-SIDE) */}
              <div className="card shadow-sm border border-secondary border-opacity-25 bg-white rounded-3">
                <div className="card-header bg-white border-bottom border-secondary border-opacity-25 py-3 d-flex justify-content-between align-items-center">
                  <div>
                    <h5 className="fw-bold text-dark mb-0 d-flex align-items-center gap-2">
                      <i className="bi bi-pie-chart-fill text-info"></i> 2. Employees at Higher Risk
                    </h5>
                    <small className="text-secondary">Question: How many employees are predicted to be at higher risk?</small>
                  </div>
                  <span className="badge bg-light text-dark border font-monospace">IMPACT</span>
                </div>
                <div className="card-body p-4">
                  <SideBySideDonutChart
                    totalPop={totalPop}
                    baseHighRisk={baseHighRisk}
                    scenHighRisk={scenHighRisk}
                  />

                  <div className="alert alert-info border border-info border-opacity-25 bg-white p-3 rounded-3 shadow-sm mb-0 mt-3">
                    <div className="d-flex align-items-start gap-2">
                      <i className="bi bi-info-circle-fill text-info fs-5 mt-1"></i>
                      <div>
                        <h6 className="fw-bold text-dark mb-1">What does this mean?</h6>
                        <p className="text-dark small mb-0">
                          Before the policy, <strong>{baseHighRisk}</strong> employees are predicted to be at higher risk. After the policy scenario, this falls to <strong>{scenHighRisk}</strong> employees (a net reduction of <strong>{countChange}</strong> employees predicted at higher risk).
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* CHART 3: POLICY FACTORS — HORIZONTAL BAR CHART */}
              <div className="card shadow-sm border border-secondary border-opacity-25 bg-white rounded-3">
                <div className="card-header bg-white border-bottom border-secondary border-opacity-25 py-3 d-flex justify-content-between align-items-center">
                  <div>
                    <h5 className="fw-bold text-dark mb-0 d-flex align-items-center gap-2">
                      <i className="bi bi-search text-warning"></i> 3. What Influenced the Prediction?
                    </h5>
                    <small className="text-secondary">Question: Which factors are influencing the prediction?</small>
                  </div>
                  <span className="badge bg-light text-dark border font-monospace">REASON</span>
                </div>
                <div className="card-body p-4">
                  <HorizontalSHAPChart topNegative={topNeg} topPositive={topPos} />

                  <div className="alert alert-info border border-info border-opacity-25 bg-white p-3 rounded-3 shadow-sm mb-0 mt-3">
                    <div className="d-flex align-items-start gap-2">
                      <i className="bi bi-info-circle-fill text-info fs-5 mt-1"></i>
                      <div>
                        <h6 className="fw-bold text-dark mb-1">Why did the prediction change?</h6>
                        <p className="text-dark small mb-0">
                          These are the employee factors that had the strongest influence on the model's prediction. The longer the bar, the stronger the model's influence.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* NEW SECTION: EMPLOYEE RISK LIST WITH TREESHAP REASONS */}
              {simulationResult.employee_risk_list && (
                <EmployeeRiskListSection riskList={simulationResult.employee_risk_list} />
              )}

              {/* SECTION: IMPORTANT DISCLAIMER */}
              <div className="alert alert-warning border border-warning-subtle bg-white p-3 rounded-3 shadow-sm mb-0">
                <div className="d-flex align-items-start gap-3">
                  <i className="bi bi-shield-exclamation text-warning fs-4 mt-1"></i>
                  <div>
                    <h6 className="fw-bold text-dark mb-1">Important Notice</h6>
                    <p className="text-dark small mb-0">
                      These results are predictions based on historical employee data. They show how the model estimates the workforce outcome under the selected policy settings. They do not guarantee what will happen in the real organization.
                    </p>
                  </div>
                </div>
              </div>

              {/* SECTION: COLLAPSIBLE TECHNICAL DETAILS */}
              <details className="bg-white p-3 rounded-3 border border-secondary border-opacity-25 shadow-sm">
                <summary className="fw-bold text-secondary cursor-pointer" style={{ cursor: 'pointer' }}>
                  ⚙️ Technical Details (Click to expand technical parameters)
                </summary>
                <div className="mt-3 pt-3 border-top border-secondary border-opacity-25 font-monospace extra-small text-dark">
                  <div className="row g-2">
                    <div className="col-md-6"><strong>Prediction Model:</strong> Random Forest (RandomForestClassifier v1.0.0)</div>
                    <div className="col-md-6"><strong>Explanation Method:</strong> TreeSHAP (shap.TreeExplainer)</div>
                    <div className="col-md-6"><strong>Training Dataset:</strong> IBM HR.csv</div>
                    <div className="col-md-6"><strong>Employees in Dataset:</strong> {totalPop.toLocaleString()}</div>
                    <div className="col-md-6"><strong>Model Version:</strong> {simulationResult.provenance?.model_version || '1.0.0'}</div>
                    <div className="col-md-6"><strong>Retraining Status:</strong> False (Zero Retraining Executed)</div>
                  </div>
                </div>
              </details>

            </div>
          )}
        </div>
      </div>

      {/* DEDICATED EMBEDDED POLICY ASSISTANT DRAWER / MODAL */}
      {showAssistant && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content bg-white border border-secondary shadow-lg rounded-3">
              <div className="modal-header bg-light border-bottom border-secondary py-3">
                <div className="d-flex align-items-center gap-2">
                  <div className="bg-success text-white rounded-circle p-2 d-flex align-items-center justify-content-center" style={{ width: '36px', height: '36px' }}>
                    <i className="bi bi-robot fs-5"></i>
                  </div>
                  <div>
                    <h5 className="fw-bold text-dark mb-0">Policy Assistant</h5>
                    <small className="text-secondary">Dedicated scenario helper • Powered by Local LLM</small>
                  </div>
                </div>
                <button type="button" className="btn-close" onClick={() => setShowAssistant(false)}></button>
              </div>

              <div className="modal-body p-3" style={{ maxHeight: '420px', overflowY: 'auto', backgroundColor: '#f8fafc' }}>
                <div className="alert alert-info py-2 px-3 mb-3 small border-0 font-medium">
                  💡 This assistant discusses the current simulation scenario ({policyParams.OverTime === 'No' ? 'No Overtime' : 'Mandatory Overtime'}, Salary Hike: {policyParams.PercentSalaryHike}%, Stock Options: Level {policyParams.StockOptionLevel}).
                </div>

                <div className="d-flex flex-column gap-3">
                  {assistantMessages.map((msg, idx) => (
                    <div key={idx} className={`d-flex ${msg.sender === 'user' ? 'justify-content-end' : 'justify-content-start'}`}>
                      <div 
                        className={`p-3 rounded-3 max-w-75 shadow-sm ${msg.sender === 'user' ? 'bg-success text-white' : 'bg-white text-dark border border-secondary border-opacity-25'}`}
                        style={{ maxWidth: '80%' }}
                      >
                        <div className="small font-medium">{msg.text}</div>
                      </div>
                    </div>
                  ))}
                  {sendingAssistant && (
                    <div className="d-flex justify-content-start">
                      <div className="bg-white p-3 rounded-3 border border-secondary border-opacity-25 text-secondary small d-flex align-items-center gap-2">
                        <span className="spinner-border spinner-border-sm text-success" role="status"></span>
                        Policy Assistant is typing...
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="modal-footer bg-white border-top border-secondary py-2">
                <form onSubmit={handleSendAssistantMessage} className="w-100 d-flex gap-2">
                  <input
                    type="text"
                    className="form-control bg-white text-dark border-secondary font-medium"
                    placeholder="Ask about this policy simulation..."
                    value={inputMsg}
                    onChange={(e) => setInputMsg(e.target.value)}
                    disabled={sendingAssistant}
                  />
                  <button type="submit" className="btn btn-success text-white fw-bold px-4" disabled={sendingAssistant || !inputMsg.trim()}>
                    Send
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default PolicyImpactSimulator;
