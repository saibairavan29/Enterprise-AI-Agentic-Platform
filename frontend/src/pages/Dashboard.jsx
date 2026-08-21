import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';
import ConflictConsole from './ConflictConsole';
import DataQualityExplainability from './DataQualityExplainability';
import EmployeeDirectory from './EmployeeDirectory';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const rowsPerPage = 10;
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'ingestion' | 'repository'
  
  // Pipeline Ingestion States
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [parserType, setParserType] = useState('auto');
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [resultTab, setResultTab] = useState('record'); // 'record' | 'metadata' | 'stages'

  // Knowledge Repository States
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [repoError, setRepoError] = useState('');
  const [repoSuccess, setRepoSuccess] = useState('');
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [selectedDocDetails, setSelectedDocDetails] = useState({
    records: [],
    versions: [],
    audit: []
  });
  const [activeDetailsTab, setActiveDetailsTab] = useState('records'); // 'records' | 'versions' | 'audit' | 'metadata'
  
  // Logical Repos & Viewer States
  const [uploadRepoType, setUploadRepoType] = useState('team'); // 'team' | 'personal'
  const [selectedRepoType, setSelectedRepoType] = useState('team'); // 'team' | 'personal'
  const [previewingDoc, setPreviewingDoc] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [csvPage, setCsvPage] = useState(1);
  const [activeExcelSheet, setActiveExcelSheet] = useState('');
  const [imageZoom, setImageZoom] = useState(100);
  
  // Generic Records Search States
  const [globalRecords, setGlobalRecords] = useState([]);
  const [loadingGlobalRecords, setLoadingGlobalRecords] = useState(false);
  const [searchField, setSearchField] = useState('');
  const [searchValue, setSearchValue] = useState('');
  const [searchContains, setSearchContains] = useState('');
  const [repoTabType, setRepoTabType] = useState('docs'); // 'docs' | 'search'

  // Inline Record Editing states
  const [editingRecordId, setEditingRecordId] = useState(null);
  const [editingDataJson, setEditingDataJson] = useState('');

  // Drag and drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setErrorMsg('');
      setResult(null);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMsg('');
      setResult(null);
    }
  };

  const handlePipelineSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setErrorMsg('Please select a file to ingest');
      return;
    }

    setProcessing(true);
    setErrorMsg('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('repository_type', uploadRepoType);
    if (parserType !== 'auto') {
      formData.append('parser_type', parserType);
    }

    try {
      const response = await client.post('ingestion/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data && response.data.success) {
        setResult(response.data.data);
      } else {
        setErrorMsg(response.data.message || 'Pipeline execution failed.');
      }
    } catch (err) {
      console.error(err);
      const data = err.response?.data;
      const msg = data?.message || data?.errors?.[0] || 'Pipeline processing crashed.';
      setErrorMsg(msg);
      if (data?.data) {
        setResult(data.data);
      }
    } finally {
      setProcessing(false);
    }
  };

  // Repository Operations
  const fetchDocuments = async () => {
    setLoadingDocs(true);
    setRepoError('');
    try {
      const res = await client.get('repository/documents/');
      const data = res.data.results || res.data.data || [];
      setDocuments(data);
    } catch (err) {
      setRepoError('Failed to fetch knowledge documents.');
    } finally {
      setLoadingDocs(false);
    }
  };

  const softDeleteDocument = async (docId) => {
    if (!window.confirm("Are you sure you want to soft delete this knowledge document? All associated records will be purged.")) {
      return;
    }
    try {
      await client.delete(`repository/documents/${docId}/`);
      setRepoSuccess('Document soft-deleted successfully.');
      setSelectedDoc(null);
      fetchDocuments();
    } catch (err) {
      setRepoError('Operator permissions insufficient or execution failed.');
    }
  };

  const fetchDocumentSubDetails = async (doc) => {
    setSelectedDoc(doc);
    setSelectedDocDetails({ records: [], versions: [], audit: [] });
    try {
      const [recRes, verRes, audRes] = await Promise.all([
        client.get(`repository/documents/${doc.id}/records/`),
        client.get(`repository/documents/${doc.id}/versions/`),
        client.get(`repository/documents/${doc.id}/audit/`)
      ]);
      setSelectedDocDetails({
        records: recRes.data.results || recRes.data.data || [],
        versions: verRes.data.results || verRes.data.data || [],
        audit: audRes.data.results || audRes.data.data || []
      });
    } catch (err) {
      setRepoError('Failed loading some document sub-elements.');
    }
  };

  const executeRecordsQuery = async () => {
    setLoadingGlobalRecords(true);
    setRepoError('');
    try {
      let params = [];
      if (searchField) params.push(`field=${encodeURIComponent(searchField)}`);
      if (searchValue) params.push(`value=${encodeURIComponent(searchValue)}`);
      if (searchContains) params.push(`contains=${encodeURIComponent(searchContains)}`);
      
      const queryStr = params.length ? `?${params.join('&')}` : '';
      const res = await client.get(`repository/records/${queryStr}`);
      setGlobalRecords(res.data.results || res.data.data || []);
    } catch (err) {
      setRepoError('Failed querying database canonical records.');
    } finally {
      setLoadingGlobalRecords(false);
    }
  };

  const handleUpdateRecord = async (recordId, isGlobal = false) => {
    try {
      const parsedData = JSON.parse(editingDataJson);
      await client.put(`repository/records/${recordId}/`, {
        canonical_data: parsedData
      });
      setRepoSuccess('Record fields updated successfully.');
      setEditingRecordId(null);
      if (isGlobal) {
        executeRecordsQuery();
      } else if (selectedDoc) {
        fetchDocumentSubDetails(selectedDoc);
      }
    } catch (err) {
      setRepoError(err.message || 'Validation failed. Ensure formatting represents correct JSON string.');
    }
  };

  const handleDeleteRecord = async (recordId, isGlobal = false) => {
    if (!window.confirm("Are you sure you want to permanently delete this canonical entry?")) {
      return;
    }
    try {
      await client.delete(`repository/records/${recordId}/`);
      setRepoSuccess('Record deleted from repository database.');
      if (isGlobal) {
        executeRecordsQuery();
      } else if (selectedDoc) {
        fetchDocumentSubDetails(selectedDoc);
      }
    } catch (err) {
      setRepoError('Operator permissions insufficient or target already removed.');
    }
  };

  const fetchFilePreview = async (doc) => {
    setPreviewingDoc(doc);
    setLoadingPreview(true);
    setPreviewError('');
    setPreviewData(null);
    setCsvPage(1);
    setActiveExcelSheet('');
    try {
      const ext = doc.title.split('.').pop().toLowerCase();
      
      if (['pdf', 'png', 'jpg', 'jpeg', 'webp'].includes(ext)) {
        const res = await client.get(`repository/documents/${doc.id}/view_file/`, {
          responseType: 'blob'
        });
        const blobUrl = URL.createObjectURL(res.data);
        setPreviewData({
          file_type: ['png', 'jpg', 'jpeg', 'webp'].includes(ext) ? 'image' : 'pdf',
          url: blobUrl
        });
      } else {
        const res = await client.get(`repository/documents/${doc.id}/view_file/`);
        const data = res.data.results || res.data.data || res.data;
        setPreviewData(data);
        if (data.file_type === 'excel' && data.sheets) {
          const sheetNames = Object.keys(data.sheets);
          if (sheetNames.length > 0) {
            setActiveExcelSheet(sheetNames[0]);
          }
        }
      }
    } catch (err) {
      console.error(err);
      setPreviewError('Failed to load file preview. Ensure operator holds view permissions.');
    } finally {
      setLoadingPreview(false);
    }
  };

  const downloadFileSecurely = async (doc) => {
    try {
      const res = await client.get(`repository/documents/${doc.id}/view_file/`, {
        responseType: 'blob'
      });
      const blobUrl = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = doc.title;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      alert('Secure download failed or unauthorized file access.');
    }
  };

  // Trigger loading documents list whenever Repository active view is selected
  useEffect(() => {
    if (activeTab === 'repository') {
      fetchDocuments();
    }
  }, [activeTab]);

  const getFailedStageName = () => {
    if (!result?.pipeline_result?.stage_execution) return null;
    for (const [stageName, info] of Object.entries(result.pipeline_result.stage_execution)) {
      if (info.status === 'FAILED') {
        return stageName;
      }
    }
    return null;
  };
  const failedStageName = getFailedStageName();

  return (
    <div className="container-fluid min-vh-100 p-0" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Top Navbar */}
      <nav className="navbar navbar-expand-lg border-bottom border-secondary py-3 px-4 glass-panel rounded-0">
        <div className="container-fluid">
          <div className="d-flex align-items-center gap-4">
            <span 
              className="navbar-brand text-gradient-glowing fw-bold fs-4 cursor-pointer mb-0 me-3" 
              onClick={() => setActiveTab('dashboard')}
              style={{ cursor: 'pointer' }}
            >
              Enterprise AI Platform
            </span>
            <div className="navbar-nav d-flex flex-row gap-3">
              <button 
                className={`btn btn-sm px-3 ${activeTab === 'employees' ? 'btn-premium-primary text-white' : 'btn-link text-secondary text-decoration-none'}`} 
                onClick={() => setActiveTab('employees')}
              >
                Employee Directory
              </button>
              <button 
                className={`btn btn-sm px-3 ${activeTab === 'repository' ? 'btn-premium-primary text-white' : 'btn-link text-secondary text-decoration-none'}`} 
                onClick={() => setActiveTab('repository')}
              >
                Enterprise Documents & Data
              </button>
              <button 
                className={`btn btn-sm px-3 ${activeTab === 'ingestion' ? 'btn-premium-primary text-white' : 'btn-link text-secondary text-decoration-none'}`} 
                onClick={() => setActiveTab('ingestion')}
              >
                Document Ingestion
              </button>
              <button 
                className={`btn btn-sm px-3 ${activeTab === 'explainability' ? 'btn-premium-primary text-white' : 'btn-link text-secondary text-decoration-none'}`} 
                onClick={() => setActiveTab('explainability')}
              >
                Data Quality Report
              </button>
              <button 
                className={`btn btn-sm px-3 ${activeTab === 'conflicts' ? 'btn-premium-primary text-white' : 'btn-link text-secondary text-decoration-none'}`} 
                onClick={() => setActiveTab('conflicts')}
              >
                Check Data Conflicts
              </button>
            </div>
          </div>
          <div className="d-flex align-items-center gap-3">
            <span className="badge bg-success py-2 px-3 text-uppercase font-monospace" style={{ fontSize: '0.75rem', letterSpacing: '1px' }}>
              Role: {user?.role}
            </span>
            <span className="text-secondary small fw-medium">Welcome, {user?.username}</span>
            <button onClick={logout} className="btn btn-premium-secondary btn-sm py-1 px-3">Logout</button>
          </div>
        </div>
      </nav>

      {/* Main Container */}
      <div className="container py-5 px-3">
        
        {activeTab === 'dashboard' && (
          <>
            {/* Dashboard Shell View */}
            <div className="mb-5 text-center text-md-start">
              <h2 className="text-gradient fw-bold mb-2">Decision Intelligence Console</h2>
              <p className="text-secondary">Enterprise-grade platform shell ready for trusted business metrics. Find, upload, and inspect data below.</p>
            </div>

            <div className="row g-4">
              {/* Employee Directory Card */}
              <div className="col-12 col-md-6 col-lg-4">
                <div 
                  className="glass-card p-4 h-100 d-flex flex-column justify-content-between cursor-pointer"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveTab('employees')}
                >
                  <div>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="fw-bold text-success mb-0">Employee Directory</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>ACTIVE</span>
                    </div>
                    <p className="text-secondary small">Access a searchable directory of enterprise team members, roles, current projects, and expert skills.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-success fw-bold small">Launch Employee Directory →</span>
                  </div>
                </div>
              </div>

              {/* Document Ingestion Card */}
              <div className="col-12 col-md-6 col-lg-4">
                <div 
                  className="glass-card p-4 h-100 d-flex flex-column justify-content-between cursor-pointer"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveTab('ingestion')}
                >
                  <div>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="fw-bold text-success mb-0">Document Ingestion</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>ACTIVE</span>
                    </div>
                    <p className="text-secondary small">Handles file upload and schema parsing pipeline (PDF, Excel, CSV, Images, JSON, APIs).</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-success fw-bold small">Launch Ingestion Workspace →</span>
                  </div>
                </div>
              </div>

              {/* Enterprise Documents & Data Card */}
              <div className="col-12 col-md-6 col-lg-4">
                <div 
                  className="glass-card p-4 h-100 d-flex flex-column justify-content-between cursor-pointer"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveTab('repository')}
                >
                  <div>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="fw-bold text-success mb-0">Enterprise Documents & Data</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>ACTIVE</span>
                    </div>
                    <p className="text-secondary small">Monitors database records (JSONB), visualizes immutable version trails, and lists security logging audits.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-success fw-bold small">Launch Repository Workspace →</span>
                  </div>
                </div>
              </div>

              {/* Check Data Conflicts Card */}
              <div className="col-12 col-md-6 col-lg-4">
                <div 
                  className="glass-card p-4 h-100 d-flex flex-column justify-content-between cursor-pointer"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveTab('conflicts')}
                >
                  <div>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="fw-bold text-success mb-0">Check Data Conflicts</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>ACTIVE</span>
                    </div>
                    <p className="text-secondary small">Analyzes semantic consistency to detect contradictory, duplicate, and outdated knowledge.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-success fw-bold small">Launch Conflict Workspace →</span>
                  </div>
                </div>
              </div>

              {/* Data Quality Report Card */}
              <div className="col-12 col-md-6 col-lg-4">
                <div 
                  className="glass-card p-4 h-100 d-flex flex-column justify-content-between cursor-pointer"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveTab('explainability')}
                >
                  <div>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="fw-bold text-success mb-0">Data Quality Report</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>ACTIVE</span>
                    </div>
                    <p className="text-secondary small">Evaluates data quality using ML classification and generates SHAP explainability attributions with recommendations.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-success fw-bold small">Launch Quality & XAI Workspace →</span>
                  </div>
                </div>
              </div>

              <div className="col-12 col-md-6 col-lg-4">
                <div className="glass-card p-4 h-100 d-flex flex-column justify-content-between opacity-75">
                  <div>
                    <h5 className="fw-bold text-dark mb-2">Phase 5: Knowledge Assistant</h5>
                    <p className="text-secondary small">RAG-grounded natural language question-answering with a local Large Language Model.</p>
                  </div>
                  <div className="text-muted small border-top border-secondary pt-3 mt-3">Awaiting Phase 5 activation</div>
                </div>
              </div>

              <div className="col-12 col-md-6 col-lg-4">
                <div className="glass-card p-4 h-100 d-flex flex-column justify-content-between opacity-75">
                  <div>
                    <h5 className="fw-bold text-dark mb-2">Phase 6: Policy Impact Simulator</h5>
                    <p className="text-secondary small">Simulates organizational policy changes using predictive models with explainable SHAP features.</p>
                  </div>
                  <div className="text-muted small border-top border-secondary pt-3 mt-3">Awaiting Phase 6 activation</div>
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'ingestion' && (
          <>
            {/* Interactive Ingestion Workspace View */}
            <div className="mb-4 d-flex align-items-center gap-3">
              <button onClick={() => setActiveTab('dashboard')} className="btn btn-premium-secondary py-1 px-3 fs-6">
                ← Back
              </button>
              <div>
                <h3 className="text-gradient fw-bold mb-0">Phase 1 Ingestion Pipeline</h3>
                <p className="text-secondary small mb-0">Upload documents to standardize, parse metadata, and map schemas.</p>
              </div>
            </div>

            <div className="row g-4">
              {/* Workspace Left Column: Control Panel */}
              <div className="col-12 col-lg-5">
                <div className="glass-panel p-4 h-100">
                  <h5 className="fw-bold text-white mb-3">Upload Workspace</h5>
                  
                  <form onSubmit={handlePipelineSubmit}>
                    {/* Drag and Drop Zone */}
                    <div 
                      className={`border border-2 border-dashed rounded-3 p-5 text-center mb-3 position-relative ${dragActive ? 'border-info' : 'border-secondary'}`}
                      style={{ 
                        backgroundColor: dragActive ? 'rgba(6, 182, 212, 0.05)' : 'rgba(255,255,255,0.02)',
                        transition: 'all 0.2s ease-in-out'
                      }}
                      onDragEnter={handleDrag}
                      onDragLeave={handleDrag}
                      onDragOver={handleDrag}
                      onDrop={handleDrop}
                    >
                      <input 
                        type="file" 
                        id="pipeline-file-input" 
                        className="position-absolute top-0 start-0 w-100 h-100 opacity-0 cursor-pointer"
                        onChange={handleFileChange}
                        style={{ cursor: 'pointer' }}
                      />
                      <svg className="mb-3 text-secondary" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      {file ? (
                        <div>
                          <p className="text-white fw-medium mb-1">{file.name}</p>
                          <p className="text-secondary small font-monospace">{(file.size / 1024).toFixed(2)} KB</p>
                        </div>
                      ) : (
                        <div>
                          <p className="text-white mb-1">Drag & drop files here</p>
                          <p className="text-secondary small">or click to browse from device</p>
                        </div>
                      )}
                    </div>

                    {/* Parser Options Selector */}
                    <div className="mb-4">
                      <label className="form-label text-secondary small fw-medium">Parser Strategy</label>
                      <select 
                        className="form-select bg-white border-secondary text-dark"
                        value={parserType}
                        onChange={(e) => setParserType(e.target.value)}
                      >
                        <option value="auto">Auto-Detect MIME Signature (Recommended)</option>
                        <option value="PDF">PDF Parser</option>
                        <option value="EXCEL">Excel/Spreadsheet Parser</option>
                        <option value="CSV">CSV Table Parser</option>
                        <option value="JSON">JSON Parser</option>
                        <option value="IMAGE">Image OCR Parser</option>
                        <option value="TEXT">Plain Text Parser</option>
                      </select>
                    </div>

                    {/* Upload Target Repository Selection */}
                    <div className="mb-4">
                      <label className="form-label text-secondary small fw-medium">Upload Target Repository</label>
                      <select 
                        className="form-select bg-white border-secondary text-dark"
                        value={uploadRepoType}
                        onChange={(e) => setUploadRepoType(e.target.value)}
                      >
                        <option value="team">Team Repository (Shared)</option>
                        <option value="personal">Personal Repository (Confidential)</option>
                      </select>
                    </div>

                    <button 
                      type="submit" 
                      className="btn btn-premium-primary w-100 py-3"
                      disabled={processing || !file}
                    >
                      {processing ? (
                        <div className="d-flex align-items-center justify-content-center gap-2">
                          <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                          <span>Executing Pipeline Stages...</span>
                        </div>
                      ) : 'Ingest Document'}
                    </button>
                  </form>

                  {/* Stage Monitor List */}
                  <div className="mt-4 pt-3 border-top border-secondary">
                    <h6 className="text-secondary small fw-bold mb-3 text-uppercase font-monospace">Data Ingestion Lifecycle</h6>
                    
                    <div className="d-flex flex-column gap-2 small">
                      {/* Step 1: Upload */}
                      <div className="d-flex justify-content-between align-items-center font-monospace">
                        <span className={file ? "text-success fw-bold" : "text-muted"}>
                          {file ? "✓" : "○"} 1. File selected and ready
                        </span>
                        {file && <span className="badge bg-success">COMPLETED</span>}
                      </div>

                      {/* Step 2: Validation */}
                      <div className="d-flex justify-content-between align-items-center font-monospace">
                        <span className={
                          processing ? "text-cyan fw-bold animate-pulse" :
                          result?.pipeline_result?.stage_execution?.ValidationStage?.status === "SUCCESS" ? "text-success fw-bold" :
                          result?.pipeline_result?.stage_execution?.ValidationStage?.status === "FAILED" ? "text-danger fw-bold" : "text-muted"
                        }>
                          {processing ? "●" : result?.pipeline_result?.stage_execution?.ValidationStage?.status === "SUCCESS" ? "✓" : result?.pipeline_result?.stage_execution?.ValidationStage?.status === "FAILED" ? "✕" : "○"} 2. Format validation passed
                        </span>
                        {processing && <span className="badge bg-info animate-pulse">ACTIVE</span>}
                        {result?.pipeline_result?.stage_execution?.ValidationStage && (
                          <span className={`badge ${result.pipeline_result.stage_execution.ValidationStage.status === "SUCCESS" ? "bg-success" : "bg-danger"}`}>
                            {result.pipeline_result.stage_execution.ValidationStage.status}
                          </span>
                        )}
                      </div>

                      {/* Step 3: File Identification */}
                      <div className="d-flex justify-content-between align-items-center font-monospace">
                        <span className={
                          result?.pipeline_result?.stage_execution?.ParserStage?.status === "SUCCESS" ? "text-success fw-bold" : "text-muted"
                        }>
                          {result?.pipeline_result?.stage_execution?.ParserStage?.status === "SUCCESS" ? "✓" : "○"} 3. Checking file headers
                        </span>
                        {result?.pipeline_result?.stage_execution?.ParserStage && (
                          <span className="badge bg-success">COMPLETED</span>
                        )}
                      </div>

                      {/* Step 4: Parsing */}
                      <div className="d-flex justify-content-between align-items-center font-monospace">
                        <span className={
                          result?.pipeline_result?.stage_execution?.ParserStage?.status === "SUCCESS" ? "text-success fw-bold" : "text-muted"
                        }>
                          {result?.pipeline_result?.stage_execution?.ParserStage?.status === "SUCCESS" ? "✓" : "○"} 4. Extracting text content
                        </span>
                        {result?.pipeline_result?.stage_execution?.ParserStage && (
                          <span className="badge bg-success">COMPLETED</span>
                        )}
                      </div>

                      {/* Step 5: Content / Metadata Extraction */}
                      <div className="d-flex justify-content-between align-items-center font-monospace">
                        <span className={
                          result?.pipeline_result?.stage_execution?.MetadataStage?.status === "SUCCESS" ? "text-success fw-bold" : "text-muted"
                        }>
                          {result?.pipeline_result?.stage_execution?.MetadataStage?.status === "SUCCESS" ? "✓" : "○"} 5. Fetching document metadata
                        </span>
                        {result?.pipeline_result?.stage_execution?.MetadataStage && (
                          <span className="badge bg-success">COMPLETED</span>
                        )}
                      </div>

                      {/* Step 6: Schema Mapping */}
                      <div className="d-flex justify-content-between align-items-center font-monospace">
                        <span className={
                          result?.pipeline_result?.stage_execution?.SchemaStage?.status === "SUCCESS" ? "text-success fw-bold" : "text-muted"
                        }>
                          {result?.pipeline_result?.stage_execution?.SchemaStage?.status === "SUCCESS" ? "✓" : "○"} 6. Mapping record fields
                        </span>
                        {result?.pipeline_result?.stage_execution?.SchemaStage && (
                          <span className="badge bg-success">COMPLETED</span>
                        )}
                      </div>

                      {/* Step 7: Data Standardization */}
                      <div className="d-flex justify-content-between align-items-center font-monospace">
                        <span className={
                          result?.pipeline_result?.stage_execution?.StandardizationStage?.status === "SUCCESS" ? "text-success fw-bold" : "text-muted"
                        }>
                          {result?.pipeline_result?.stage_execution?.StandardizationStage?.status === "SUCCESS" ? "✓" : "○"} 7. Standardizing record formats
                        </span>
                        {result?.pipeline_result?.stage_execution?.StandardizationStage && (
                          <span className="badge bg-success">COMPLETED</span>
                        )}
                      </div>

                      {/* Step 8: Pipeline Completed */}
                      <div className="d-flex justify-content-between align-items-center font-monospace">
                        <span className={
                          result?.pipeline_result?.stage_execution?.PersistenceStage?.status === "SUCCESS" ? "text-success fw-bold" : "text-muted"
                        }>
                          {result?.pipeline_result?.stage_execution?.PersistenceStage?.status === "SUCCESS" ? "✓" : "○"} 8. Saved to enterprise database
                        </span>
                        {result?.pipeline_result?.stage_execution?.PersistenceStage && (
                          <span className="badge bg-success">SUCCESS</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Ingestion Summary Card */}
                  {result && (
                    <div className="mt-4 pt-3 border-top border-secondary">
                      <div className="p-3 bg-light rounded-3 border border-secondary">
                        <h6 className="fw-bold text-success mb-2">✓ Ingestion Summary</h6>
                        <div className="small font-monospace text-secondary d-flex flex-column gap-1">
                          <div>File: <strong className="text-dark">{result.file_name}</strong></div>
                          <div>Parser: <strong className="text-dark">{result.pipeline_result?.metadata?.processing?.parser_used || 'AutoDetect'}</strong></div>
                          <div>Validation: <strong className="text-success">Passed</strong></div>
                          <div>Duration: <strong className="text-dark">{((result.pipeline_result?.pipeline_duration || 0) * 1000).toFixed(0)} ms</strong></div>
                          <div>Records: <strong className="text-dark">{result.pipeline_result?.standardized_record?.standardized_record?.length || result.pipeline_result?.standardized_record?.records?.length || 0}</strong></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Workspace Right Column: Result Explorer */}
              <div className="col-12 col-lg-7">
                <div className="glass-panel p-4 h-100 d-flex flex-column" style={{ minHeight: '400px' }}>
                  <h5 className="fw-bold text-white mb-3">Pipeline Results</h5>

                  {errorMsg && (
                    <div className="alert alert-danger border-0 text-white mb-3" style={{ backgroundColor: 'rgba(220, 53, 69, 0.2)' }}>
                      <h6 className="fw-bold">Pipeline Aborted</h6>
                      <p className="small mb-0">{errorMsg}</p>
                    </div>
                  )}

                  {result ? (
                    <div className="d-flex flex-column flex-grow-1">
                      {/* Success / Failure Banner */}
                      {result.processing_status === 'COMPLETED' ? (
                        <div className="alert alert-success border-0 py-2 px-3 mb-3 d-flex justify-content-between align-items-center">
                          <span className="fw-bold">✓ PROCESSING COMPLETED SUCCESSFULLY</span>
                          <button className="btn btn-premium-secondary btn-sm py-1 px-3 border-secondary" onClick={() => setActiveTab('repository')}>
                            Go to Repository
                          </button>
                        </div>
                      ) : (
                        <div className="alert alert-danger border-0 py-3 px-3 mb-3">
                          <span className="fw-bold fs-6 d-block mb-2">✕ PIPELINE EXECUTION FAILED</span>
                          <p className="small mb-1">Document uploaded, but processing aborted due to execution failure.</p>
                          {failedStageName && (
                            <div className="mt-2 font-monospace small">
                              <strong>Failed Stage:</strong> <span className="text-danger fw-bold">{failedStageName}</span>
                            </div>
                          )}
                          {errorMsg && (
                            <div className="mt-1 font-monospace small bg-light p-2 rounded border border-danger border-opacity-25 text-danger overflow-auto" style={{ maxHeight: '100px' }}>
                              <strong>Reason:</strong> {errorMsg}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Document Overview Metadata Panel */}
                      <div className="row g-2 mb-4 bg-light p-3 rounded-3 border border-secondary">
                        <div className="col-6 col-sm-3">
                          <span className="text-secondary d-block small">DOCUMENT ID</span>
                          <span className="fw-bold font-monospace">{result.document_id || 'N/A'}</span>
                        </div>
                        <div className="col-6 col-sm-3">
                          <span className="text-secondary d-block small">STATUS</span>
                          <span className={`badge ${result.processing_status === 'COMPLETED' ? 'bg-success' : 'bg-danger'}`}>
                            {result.processing_status}
                          </span>
                        </div>
                        <div className="col-6 col-sm-3 mt-2 mt-sm-0">
                          <span className="text-secondary d-block small">ELAPSED TIME</span>
                          <span className="fw-bold font-monospace text-dark">
                            {result.pipeline_result?.pipeline_duration?.toFixed(3) || '0.000'}s
                          </span>
                        </div>
                        <div className="col-6 col-sm-3 mt-2 mt-sm-0">
                          <span className="text-secondary d-block small">RECORDS SYNC'D</span>
                          <span className="fw-bold font-monospace text-dark">
                            {result.processing_status === 'COMPLETED' ? (result.pipeline_result?.standardized_record?.standardized_record?.length || result.pipeline_result?.standardized_record?.records?.length || 0) : 0}
                          </span>
                        </div>
                      </div>

                      {/* Tab Switched Explorer */}
                      <ul className="nav nav-tabs border-secondary mb-3">
                        <li className="nav-item">
                          <button 
                            className={`nav-link bg-transparent border-0 border-bottom text-dark ${resultTab === 'record' ? 'border-success active text-success font-bold' : 'border-transparent text-secondary'}`}
                            onClick={() => setResultTab('record')}
                          >
                            Standardized Record
                          </button>
                        </li>
                        <li className="nav-item">
                          <button 
                            className={`nav-link bg-transparent border-0 border-bottom text-dark ${resultTab === 'metadata' ? 'border-success active text-success font-bold' : 'border-transparent text-secondary'}`}
                            onClick={() => setResultTab('metadata')}
                          >
                            Pipeline Metadata
                          </button>
                        </li>
                        <li className="nav-item">
                          <button 
                            className={`nav-link bg-transparent border-0 border-bottom text-dark ${resultTab === 'stages' ? 'border-success active text-success font-bold' : 'border-transparent text-secondary'}`}
                            onClick={() => setResultTab('stages')}
                          >
                            Orchestration Logs
                          </button>
                        </li>
                      </ul>

                      {/* Tab content viewer */}
                      <div className="flex-grow-1 position-relative" style={{ minHeight: '300px' }}>
                        {resultTab === 'record' && (
                          <div className="bg-light rounded-3 p-3 h-100 border border-secondary font-monospace overflow-auto" style={{ maxHeight: '350px' }}>
                            {result.processing_status === 'FAILED' ? (
                              <div className="text-danger small">
                                ✕ No standardized record was generated because the pipeline failed.
                              </div>
                            ) : (
                              <pre className="text-success small mb-0">
                                {JSON.stringify(result.pipeline_result?.standardized_record || {}, null, 2)}
                              </pre>
                            )}
                          </div>
                        )}

                        {resultTab === 'metadata' && (
                          <div className="bg-light rounded-3 p-3 h-100 border border-secondary font-monospace overflow-auto" style={{ maxHeight: '350px' }}>
                            {result.processing_status === 'FAILED' ? (
                              <div className="text-danger small">
                                ✕ No metadata was generated because the pipeline failed.
                              </div>
                            ) : (
                              <pre className="text-warning small mb-0">
                                {JSON.stringify(result.pipeline_result?.metadata || {}, null, 2)}
                              </pre>
                            )}
                          </div>
                        )}

                        {resultTab === 'stages' && (
                          <div className="h-100 d-flex flex-column gap-3 overflow-auto" style={{ maxHeight: '350px' }}>
                            <div className="bg-light rounded-3 p-3 border border-secondary font-monospace small">
                              <div className="text-secondary mb-2">// Correlation Execution IDs</div>
                              <div>Pipeline ID: <span className="text-success">{result.pipeline_result?.pipeline_id || 'N/A'}</span></div>
                              <div>Document ID: <span className="text-success">{result.document_id || 'N/A'}</span></div>
                            </div>
                            
                            <div className="d-flex flex-column gap-2">
                              {result.pipeline_result?.warnings?.map((warning, idx) => (
                                <div key={idx} className="alert alert-warning py-2 small mb-0 border-0">
                                  ⚠️ [WARNING] {warning}
                                </div>
                              ))}
                              {result.pipeline_result?.errors?.map((error, idx) => (
                                <div key={idx} className="alert alert-danger py-2 small mb-0 border-0">
                                  🛑 [ERROR] {error}
                                </div>
                              ))}
                              {(!result.pipeline_result?.warnings?.length && !result.pipeline_result?.errors?.length) && (
                                <div className="text-success small">✓ Ingestion complete with zero warnings and zero exceptions.</div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="d-flex flex-column justify-content-center align-items-center flex-grow-1 text-center text-muted">
                      <svg width="64" height="64" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mb-3 opacity-25">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <p className="fw-medium text-secondary mb-1">Awaiting pipeline run...</p>
                      <p className="small text-muted px-4">Upload a document on the left and run ingestion to inspect schema records and governance metadata details.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'repository' && (
          <>
            {/* Knowledge Repository Workspace */}
            <div className="mb-4 d-flex align-items-center justify-content-between">
              <div className="d-flex align-items-center gap-3">
                <button onClick={() => setActiveTab('dashboard')} className="btn btn-premium-secondary py-1 px-3 fs-6">
                  ← Back
                </button>
                <div>
                  <h3 className="text-gradient fw-bold mb-0">Enterprise Documents & Data</h3>
                  <p className="text-secondary small mb-0">Browse logical repositories and preview enterprise documents securely.</p>
                </div>
              </div>
              
              <div className="btn-group border border-secondary rounded overflow-hidden">
                <button 
                  className={`btn py-2 px-3 border-0 rounded-0 ${repoTabType === 'docs' ? 'btn-premium-primary' : 'btn-dark text-secondary'}`}
                  onClick={() => setRepoTabType('docs')}
                >
                  Document Registry
                </button>
                <button 
                  className={`btn py-2 px-3 border-0 rounded-0 ${repoTabType === 'search' ? 'btn-premium-primary' : 'btn-dark text-secondary'}`}
                  onClick={() => setRepoTabType('search')}
                >
                  Query Records (JSONB)
                </button>
              </div>
            </div>

            {/* Alert messages */}
            {repoError && (
              <div className="alert alert-danger border-0 text-white mb-4 d-flex justify-content-between align-items-center" style={{ backgroundColor: 'rgba(220, 53, 69, 0.2)' }}>
                <span>🛑 {repoError}</span>
                <button className="btn btn-sm text-white border-0" onClick={() => setRepoError('')}>×</button>
              </div>
            )}
            {repoSuccess && (
              <div className="alert alert-success border-0 text-white mb-4 d-flex justify-content-between align-items-center" style={{ backgroundColor: 'rgba(25, 135, 84, 0.2)' }}>
                <span>✓ {repoSuccess}</span>
                <button className="btn btn-sm text-white border-0" onClick={() => setRepoSuccess('')}>×</button>
              </div>
            )}

            {repoTabType === 'docs' ? (
              <div className="d-flex flex-column gap-4">
                <div className="row g-4">
                  {/* Documents Table */}
                  <div className="col-12 col-lg-7">
                    <div className="glass-panel p-4 h-100">
                      {/* Logical Repository Selection Tabs */}
                      <div className="d-flex justify-content-between align-items-center mb-4">
                        <div className="btn-group border border-secondary rounded overflow-hidden">
                          <button 
                            className={`btn py-1 px-3 border-0 rounded-0 small ${selectedRepoType === 'team' ? 'btn-premium-primary' : 'btn-dark text-secondary'}`}
                            onClick={() => { setSelectedRepoType('team'); setSelectedDoc(null); }}
                            style={{ fontSize: '0.85rem' }}
                          >
                            Team Repository
                          </button>
                          <button 
                            className={`btn py-1 px-3 border-0 rounded-0 small ${selectedRepoType === 'personal' ? 'btn-premium-primary' : 'btn-dark text-secondary'}`}
                            onClick={() => { setSelectedRepoType('personal'); setSelectedDoc(null); }}
                            style={{ fontSize: '0.85rem' }}
                          >
                            Personal Repository
                          </button>
                        </div>
                        <button className="btn btn-premium-secondary btn-sm py-1 px-3" onClick={fetchDocuments} disabled={loadingDocs}>
                          Refresh
                        </button>
                      </div>

                      {loadingDocs ? (
                        <div className="text-center py-5 text-secondary">
                          <span className="spinner-border spinner-border-sm me-2"></span>
                          Loading registry...
                        </div>
                      ) : documents.filter(doc => (doc.metadata?.repository_type || 'team') === selectedRepoType).length > 0 ? (
                        <div className="table-responsive">
                          <table className="table table-hover align-middle border table-sm">
                            <thead className="table-light">
                              <tr className="small text-secondary">
                                <th>Document Name</th>
                                <th>File Type</th>
                                <th>Version</th>
                                <th>Last Updated</th>
                                <th className="text-end">Actions</th>
                              </tr>
                            </thead>
                            <tbody className="small">
                              {documents
                                .filter(doc => (doc.metadata?.repository_type || 'team') === selectedRepoType)
                                .map((doc) => {
                                  const fileExt = doc.title.split('.').pop().toUpperCase();
                                  return (
                                    <tr 
                                      key={doc.id} 
                                      className={`cursor-pointer ${selectedDoc?.id === doc.id ? 'table-active' : ''}`}
                                      onClick={() => fetchDocumentSubDetails(doc)}
                                    >
                                      <td className="fw-medium text-dark text-truncate" style={{ maxWidth: '180px' }}>
                                        {doc.title}
                                      </td>
                                      <td><span className="badge bg-secondary">{fileExt}</span></td>
                                      <td>v{doc.current_version}</td>
                                      <td className="font-monospace text-secondary">{new Date(doc.last_sync).toLocaleDateString()}</td>
                                      <td className="text-end" onClick={(e) => e.stopPropagation()}>
                                        <div className="d-flex gap-2 justify-content-end">
                                          <button onClick={() => fetchFilePreview(doc)} className="btn btn-sm btn-premium-primary py-0 px-2">
                                            View
                                          </button>
                                          {user?.role === 'admin' && (
                                            <button onClick={() => softDeleteDocument(doc.id)} className="btn btn-sm btn-outline-danger py-0 px-2 border-0">
                                              Purge
                                            </button>
                                          )}
                                        </div>
                                      </td>
                                    </tr>
                                  );
                                })}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="text-center py-5 text-muted small">
                          No active {selectedRepoType} documents found.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Clean Business details panel */}
                  <div className="col-12 col-lg-5">
                    <div className="glass-panel p-4 h-100 d-flex flex-column" style={{ minHeight: '400px' }}>
                      {selectedDoc ? (
                        <>
                          <div className="d-flex justify-content-between align-items-start mb-3 border-bottom border-secondary pb-3">
                            <div>
                              <h5 className="fw-bold text-white mb-0">{selectedDoc.title}</h5>
                              <span className="text-secondary small font-monospace">Repository: {selectedDoc.metadata?.repository_type === 'personal' ? 'Personal (Confidential)' : 'Team (Shared)'}</span>
                            </div>
                            <button className="btn btn-premium-primary btn-sm py-1 px-3" onClick={() => fetchFilePreview(selectedDoc)}>
                              Open File Viewer
                            </button>
                          </div>

                          <div className="d-flex flex-column gap-3 mb-4">
                            <div className="row g-2 small text-secondary">
                              <div className="col-6">File Type: <strong className="text-white">{selectedDoc.title.split('.').pop().toUpperCase()}</strong></div>
                              <div className="col-6">Current Version: <strong className="text-white">v{selectedDoc.current_version}</strong></div>
                              <div className="col-6">Record Count: <strong className="text-white">{selectedDoc.record_count}</strong></div>
                              <div className="col-6">Last Updated: <strong className="text-white">{new Date(selectedDoc.last_sync).toLocaleString()}</strong></div>
                            </div>
                          </div>

                          {/* Technical information strictly collapsed under a Details Accordion */}
                          <div className="accordion mt-auto" id="techAccordion">
                            <div className="accordion-item bg-dark border-secondary">
                              <h2 className="accordion-header">
                                <button className="accordion-button collapsed py-2 px-3 small text-secondary bg-dark text-white border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#techCollapse">
                                  Technical Details (Admin / Developers Only)
                                </button>
                              </h2>
                              <div id="techCollapse" className="accordion-collapse collapse" data-bs-parent="#techAccordion">
                                <div className="accordion-body p-3 font-monospace small text-secondary bg-dark">
                                  <div className="mb-2">Document ID: {selectedDoc.id}</div>
                                  <div className="mb-2">Source file size: {(selectedDoc.repository_size / 1024).toFixed(2)} KB</div>
                                  
                                  {/* Sub-tabs nav inside tech area */}
                                  <ul className="nav nav-pills nav-fill border border-secondary rounded overflow-hidden mb-3 bg-dark bg-opacity-50 mt-3">
                                    {['records', 'versions', 'audit', 'metadata'].map((tab) => (
                                      <li className="nav-item" key={tab}>
                                        <button 
                                          className={`nav-link text-white py-1 rounded-0 border-0 ${activeDetailsTab === tab ? 'btn-premium-primary text-white' : 'bg-transparent text-secondary'}`}
                                          onClick={() => setActiveDetailsTab(tab)}
                                          style={{ fontSize: '0.75rem' }}
                                        >
                                          {tab.toUpperCase()}
                                        </button>
                                      </li>
                                    ))}
                                  </ul>

                                  <div className="overflow-auto" style={{ maxHeight: '250px' }}>
                                    {activeDetailsTab === 'records' && (
                                      <div className="d-flex flex-column gap-2">
                                        {selectedDocDetails.records.length > 0 ? (
                                          selectedDocDetails.records.map((rec) => (
                                            <div key={rec.id} className="bg-light rounded p-2 border border-secondary font-monospace position-relative">
                                              <div className="d-flex justify-content-between mb-1">
                                                <span className="text-success small">{rec.entity_type.toUpperCase()}</span>
                                                <div className="d-flex gap-2">
                                                  {editingRecordId === rec.id ? (
                                                    <>
                                                      <button className="btn btn-sm btn-success py-0 px-2 border-0" onClick={() => handleUpdateRecord(rec.id)}>Save</button>
                                                      <button className="btn btn-sm btn-secondary py-0 px-2 border-0" onClick={() => setEditingRecordId(null)}>Cancel</button>
                                                    </>
                                                  ) : (
                                                    <>
                                                      <button className="btn btn-sm btn-outline-info py-0 px-1 border-0" onClick={() => {
                                                        setEditingRecordId(rec.id);
                                                        setEditingDataJson(JSON.stringify(rec.canonical_data, null, 2));
                                                      }}>Edit</button>
                                                      <button className="btn btn-sm btn-outline-danger py-0 px-1 border-0" onClick={() => handleDeleteRecord(rec.id)}>Del</button>
                                                    </>
                                                  )}
                                                </div>
                                              </div>
                                              
                                              {editingRecordId === rec.id ? (
                                                <textarea 
                                                  className="form-control bg-white text-dark small border-secondary font-monospace w-100" 
                                                  rows="4"
                                                  value={editingDataJson}
                                                  onChange={(e) => setEditingDataJson(e.target.value)}
                                                />
                                              ) : (
                                                <pre className="text-success small mb-0 overflow-auto">{JSON.stringify(rec.canonical_data, null, 2)}</pre>
                                              )}
                                            </div>
                                          ))
                                        ) : (
                                          <p className="text-muted small">No record list found.</p>
                                        )}
                                      </div>
                                    )}

                                    {activeDetailsTab === 'versions' && (
                                      <div className="d-flex flex-column gap-2">
                                        {selectedDocDetails.versions.length > 0 ? (
                                          selectedDocDetails.versions.map((ver) => (
                                            <div key={ver.id} className="bg-light p-2 rounded border border-secondary small">
                                              <div className="d-flex justify-content-between mb-1">
                                                <span className="fw-semibold text-dark">Version v{ver.version}</span>
                                                <span className="text-secondary">{new Date(ver.snapshot_timestamp).toLocaleDateString()}</span>
                                              </div>
                                              <div className="text-muted mb-1 text-truncate">Commit user: {ver.updated_by_username || 'SYSTEM'}</div>
                                              <pre className="text-warning small mb-0 bg-white p-1 border border-secondary" style={{ fontSize: '0.7rem' }}>{JSON.stringify(ver.change_summary || {}, null, 2)}</pre>
                                            </div>
                                          ))
                                        ) : (
                                          <p className="text-muted small">No snapshots compiled.</p>
                                        )}
                                      </div>
                                    )}

                                    {activeDetailsTab === 'audit' && (
                                      <div className="d-flex flex-column gap-2">
                                        {selectedDocDetails.audit.length > 0 ? (
                                          selectedDocDetails.audit.map((aud) => (
                                            <div key={aud.id} className="bg-light p-2 rounded border border-secondary small">
                                              <div className="d-flex justify-content-between mb-1">
                                                <span className={`badge ${
                                                  aud.action === 'SYNC' ? 'bg-success' :
                                                  aud.action === 'EDIT' ? 'bg-warning' : 'bg-danger'
                                                }`}>{aud.action}</span>
                                                <span className="text-secondary" style={{ fontSize: '0.7rem' }}>{new Date(aud.timestamp).toLocaleString()}</span>
                                              </div>
                                              <div className="text-light my-1">{aud.reason}</div>
                                              <div className="text-muted" style={{ fontSize: '0.7rem' }}>User: {aud.user}</div>
                                            </div>
                                          ))
                                        ) : (
                                          <p className="text-muted small">No audit trail logged.</p>
                                        )}
                                      </div>
                                    )}

                                    {activeDetailsTab === 'metadata' && (
                                      <div className="bg-light rounded p-2 border border-secondary">
                                        <pre className="text-warning small mb-0">{JSON.stringify(selectedDoc.metadata || {}, null, 2)}</pre>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="d-flex flex-column justify-content-center align-items-center flex-grow-1 text-center text-muted">
                          <svg width="68" height="68" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mb-3 opacity-25">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          <p className="fw-semibold text-secondary">Awaiting document selection</p>
                          <p className="small text-muted px-4">Select an active document in the registry list on the left to see details and fetch record snapshots.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* IN-ERP FILE VIEWER FRAME */}
                {previewingDoc && (
                  <div className="glass-panel p-4 border border-info rounded-3">
                    <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary">
                      <div className="d-flex align-items-center gap-2">
                        <span className="badge bg-info text-black font-monospace text-uppercase">{previewData?.file_type || 'Loading'}</span>
                        <h5 className="fw-bold text-white mb-0">{previewingDoc.title}</h5>
                      </div>
                      <div className="d-flex gap-2">
                        <button className="btn btn-premium-secondary btn-sm py-1 px-3" onClick={() => downloadFileSecurely(previewingDoc)}>
                          Secure Download
                        </button>
                        <button className="btn btn-premium-secondary btn-sm py-1 px-3" onClick={() => { setPreviewingDoc(null); setPreviewData(null); }}>
                          Close Preview
                        </button>
                      </div>
                    </div>

                    {loadingPreview ? (
                      <div className="text-center py-5 text-secondary">
                        <span className="spinner-border spinner-border-sm me-2 text-info"></span>
                        Reading file contents securely from server...
                      </div>
                    ) : previewError ? (
                      <div className="alert alert-danger py-2">{previewError}</div>
                    ) : previewData ? (
                      <div className="preview-container overflow-auto" style={{ maxHeight: '600px' }}>
                        {previewData.file_type === 'csv' && (
                          <div className="bg-light p-3 rounded border">
                            <div className="table-responsive">
                              <table className="table table-hover table-bordered align-middle table-sm small mb-0">
                                <thead className="table-light">
                                  <tr className="small text-secondary">
                                    {previewData.headers.map((h, idx) => <th key={idx}>{h}</th>)}
                                  </tr>
                                </thead>
                                <tbody>
                                  {previewData.rows.slice((csvPage - 1) * rowsPerPage, csvPage * rowsPerPage).map((row, rIdx) => (
                                    <tr key={rIdx}>
                                      {row.map((cell, cIdx) => <td key={cIdx}>{cell !== null && cell !== undefined ? String(cell) : ""}</td>)}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            {/* CSV pagination */}
                            {previewData.rows.length > rowsPerPage && (
                              <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top">
                                <span className="small text-secondary">Showing {((csvPage - 1) * rowsPerPage) + 1} to {Math.min(csvPage * rowsPerPage, previewData.rows.length)} of {previewData.rows.length} rows</span>
                                <div className="btn-group">
                                  <button className="btn btn-premium-secondary btn-sm py-0 px-2" disabled={csvPage === 1} onClick={() => setCsvPage(csvPage - 1)}>Prev</button>
                                  <button className="btn btn-premium-secondary btn-sm py-0 px-2" disabled={csvPage * rowsPerPage >= previewData.rows.length} onClick={() => setCsvPage(csvPage + 1)}>Next</button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {previewData.file_type === 'excel' && (
                          <div className="bg-light p-3 rounded border">
                            {/* Excel sheets tabs */}
                            <div className="d-flex flex-wrap gap-2 mb-3 border-bottom pb-2">
                              {Object.keys(previewData.sheets).map(sheetName => (
                                <button 
                                  key={sheetName} 
                                  className={`btn btn-sm ${activeExcelSheet === sheetName ? 'btn-premium-primary text-white' : 'btn-outline-secondary'}`}
                                  onClick={() => { setActiveExcelSheet(sheetName); setCsvPage(1); }}
                                >{sheetName}</button>
                              ))}
                            </div>
                            
                            {activeExcelSheet && previewData.sheets[activeExcelSheet] && (() => {
                              const sheet = previewData.sheets[activeExcelSheet];
                              return (
                                <>
                                  <div className="table-responsive">
                                    <table className="table table-hover table-bordered align-middle table-sm small mb-0">
                                      <thead className="table-light">
                                        <tr className="small text-secondary">
                                          {sheet.headers.map((h, idx) => <th key={idx}>{h}</th>)}
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {sheet.rows.slice((csvPage - 1) * rowsPerPage, csvPage * rowsPerPage).map((row, rIdx) => (
                                          <tr key={rIdx}>
                                            {row.map((cell, cIdx) => <td key={cIdx}>{cell !== null && cell !== undefined ? String(cell) : ""}</td>)}
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                  {/* Excel sheet pagination */}
                                  {sheet.rows.length > rowsPerPage && (
                                    <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top border-secondary">
                                      <span className="small text-secondary">Showing {((csvPage - 1) * rowsPerPage) + 1} to {Math.min(csvPage * rowsPerPage, sheet.rows.length)} of {sheet.rows.length} rows</span>
                                      <div className="btn-group">
                                        <button className="btn btn-premium-secondary btn-sm py-0 px-2" disabled={csvPage === 1} onClick={() => setCsvPage(csvPage - 1)}>Prev</button>
                                        <button className="btn btn-premium-secondary btn-sm py-0 px-2" disabled={csvPage * rowsPerPage >= sheet.rows.length} onClick={() => setCsvPage(csvPage + 1)}>Next</button>
                                      </div>
                                    </div>
                                  )}
                                </>
                              );
                            })()}
                          </div>
                        )}

                        {previewData.file_type === 'text' && (
                          <pre className="text-success bg-black p-3 rounded font-monospace small mb-0 overflow-auto" style={{ maxHeight: '450px', whiteSpace: 'pre-wrap' }}>
                            {previewData.content}
                          </pre>
                        )}

                        {previewData.file_type === 'pdf' && (
                          <div className="pdf-viewer-frame border rounded overflow-hidden">
                            <iframe src={previewData.url} className="w-100" style={{ height: '600px', border: 'none' }} title="PDF Preview" />
                          </div>
                        )}

                        {previewData.file_type === 'image' && (
                          <div className="text-center p-3 bg-dark rounded border">
                            <div className="mb-2 d-flex gap-2 justify-content-center">
                              <button className="btn btn-sm btn-premium-secondary py-0 px-2" onClick={() => setImageZoom(Math.max(25, imageZoom - 25))}>Zoom Out</button>
                              <span className="text-secondary small font-monospace align-self-center">{imageZoom}%</span>
                              <button className="btn btn-sm btn-premium-secondary py-0 px-2" onClick={() => setImageZoom(Math.min(200, imageZoom + 25))}>Zoom In</button>
                              <button className="btn btn-sm btn-premium-secondary py-0 px-2" onClick={() => setImageZoom(100)}>Reset</button>
                            </div>
                            <img 
                              src={previewData.url} 
                              alt="Image preview" 
                              className="img-fluid rounded" 
                              style={{ 
                                maxWidth: '100%', 
                                maxHeight: '500px', 
                                transform: `scale(${imageZoom / 100})`, 
                                transition: 'transform 0.15s ease-in-out',
                                objectFit: 'contain'
                              }} 
                            />
                          </div>
                        )}

                        {previewData.file_type === 'unsupported' && (
                          <div className="text-center py-5 text-muted small bg-dark p-4 rounded border">
                            <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mb-3 opacity-50">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            <p className="fw-semibold text-white mb-2">Preview not available for this file type ({previewingDoc.title.split('.').pop()})</p>
                            <p className="small text-secondary mb-4">Please download the document to view its contents locally.</p>
                            <button className="btn btn-premium-primary" onClick={() => downloadFileSecurely(previewingDoc)}>
                              Download Document
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-5 text-muted">Awaiting preview content</div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              /* Global Records Custom Search Workspace */
              <div className="glass-panel p-4">
                <h5 className="fw-bold text-white mb-3">Database Records Lookup (JSONB Query Engine)</h5>
                
                <div className="row g-3 mb-4">
                  <div className="col-12 col-md-3">
                    <label className="form-label text-secondary small">JSONB Field Key</label>
                    <input 
                      type="text" 
                      className="form-control bg-white border-secondary text-success font-monospace" 
                      placeholder="e.g. employee_id, email, salary"
                      value={searchField}
                      onChange={(e) => setSearchField(e.target.value)}
                    />
                  </div>
                  <div className="col-12 col-md-3">
                    <label className="form-label text-secondary small">Exact Field Value</label>
                    <input 
                      type="text" 
                      className="form-control bg-white border-secondary text-success font-monospace" 
                      placeholder="e.g. EMP101, HR"
                      value={searchValue}
                      onChange={(e) => setSearchValue(e.target.value)}
                    />
                  </div>
                  <div className="col-12 col-md-3">
                    <label className="form-label text-secondary small">Search Substring (Contains)</label>
                    <input 
                      type="text" 
                      className="form-control bg-white border-secondary text-success font-monospace" 
                      placeholder="e.g. @corporation.com"
                      value={searchContains}
                      onChange={(e) => setSearchContains(e.target.value)}
                    />
                  </div>
                  <div className="col-12 col-md-3 d-flex align-items-end">
                    <button 
                      className="btn btn-premium-primary w-100 py-2"
                      onClick={executeRecordsQuery}
                      disabled={loadingGlobalRecords}
                    >
                      {loadingGlobalRecords ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2"></span>
                          Searching...
                        </>
                      ) : 'Execute Query'}
                    </button>
                  </div>
                </div>

                <div className="border-top border-secondary pt-3 mt-4">
                  <h6 className="text-secondary small fw-bold mb-3 font-monospace">Record Results Query Matches ({globalRecords.length})</h6>
                  
                  {loadingGlobalRecords ? (
                    <div className="text-center py-5 text-secondary">
                      <span className="spinner-border spinner-border-sm me-2"></span>
                      Searching JSONB fields...
                    </div>
                  ) : globalRecords.length > 0 ? (
                    <div className="row g-3">
                      {globalRecords.map((rec) => (
                        <div key={rec.id} className="col-12 col-md-6 col-lg-4">
                          <div className="bg-light rounded p-3 border border-secondary font-monospace h-100 d-flex flex-column justify-content-between">
                            <div>
                              <div className="d-flex justify-content-between mb-2 pb-2 border-bottom border-secondary">
                                <span className="text-success small">{rec.entity_type.toUpperCase()}</span>
                                <span className="text-secondary small font-monospace" style={{ fontSize: '0.75rem' }}>Doc: {rec.knowledge_document}</span>
                              </div>
                              
                              {editingRecordId === rec.id ? (
                                <textarea 
                                  className="form-control bg-white text-dark small border-secondary font-monospace w-100 mb-2" 
                                  rows="6"
                                  value={editingDataJson}
                                  onChange={(e) => setEditingDataJson(e.target.value)}
                                />
                              ) : (
                                <pre className="text-success small mb-0 overflow-auto" style={{ maxHeight: '180px' }}>
                                  {JSON.stringify(rec.canonical_data, null, 2)}
                                </pre>
                              )}
                            </div>

                            <div className="d-flex gap-2 justify-content-end mt-3 pt-2 border-top border-secondary">
                              {editingRecordId === rec.id ? (
                                <>
                                  <button 
                                    className="btn btn-sm btn-success py-0 px-2 border-0" 
                                    onClick={() => handleUpdateRecord(rec.id, true)}
                                  >Save</button>
                                  <button 
                                    className="btn btn-sm btn-secondary py-0 px-2 border-0" 
                                    onClick={() => setEditingRecordId(null)}
                                  >Cancel</button>
                                </>
                              ) : (
                                <>
                                  <button 
                                    className="btn btn-sm btn-outline-info py-0 px-2 border-0" 
                                    onClick={() => {
                                      setEditingRecordId(rec.id);
                                      setEditingDataJson(JSON.stringify(rec.canonical_data, null, 2));
                                    }}
                                  >Edit Keys</button>
                                  <button 
                                    className="btn btn-sm btn-outline-danger py-0 px-2 border-0" 
                                    onClick={() => handleDeleteRecord(rec.id, true)}
                                  >Purge Record</button>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-5 text-muted small">
                      No records matched or execution empty. Execute a query with filters above.
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === 'employees' && (
          <>
            <div className="mb-4 d-flex align-items-center gap-3">
              <button onClick={() => setActiveTab('dashboard')} className="btn btn-premium-secondary py-1 px-3 fs-6">
                ← Back
              </button>
              <div>
                <h3 className="text-gradient fw-bold mb-0">Employee Directory</h3>
                <p className="text-secondary small mb-0">Searchable directory of enterprise team members.</p>
              </div>
            </div>
            <div className="glass-panel p-4 bg-white rounded-3 border">
              <EmployeeDirectory />
            </div>
          </>
        )}

        {activeTab === 'conflicts' && (
          <>
            <div className="mb-4 d-flex align-items-center gap-3">
              <button onClick={() => setActiveTab('dashboard')} className="btn btn-premium-secondary py-1 px-3 fs-6">
                ← Back
              </button>
              <div>
                <h3 className="text-gradient fw-bold mb-0">Phase 3 Conflict Detection</h3>
              </div>
            </div>
            <div className="glass-panel p-4">
              <ConflictConsole />
            </div>
          </>
        )}

        {activeTab === 'explainability' && (
          <>
            <div className="mb-4 d-flex align-items-center gap-3">
              <button onClick={() => setActiveTab('dashboard')} className="btn btn-premium-secondary py-1 px-3 fs-6">
                ← Back
              </button>
              <div>
                <h3 className="text-gradient fw-bold mb-0">Phase 4 Data Quality & Explainable AI (EDQI)</h3>
              </div>
            </div>
            <div className="glass-panel p-4">
              <DataQualityExplainability />
            </div>
          </>
        )}

      </div>
    </div>
  );
};

export default Dashboard;
