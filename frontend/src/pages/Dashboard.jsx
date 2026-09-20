import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';
import ConflictConsole from './ConflictConsole';
import DataQualityExplainability from './DataQualityExplainability';
import EmployeeDirectory from './EmployeeDirectory';
import UniversalKnowledgeAssistant from './UniversalKnowledgeAssistant';

const getFileIcon = (filename) => {
  if (!filename) return <i className="bi bi-file-earmark text-secondary me-2 fs-5"></i>;
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return <i className="bi bi-filetype-pdf text-danger me-2 fs-5"></i>;
    case 'xlsx':
    case 'xls':
      return <i className="bi bi-filetype-xlsx text-success me-2 fs-5"></i>;
    case 'csv':
      return <i className="bi bi-filetype-csv text-success me-2 fs-5"></i>;
    case 'png':
      return <i className="bi bi-filetype-png text-info me-2 fs-5"></i>;
    case 'jpg':
    case 'jpeg':
    case 'webp':
    case 'gif':
    case 'bmp':
      return <i className="bi bi-file-earmark-image text-info me-2 fs-5"></i>;
    case 'docx':
    case 'doc':
      return <i className="bi bi-filetype-docx text-primary me-2 fs-5"></i>;
    case 'json':
      return <i className="bi bi-filetype-json text-warning me-2 fs-5"></i>;
    case 'txt':
    case 'log':
      return <i className="bi bi-filetype-txt text-secondary me-2 fs-5"></i>;
    case 'xml':
      return <i className="bi bi-filetype-xml text-warning me-2 fs-5"></i>;
    case 'zip':
    case 'tar':
    case 'gz':
    case '7z':
    case 'rar':
      return <i className="bi bi-file-earmark-zip text-warning me-2 fs-5"></i>;
    case 'mp4':
    case 'mkv':
    case 'mp3':
    case 'wav':
      return <i className="bi bi-file-play text-danger me-2 fs-5"></i>;
    default:
      return <i className="bi bi-file-earmark-text text-secondary me-2 fs-5"></i>;
  }
};

const Dashboard = () => {
  const { user, logout } = useAuth();
  const rowsPerPage = 10;
  
  // Navigation active tab: 'dashboard' | 'repository' | 'employees' | 'conflicts' | 'explainability' | 'knowledge-assistant'
  const [activeTab, setActiveTab] = useState('dashboard');

  // Enterprise Data Repository States
  const [selectedRepoType, setSelectedRepoType] = useState('team'); // 'team' | 'personal'
  const [currentFolderId, setCurrentFolderId] = useState(null);
  const [explorerData, setExplorerData] = useState({
    current_folder: null,
    breadcrumbs: [{ id: null, name: 'Root' }],
    current_logical_path: 'Team/',
    subfolders: [],
    documents: []
  });
  const [loadingExplorer, setLoadingExplorer] = useState(false);
  const [repoError, setRepoError] = useState('');
  const [repoSuccess, setRepoSuccess] = useState('');
  const [toastMsg, setToastMsg] = useState('');

  // Modals state
  const [showNewFolderModal, setShowNewFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [targetFolderId, setTargetFolderId] = useState(null);
  const [targetFolderPath, setTargetFolderPath] = useState('');

  const [showRecycleBin, setShowRecycleBin] = useState(false);
  const [recycleBinData, setRecycleBinData] = useState({ folders: [], documents: [] });
  const [loadingRecycleBin, setLoadingRecycleBin] = useState(false);

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadMode, setUploadMode] = useState('file'); // 'file' | 'folder'
  const [selectedFile, setSelectedFile] = useState(null);
  const [folderFiles, setFolderFiles] = useState([]);
  const [parserType, setParserType] = useState('auto');
  const [dragActive, setDragActive] = useState(false);

  // Modal Launchers with explicitly targeted subfolder path context
  const openNewFolderModal = (folderId = null, path = null) => {
    setTargetFolderId(folderId !== null ? folderId : currentFolderId);
    setTargetFolderPath(path !== null ? path : (explorerData.current_logical_path || 'Team/'));
    setNewFolderName('');
    setShowNewFolderModal(true);
  };

  const openUploadModal = (mode = 'file', folderId = null, path = null) => {
    setUploadMode(mode);
    setTargetFolderId(folderId !== null ? folderId : currentFolderId);
    setTargetFolderPath(path !== null ? path : (explorerData.current_logical_path || 'Team/'));
    setSelectedFile(null);
    setFolderFiles([]);
    setPipelineResult(null);
    setPipelineError('');
    setShowUploadModal(true);
  };

  // Ingestion Pipeline Status Monitor
  const [processing, setProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [pipelineResult, setPipelineResult] = useState(null);
  const [pipelineError, setPipelineError] = useState('');
  const [resultTab, setResultTab] = useState('record'); // 'record' | 'metadata' | 'stages'
  const pollingRef = useRef(null);

  // File Previewer & Record Inspector
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [selectedDocDetails, setSelectedDocDetails] = useState({
    records: [],
    versions: [],
    audit: []
  });
  const [activeDetailsTab, setActiveDetailsTab] = useState('records');
  const [previewingDoc, setPreviewingDoc] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [csvPage, setCsvPage] = useState(1);
  const [activeExcelSheet, setActiveExcelSheet] = useState('');
  const [imageZoom, setImageZoom] = useState(100);

  // JSONB Records Query Engine
  const [repoTabMode, setRepoTabMode] = useState('explorer'); // 'explorer' | 'search'
  const [globalRecords, setGlobalRecords] = useState([]);
  const [loadingGlobalRecords, setLoadingGlobalRecords] = useState(false);
  const [searchField, setSearchField] = useState('');
  const [searchValue, setSearchValue] = useState('');
  const [searchContains, setSearchContains] = useState('');
  const [editingRecordId, setEditingRecordId] = useState(null);
  const [editingDataJson, setEditingDataJson] = useState('');

  // Toast feedback helper
  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 4000);
  };

  // Copy Logical Path helper
  const copyLogicalPath = (path) => {
    if (!path) return;
    navigator.clipboard.writeText(path);
    showToast(`Logical path copied to clipboard: ${path}`);
  };

  // Stop Polling helper
  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    return () => stopPolling();
  }, []);

  // Poll ingestion status when upload modal shows PROCESSING status
  useEffect(() => {
    let interval = null;
    if (showUploadModal && pipelineResult && pipelineResult.document_id && pipelineResult.processing_status === 'PROCESSING') {
      interval = setInterval(async () => {
        try {
          const res = await client.get(`ingestion/status/${pipelineResult.document_id}/`);
          if (res.data && res.data.success) {
            const newStatus = res.data.processing_status;
            setPipelineResult(prev => ({
              ...prev,
              processing_status: newStatus,
              pipeline_result: {
                standardized_record: res.data.standardized_preview || prev.pipeline_result?.standardized_record || {},
                metadata: res.data.metadata || prev.pipeline_result?.metadata || {},
                stage_execution: res.data.stage_execution || prev.pipeline_result?.stage_execution || {}
              }
            }));
            if (newStatus === 'COMPLETED' || newStatus === 'FAILED') {
              clearInterval(interval);
              fetchExplorer();
            }
          }
        } catch (e) {
          // Ignore transient status poll error
        }
      }, 2500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [showUploadModal, pipelineResult?.document_id, pipelineResult?.processing_status]);

  // Fetch Explorer Contents
  const fetchExplorer = async (repoType = selectedRepoType, folderId = currentFolderId) => {
    setLoadingExplorer(true);
    setRepoError('');
    try {
      let url = `repository/explorer/?repository_type=${repoType}`;
      if (folderId) {
        url += `&folder_id=${folderId}`;
      }
      const res = await client.get(url);
      if (res.data && res.data.success) {
        setExplorerData(res.data.data);
      }
    } catch (err) {
      setRepoError('Failed to load repository folder explorer.');
    } finally {
      setLoadingExplorer(false);
    }
  };

  // Re-fetch explorer when tab, repository type, or folder changes
  useEffect(() => {
    if (activeTab === 'repository') {
      fetchExplorer(selectedRepoType, currentFolderId);
    }
  }, [activeTab, selectedRepoType, currentFolderId]);

  // Handle repository switch (Team vs Personal)
  const handleSwitchRepoType = (newType) => {
    setSelectedRepoType(newType);
    setCurrentFolderId(null);
    setSelectedDoc(null);
    setPreviewingDoc(null);
  };

  // Create New Folder
  const handleCreateFolder = async (e) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    setCreatingFolder(true);
    setRepoError('');
    const effectiveParentId = targetFolderId !== null ? targetFolderId : currentFolderId;
    try {
      const res = await client.post('repository/folders/', {
        name: newFolderName.trim(),
        repository_type: selectedRepoType,
        parent: effectiveParentId,
        parent_id: effectiveParentId,
        parent_path: targetFolderPath || explorerData.current_logical_path
      });
      if (res.data && res.data.success) {
        setRepoSuccess(`Folder "${newFolderName}" created successfully.`);
        setNewFolderName('');
        setShowNewFolderModal(false);
        fetchExplorer();
      }
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.name?.[0] || 'Failed to create folder.';
      setRepoError(msg);
    } finally {
      setCreatingFolder(false);
    }
  };

  // Soft Delete Document
  const softDeleteDocument = async (docId, docTitle) => {
    if (!window.confirm(`Are you sure you want to soft delete "${docTitle}"? It will be moved to the Recycle Bin.`)) {
      return;
    }
    try {
      await client.delete(`repository/documents/${docId}/`);
      showToast(`Document "${docTitle}" moved to Recycle Bin.`);
      if (selectedDoc?.id === docId) setSelectedDoc(null);
      if (previewingDoc?.id === docId) setPreviewingDoc(null);
      fetchExplorer();
    } catch (err) {
      setRepoError('Failed to soft delete document. Insufficient permissions.');
    }
  };

  // Soft Delete Folder
  const softDeleteFolder = async (folderId, folderName) => {
    if (!window.confirm(`Are you sure you want to delete folder "${folderName}" and all its contents? Items will be moved to Recycle Bin.`)) {
      return;
    }
    try {
      await client.delete(`repository/folders/${folderId}/`);
      showToast(`Folder "${folderName}" moved to Recycle Bin.`);
      fetchExplorer();
    } catch (err) {
      setRepoError('Failed to delete folder.');
    }
  };

  // Fetch Recycle Bin
  const fetchRecycleBin = async () => {
    setLoadingRecycleBin(true);
    try {
      const res = await client.get('repository/recycle-bin/');
      if (res.data && res.data.success) {
        setRecycleBinData(res.data.data);
      }
    } catch (err) {
      setRepoError('Failed to fetch Recycle Bin items.');
    } finally {
      setLoadingRecycleBin(false);
    }
  };

  const openRecycleBinModal = () => {
    setShowRecycleBin(true);
    fetchRecycleBin();
  };

  // Restore Item
  const handleRestoreItem = async (type, id) => {
    try {
      const endpoint = type === 'folder' ? `repository/folders/${id}/restore/` : `repository/documents/${id}/restore/`;
      const res = await client.post(endpoint);
      if (res.data && res.data.success) {
        showToast('Item restored successfully.');
        fetchRecycleBin();
        fetchExplorer();
      }
    } catch (err) {
      setRepoError('Failed to restore item.');
    }
  };

  // Permanent Delete Item
  const handlePermanentDelete = async (type, id, title) => {
    if (!window.confirm(`WARNING: Permanently delete "${title}"? This cannot be undone.`)) {
      return;
    }
    try {
      const endpoint = type === 'folder' ? `repository/folders/${id}/permanent_delete/` : `repository/documents/${id}/permanent_delete/`;
      await client.delete(endpoint);
      showToast('Item permanently deleted.');
      fetchRecycleBin();
    } catch (err) {
      setRepoError('Failed to permanently delete item.');
    }
  };

  // Delete All Items in active folder / repository
  const deleteAllRepositoryItems = async () => {
    const scopeLabel = currentFolderId ? 'current folder' : `${selectedRepoType.toUpperCase()} repository`;
    if (!window.confirm(`Are you sure you want to move all files and folders in the ${scopeLabel} to the Recycle Bin?`)) {
      return;
    }
    setLoadingExplorer(true);
    try {
      const res = await client.post('repository/documents/delete_all/', {
        repository_type: selectedRepoType,
        folder_id: currentFolderId || ''
      });
      if (res.data && res.data.success) {
        showToast(res.data.message || 'All items moved to Recycle Bin.');
        fetchExplorer();
      } else {
        setRepoError(res.data.message || 'Failed to delete items.');
      }
    } catch (err) {
      setRepoError(err.response?.data?.message || 'Failed to delete items.');
    } finally {
      setLoadingExplorer(false);
    }
  };

  // Empty / Purge All items in Recycle Bin
  const emptyRecycleBin = async () => {
    if (!window.confirm("Are you sure you want to permanently purge ALL items from the Recycle Bin? This action cannot be undone.")) {
      return;
    }
    setLoadingRecycleBin(true);
    try {
      const res = await client.delete('repository/recycle-bin/');
      if (res.data && res.data.success) {
        showToast(res.data.message || 'Recycle Bin emptied cleanly.');
        fetchRecycleBin();
        fetchExplorer();
      } else {
        showToast('Failed to empty Recycle Bin.');
      }
    } catch (err) {
      showToast(err.response?.data?.message || 'Failed to empty Recycle Bin.');
    } finally {
      setLoadingRecycleBin(false);
    }
  };

  // Ingestion Pipeline Polling
  const pollStatus = async (docId) => {
    try {
      const res = await client.get(`ingestion/status/${docId}/`);
      const d = res.data;
      if (d && d.success) {
        setPipelineResult({
          document_id: d.document_id,
          file_name: d.file_name,
          file_size: d.file_size,
          processing_status: d.processing_status,
          current_stage: d.current_stage,
          last_failed_stage: d.last_failed_stage,
          elapsed_time: d.elapsed_time,
          pipeline_result: {
            stage_execution: d.stage_execution || {},
            pipeline_duration: d.elapsed_time,
            metadata: d.metadata || {},
            standardized_record: d.standardized_preview
          }
        });

        if (d.processing_status === 'COMPLETED') {
          stopPolling();
          setProcessing(false);
          if (targetFolderId !== null && targetFolderId !== currentFolderId) {
            setCurrentFolderId(targetFolderId);
          } else {
            fetchExplorer();
          }
        } else if (d.processing_status === 'FAILED') {
          stopPolling();
          setProcessing(false);
          setPipelineError(`Pipeline failed at stage: ${d.last_failed_stage || 'Persistence'}`);
        }
      }
    } catch (err) {
      console.error("Error polling document status:", err);
    }
  };

  const startPolling = (docId) => {
    stopPolling();
    pollStatus(docId);
    pollingRef.current = setInterval(() => pollStatus(docId), 1500);
  };

  // File / Folder Upload Handler
  const handleUploadSubmit = async (e) => {
    if (e) e.preventDefault();
    setPipelineError('');
    setPipelineResult(null);

    const effectiveFolderId = targetFolderId !== null ? targetFolderId : currentFolderId;
    const effectivePath = targetFolderPath || explorerData.current_logical_path;

    if (uploadMode === 'file') {
      if (!selectedFile) {
        setPipelineError('Please select a file to upload.');
        return;
      }
      setProcessing(true);
      setUploadProgress('Uploading document...');
      
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('repository_type', selectedRepoType);
      if (effectiveFolderId) formData.append('folder_id', effectiveFolderId);
      if (effectivePath) formData.append('target_logical_path', effectivePath);
      if (parserType !== 'auto') formData.append('parser_type', parserType);

      try {
        const response = await client.post('ingestion/upload/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        if (response.data && response.data.success) {
          setPipelineResult(response.data.data);
          setProcessing(false);
          showToast('File uploaded successfully!');
          fetchExplorer();
        } else {
          setPipelineError(response.data.message || 'File upload failed.');
          setProcessing(false);
        }
      } catch (err) {
        setPipelineError(err.response?.data?.message || err.message || 'File upload failed.');
        setProcessing(false);
      }
    } else {
      // Folder upload mode (webkitdirectory)
      if (!folderFiles || folderFiles.length === 0) {
        setPipelineError('Please select a folder to upload.');
        return;
      }
      setProcessing(true);
      const total = folderFiles.length;
      let completed = 0;
      const batchDocIds = [];

      for (let i = 0; i < total; i++) {
        const f = folderFiles[i];
        setUploadProgress(`Uploading item ${i + 1} of ${total}: ${f.name}...`);
        
        const formData = new FormData();
        formData.append('file', f);
        formData.append('repository_type', selectedRepoType);
        if (effectiveFolderId) formData.append('folder_id', effectiveFolderId);
        if (effectivePath) formData.append('target_logical_path', effectivePath);
        if (f.webkitRelativePath) formData.append('relative_path', f.webkitRelativePath);
        if (parserType !== 'auto') formData.append('parser_type', parserType);

        try {
          const res = await client.post('ingestion/upload/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          if (res.data && res.data.success && res.data.data?.document_id) {
            batchDocIds.push(res.data.data.document_id);
          }
        } catch (err) {
          console.error(`Folder item ${f.name} upload failed:`, err);
        }
        completed++;
        await new Promise(r => setTimeout(r, 100));
      }

      setProcessing(false);
      setShowUploadModal(false);
      showToast(`Uploaded ${completed} items from folder. Ingestion running in background.`);
      if (targetFolderId !== null && targetFolderId !== currentFolderId) {
        setCurrentFolderId(targetFolderId);
      } else {
        fetchExplorer();
      }
    }
  };

  // Drag and drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setUploadMode('file');
      setPipelineError('');
    }
  };

  // Document Details & Technical Records Viewer
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
      setRepoError('Failed loading document sub-elements.');
    }
  };

  // File Previewer
  const fetchFilePreview = async (doc) => {
    setPreviewingDoc(doc);
    setLoadingPreview(true);
    setPreviewError('');
    setPreviewData(null);
    setCsvPage(1);
    setActiveExcelSheet('');
    try {
      const ext = doc.title.split('.').pop().toLowerCase();
      if (['pdf', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'].includes(ext)) {
        const res = await client.get(`repository/documents/${doc.id}/view_file/`, {
          responseType: 'blob'
        });
        const blobUrl = URL.createObjectURL(res.data);
        setPreviewData({
          file_type: ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'].includes(ext) ? 'image' : 'pdf',
          url: blobUrl
        });
      } else {
        const res = await client.get(`repository/documents/${doc.id}/view_file/`);
        const data = res.data.results || res.data.data || res.data;
        setPreviewData(data);
        if (data.file_type === 'excel' && data.sheets) {
          const sheetNames = Object.keys(data.sheets);
          if (sheetNames.length > 0) setActiveExcelSheet(sheetNames[0]);
        }
      }
    } catch (err) {
      setPreviewError('Failed to load file preview.');
    } finally {
      setLoadingPreview(false);
    }
  };

  // Secure File Download
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

  // Database Records Query Engine
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
      await client.put(`repository/records/${recordId}/`, { canonical_data: parsedData });
      showToast('Record fields updated successfully.');
      setEditingRecordId(null);
      if (isGlobal) executeRecordsQuery();
      else if (selectedDoc) fetchDocumentSubDetails(selectedDoc);
    } catch (err) {
      setRepoError('Validation failed. Ensure formatting represents correct JSON string.');
    }
  };

  const handleDeleteRecord = async (recordId, isGlobal = false) => {
    if (!window.confirm("Are you sure you want to delete this canonical entry?")) return;
    try {
      await client.delete(`repository/records/${recordId}/`);
      showToast('Record deleted from database.');
      if (isGlobal) executeRecordsQuery();
      else if (selectedDoc) fetchDocumentSubDetails(selectedDoc);
    } catch (err) {
      setRepoError('Deletion failed.');
    }
  };

  return (
    <div className="container-fluid min-vh-100 p-0" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Toast Notification Floating Banner */}
      {toastMsg && (
        <div 
          className="position-fixed bottom-0 end-0 p-3" 
          style={{ zIndex: 9999 }}
        >
          <div className="toast show align-items-center text-white bg-dark border border-success shadow-lg" role="alert">
            <div className="d-flex">
              <div className="toast-body font-monospace small">
                📋 {toastMsg}
              </div>
              <button type="button" className="btn-close btn-close-white me-2 m-auto" onClick={() => setToastMsg('')}></button>
            </div>
          </div>
        </div>
      )}

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
            <div className="navbar-nav d-flex flex-row gap-2">
              <button 
                className={`btn btn-sm px-3 fw-bold ${activeTab === 'repository' ? 'btn-premium-primary text-white' : 'btn-link text-dark text-decoration-none opacity-75'}`} 
                onClick={() => setActiveTab('repository')}
              >
                <i className="bi bi-folder-fill text-warning me-1"></i> Enterprise Data Repository
              </button>
              <button 
                className={`btn btn-sm px-3 fw-bold ${activeTab === 'employees' ? 'btn-premium-primary text-white' : 'btn-link text-dark text-decoration-none opacity-75'}`} 
                onClick={() => setActiveTab('employees')}
              >
                Employee Directory
              </button>
              <button 
                className={`btn btn-sm px-3 fw-bold ${activeTab === 'explainability' ? 'btn-premium-primary text-white' : 'btn-link text-dark text-decoration-none opacity-75'}`} 
                onClick={() => setActiveTab('explainability')}
              >
                Data Quality Report
              </button>
              <button 
                className={`btn btn-sm px-3 fw-bold ${activeTab === 'conflicts' ? 'btn-premium-primary text-white' : 'btn-link text-dark text-decoration-none opacity-75'}`} 
                onClick={() => setActiveTab('conflicts')}
              >
                Check Data Conflicts
              </button>
              <button 
                className={`btn btn-sm px-3 fw-bold ${activeTab === 'knowledge-assistant' ? 'btn-premium-primary text-white' : 'btn-link text-dark text-decoration-none opacity-75'}`} 
                onClick={() => setActiveTab('knowledge-assistant')}
              >
                <i className="bi bi-robot text-primary me-1"></i> Phase 5 Knowledge Assistant
              </button>
            </div>
          </div>
          <div className="d-flex align-items-center gap-3">
            <span className="badge bg-success py-2 px-3 text-uppercase font-monospace fw-bold" style={{ fontSize: '0.75rem', letterSpacing: '1px' }}>
              Role: {user?.role}
            </span>
            <span className="text-dark small fw-bold">Welcome, {user?.username}</span>
            <button onClick={logout} className="btn btn-premium-secondary btn-sm py-1 px-3">Logout</button>
          </div>
        </div>
      </nav>

      {/* Main Container */}
      <div className="container py-4 px-3">
        
        {/* DASHBOARD HOME VIEW */}
        {activeTab === 'dashboard' && (
          <>
            <div className="mb-5 text-center text-md-start">
              <h2 className="text-success fw-bold mb-2">Decision Intelligence Console</h2>
              <p className="text-dark opacity-75 fw-medium">Enterprise-grade platform shell ready for trusted business metrics. Manage files, query knowledge, and audit records below.</p>
            </div>

            <div className="row g-4">
              {/* Enterprise Data Repository Card */}
              <div className="col-12 col-md-6 col-lg-4">
                <div 
                  className="glass-card p-4 h-100 d-flex flex-column justify-content-between cursor-pointer border border-success border-opacity-50"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveTab('repository')}
                >
                  <div>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="fw-bold text-success mb-0">Enterprise Data Repository</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>UNIFIED</span>
                    </div>
                    <p className="text-dark opacity-75 small">Unified file explorer, logical path manager (`Team/Projects/...`), single & folder uploading, real-time ingestion status monitor, and soft-delete recycle bin.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-success fw-bold small">Launch Repository Workspace →</span>
                  </div>
                </div>
              </div>

              {/* Employee Directory Card */}
              <div className="col-12 col-md-6 col-lg-4">
                <div 
                  className="glass-card p-4 h-100 d-flex flex-column justify-content-between cursor-pointer"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveTab('employees')}
                >
                  <div>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="fw-bold text-dark mb-0">Employee Directory</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>ACTIVE</span>
                    </div>
                    <p className="text-dark opacity-75 small">Access searchable directory of team members, roles, current projects, and domain expert skills.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-primary fw-bold small">Launch Employee Directory →</span>
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
                      <h5 className="fw-bold text-dark mb-0">Check Data Conflicts</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>ACTIVE</span>
                    </div>
                    <p className="text-dark opacity-75 small">Analyzes semantic consistency to detect contradictory, duplicate, and outdated knowledge.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-primary fw-bold small">Launch Conflict Workspace →</span>
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
                      <h5 className="fw-bold text-dark mb-0">Data Quality Report</h5>
                      <span className="badge bg-success font-monospace" style={{ fontSize: '0.7rem' }}>ACTIVE</span>
                    </div>
                    <p className="text-dark opacity-75 small">Evaluates data quality using ML classification and generates SHAP explainability attributions with recommendations.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-primary fw-bold small">Launch Quality & XAI Workspace →</span>
                  </div>
                </div>
              </div>

              {/* Universal Knowledge Assistant Card */}
              <div className="col-12 col-md-6 col-lg-4">
                <div 
                  className="glass-card p-4 h-100 d-flex flex-column justify-content-between cursor-pointer border border-primary border-opacity-50"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveTab('knowledge-assistant')}
                >
                  <div>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="fw-bold text-primary mb-0"><i className="bi bi-robot me-1"></i> Knowledge Assistant</h5>
                      <span className="badge bg-primary font-monospace text-white" style={{ fontSize: '0.7rem' }}>PHASE 5</span>
                    </div>
                    <p className="text-dark opacity-75 small">RAG-grounded natural language question-answering with local LLMs, FAISS vector index, and logical file/folder path resolution.</p>
                  </div>
                  <div className="border-top border-secondary pt-3 mt-3 d-flex justify-content-between align-items-center">
                    <span className="text-primary fw-bold small">Launch Knowledge Assistant →</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ENTERPRISE DATA REPOSITORY VIEW (PHASE 1 + PHASE 2 UNIFIED) */}
        {activeTab === 'repository' && (
          <>
            {/* Header Toolbar */}
            <div className="mb-4 d-flex flex-wrap align-items-center justify-content-between gap-3">
              <div className="d-flex align-items-center gap-3">
                <button onClick={() => setActiveTab('dashboard')} className="btn btn-premium-secondary py-1 px-3 fs-6">
                  ← Back
                </button>
                <div>
                  <h3 className="text-gradient fw-bold mb-0">Enterprise Data Repository</h3>
                  <p className="text-secondary small mb-0">Manage logical folders, files, copy path targets, ingestion pipelines, and soft-delete recycle bin.</p>
                </div>
              </div>
              
              <div className="d-flex gap-2">
                <div className="btn-group border border-secondary rounded overflow-hidden">
                  <button 
                    className={`btn py-2 px-3 border-0 rounded-0 ${repoTabMode === 'explorer' ? 'btn-premium-primary' : 'btn-dark text-secondary'}`}
                    onClick={() => setRepoTabMode('explorer')}
                  >
                    📁 Explorer View
                  </button>
                  <button 
                    className={`btn py-2 px-3 border-0 rounded-0 ${repoTabMode === 'search' ? 'btn-premium-primary' : 'btn-dark text-secondary'}`}
                    onClick={() => setRepoTabMode('search')}
                  >
                    🔍 Database Records (JSONB)
                  </button>
                </div>
              </div>
            </div>

            {/* General Errors / Successes */}
            {repoError && (
              <div className="alert alert-danger border border-danger-subtle text-danger mb-3 d-flex justify-content-between align-items-center fw-bold">
                <span>🛑 {repoError}</span>
                <button className="btn btn-sm text-danger border-0" onClick={() => setRepoError('')}>×</button>
              </div>
            )}
            {repoSuccess && (
              <div className="alert alert-success border border-success-subtle text-success mb-3 d-flex justify-content-between align-items-center fw-bold">
                <span>✓ {repoSuccess}</span>
                <button className="btn btn-sm text-success border-0" onClick={() => setRepoSuccess('')}>×</button>
              </div>
            )}

            {repoTabMode === 'explorer' ? (
              <div className="d-flex flex-column gap-4">
                
                {/* Windows File Explorer Command Bar & Path Bar */}
                <div className="glass-panel p-3 shadow-sm rounded-3 bg-white border">
                  <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
                    
                    {/* Repository Mode Slider (Team vs Personal) */}
                    <div className="d-flex align-items-center bg-light p-1 rounded-3 border border-secondary-subtle">
                      <button 
                        className={`btn btn-sm py-1 px-4 rounded-2 border-0 fw-bold transition-all ${selectedRepoType === 'team' ? 'bg-success text-white shadow-sm' : 'text-dark'}`}
                        onClick={() => handleSwitchRepoType('team')}
                      >
                        🏢 Team Repository (Shared)
                      </button>
                      <button 
                        className={`btn btn-sm py-1 px-4 rounded-2 border-0 fw-bold transition-all ${selectedRepoType === 'personal' ? 'bg-info text-white shadow-sm' : 'text-dark'}`}
                        onClick={() => handleSwitchRepoType('personal')}
                      >
                        🔒 Personal Workspace
                      </button>
                    </div>

                    {/* Windows Explorer Style Command Toolbar */}
                    <div className="d-flex flex-wrap align-items-center gap-2">
                      
                      {/* + New Folder Button */}
                      <button 
                        className="btn btn-sm btn-success fw-bold d-flex align-items-center gap-1 text-white shadow-sm"
                        onClick={() => openNewFolderModal(currentFolderId, explorerData.current_logical_path)}
                        title="Create a new subfolder in current location"
                      >
                        <i className="bi bi-folder-plus text-white fs-6"></i> + New Folder
                      </button>

                      {/* Upload File Button */}
                      <button 
                        className="btn btn-sm btn-primary fw-bold d-flex align-items-center gap-1 text-white shadow-sm"
                        onClick={() => openUploadModal('file', currentFolderId, explorerData.current_logical_path)}
                        title="Upload file into current location"
                      >
                        <i className="bi bi-file-earmark-arrow-up text-white fs-6"></i> Upload File
                      </button>

                      {/* Upload Folder Tree Button */}
                      <button 
                        className="btn btn-sm btn-outline-primary fw-bold d-flex align-items-center gap-1"
                        onClick={() => openUploadModal('folder', currentFolderId, explorerData.current_logical_path)}
                        title="Upload local folder tree structure"
                      >
                        <i className="bi bi-folder-symlink fs-6"></i> Upload Folder Tree
                      </button>

                      <div className="vr mx-1 opacity-25"></div>

                      {/* Copy Path */}
                      <button 
                        className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
                        onClick={() => copyLogicalPath(explorerData.current_logical_path)}
                        title="Copy Logical Path for Assistant"
                      >
                        <i className="bi bi-clipboard text-secondary"></i> Copy Path
                      </button>

                      {/* Recycle Bin */}
                      <button 
                        className="btn btn-sm btn-outline-warning d-flex align-items-center gap-1"
                        onClick={openRecycleBinModal}
                        title="View soft-deleted items"
                      >
                        <i className="bi bi-recycle text-warning"></i> Recycle Bin
                      </button>

                      {/* Refresh */}
                      <button 
                        className="btn btn-sm btn-outline-dark d-flex align-items-center gap-1"
                        onClick={() => fetchExplorer()}
                        disabled={loadingExplorer}
                        title="Refresh explorer directory"
                      >
                        <i className="bi bi-arrow-clockwise text-success"></i> Refresh
                      </button>

                      {/* Delete All Files */}
                      <button 
                        className="btn btn-sm btn-outline-danger d-flex align-items-center gap-1"
                        onClick={deleteAllRepositoryItems}
                        title="Move all items in current directory to Recycle Bin"
                      >
                        <i className="bi bi-trash3 text-danger"></i> Purge All
                      </button>
                    </div>

                  </div>

                  {/* Windows File Manager Address Bar */}
                  <div className="mt-3 pt-2 border-top border-secondary-subtle d-flex align-items-center justify-content-between bg-light px-3 py-2 rounded-2 border">
                    <div className="d-flex align-items-center gap-2 font-monospace small">
                      <i className="bi bi-folder2-open text-warning fs-5"></i>
                      <span className="text-secondary fw-semibold">Address:</span>
                      <nav aria-label="breadcrumb">
                        <ol className="breadcrumb mb-0">
                          {(explorerData.breadcrumbs || []).map((bc, idx) => {
                            const isLast = idx === (explorerData.breadcrumbs.length - 1);
                            return (
                              <li key={idx} className={`breadcrumb-item ${isLast ? 'active text-success fw-bold' : ''}`}>
                                {isLast ? (
                                  <span>{bc.name}</span>
                                ) : (
                                  <span 
                                    className="text-primary cursor-pointer text-decoration-underline fw-medium" 
                                    style={{ cursor: 'pointer' }}
                                    onClick={() => setCurrentFolderId(bc.id)}
                                  >
                                    {bc.name}
                                  </span>
                                )}
                              </li>
                            );
                          })}
                        </ol>
                      </nav>
                    </div>

                    <div className="font-monospace small text-secondary">
                      Logical Path: <span className="text-dark bg-white px-2 py-1 rounded border fw-bold">{explorerData.current_logical_path}</span>
                    </div>
                  </div>
                </div>

                {/* File Explorer Table View & Details Side Panel */}
                <div className="row g-4">
                  
                  {/* Left Column: Explorer Directory Listing */}
                  <div className="col-12 col-lg-7">
                    <div className="glass-panel p-4 h-100">
                      <div className="d-flex justify-content-between align-items-center mb-3">
                        <h5 className="fw-bold text-dark mb-0 font-monospace">
                          {selectedRepoType === 'team' ? '🏢 Team Files & Folders' : '🔒 Personal Workspace'}
                        </h5>
                        <span className="text-secondary small font-monospace">
                          {(explorerData.subfolders?.length || 0)} folders, {(explorerData.documents?.length || 0)} files
                        </span>
                      </div>

                      {loadingExplorer ? (
                        <div className="text-center py-5 text-secondary">
                          <span className="spinner-border spinner-border-sm me-2 text-info"></span>
                          Reading repository explorer directory...
                        </div>
                      ) : (explorerData.subfolders?.length === 0 && explorerData.documents?.length === 0) ? (
                        <div className="text-center py-5 text-muted border border-dashed rounded-3 p-4">
                          <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mb-2 opacity-50">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                          </svg>
                          <p className="fw-semibold text-dark mb-1">This folder is empty</p>
                          <p className="small text-secondary mb-3">Upload files or create subfolders to organize enterprise documents.</p>
                          <div className="d-flex justify-content-center gap-2 mt-3">
                            <button 
                              className="btn btn-sm btn-premium-primary d-flex align-items-center gap-1" 
                              onClick={() => openUploadModal('file', currentFolderId, explorerData.current_logical_path)}
                            >
                              <i className="bi bi-upload text-white"></i> Upload File Here
                            </button>
                            <button 
                              className="btn btn-sm btn-outline-success d-flex align-items-center gap-1" 
                              onClick={() => openNewFolderModal(currentFolderId, explorerData.current_logical_path)}
                            >
                              <i className="bi bi-folder-plus text-success"></i> + Create Subfolder Here
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="table-responsive">
                          <table className="table table-hover align-middle table-sm border-0">
                            <thead className="bg-light text-dark fw-bold font-monospace border-bottom border-secondary">
                              <tr className="small">
                                <th className="text-dark">Item Name</th>
                                <th className="text-dark">Type</th>
                                <th className="text-dark">Logical Path</th>
                                <th className="text-end text-dark">Actions</th>
                              </tr>
                            </thead>
                            <tbody className="small font-monospace">
                              {/* Parent Folder Row if not root */}
                              {currentFolderId && (
                                <tr 
                                  className="cursor-pointer bg-light" 
                                  style={{ cursor: 'pointer' }}
                                  onClick={() => {
                                    const bcs = explorerData.breadcrumbs || [];
                                    if (bcs.length >= 2) {
                                      setCurrentFolderId(bcs[bcs.length - 2].id);
                                    } else {
                                      setCurrentFolderId(null);
                                    }
                                  }}
                                >
                                  <td colSpan="4" className="text-success fw-bold">
                                    <i className="bi bi-arrow-up-circle-fill text-success me-2 fs-5"></i> .. (Parent Folder)
                                  </td>
                                </tr>
                              )}

                              {/* Render Subfolders */}
                              {explorerData.subfolders?.map((folder) => (
                                <tr 
                                  key={folder.id} 
                                  className="cursor-pointer align-middle hover-shadow"
                                  style={{ cursor: 'pointer' }}
                                  onClick={() => setCurrentFolderId(folder.id)}
                                >
                                  <td className="fw-bold text-dark text-truncate" style={{ maxWidth: '220px' }}>
                                    <i className="bi bi-folder-fill text-warning me-2 fs-5"></i> {folder.name}
                                  </td>
                                  <td><span className="badge bg-warning text-dark fw-bold">FOLDER</span></td>
                                  <td className="text-secondary text-truncate" style={{ maxWidth: '180px' }} title={folder.logical_path}>
                                    {folder.logical_path}
                                  </td>
                                  <td className="text-end" onClick={(e) => e.stopPropagation()}>
                                    <div className="d-flex gap-1 justify-content-end align-items-center">
                                      <button 
                                        className="btn btn-sm btn-outline-primary py-0 px-2 fw-semibold"
                                        onClick={() => setCurrentFolderId(folder.id)}
                                        title="Open Folder"
                                      >
                                        Open
                                      </button>
                                      <button 
                                        className="btn btn-sm btn-outline-secondary py-0 px-2"
                                        onClick={() => copyLogicalPath(folder.logical_path)}
                                        title="Copy folder logical path"
                                      >
                                        Copy Path
                                      </button>
                                      <button 
                                        className="btn btn-sm btn-outline-danger py-0 px-2 border-0"
                                        onClick={() => softDeleteFolder(folder.id, folder.name)}
                                        title="Delete folder to Recycle Bin"
                                      >
                                        <i className="bi bi-trash text-danger"></i>
                                      </button>
                                    </div>
                                  </td>
                                </tr>
                              ))}

                              {/* Render Documents with extension-specific icons */}
                              {explorerData.documents?.map((doc) => {
                                const ext = (doc.title || '').split('.').pop()?.toUpperCase() || 'FILE';
                                const icon = getFileIcon(doc.title);
                                return (
                                  <tr 
                                    key={doc.id} 
                                    className={`cursor-pointer ${selectedDoc?.id === doc.id ? 'table-active' : ''}`}
                                    onClick={() => fetchDocumentSubDetails(doc)}
                                  >
                                    <td className="fw-medium text-dark text-truncate" style={{ maxWidth: '200px' }}>
                                      {icon} {doc.title}
                                    </td>
                                    <td><span className="badge bg-light text-dark border border-secondary fw-bold">{ext}</span></td>
                                    <td className="text-secondary text-truncate" style={{ maxWidth: '180px' }} title={doc.logical_path}>
                                      {doc.logical_path}
                                    </td>
                                    <td className="text-end" onClick={(e) => e.stopPropagation()}>
                                      <div className="d-flex gap-1 justify-content-end">
                                        <button 
                                          className="btn btn-sm btn-outline-info py-0 px-2"
                                          onClick={() => copyLogicalPath(doc.logical_path)}
                                          title="Copy file logical path for Knowledge Assistant"
                                        >
                                          Copy Path
                                        </button>
                                        <button 
                                          className="btn btn-sm btn-premium-primary py-0 px-2"
                                          onClick={() => fetchFilePreview(doc)}
                                        >
                                          View
                                        </button>
                                        <button 
                                          className="btn btn-sm btn-outline-danger py-0 px-2 border-0"
                                          onClick={() => softDeleteDocument(doc.id, doc.title)}
                                          title="Delete document to Recycle Bin"
                                        >
                                          <i className="bi bi-trash text-danger"></i>
                                        </button>
                                      </div>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Selected Document Inspector & High-Contrast Details Card */}
                  <div className="col-12 col-lg-5">
                    <div className="glass-panel p-4 h-100 d-flex flex-column" style={{ minHeight: '400px' }}>
                      {selectedDoc ? (
                        <>
                          <div className="d-flex justify-content-between align-items-start mb-3 border-bottom border-secondary pb-3">
                            <div>
                              <h5 className="fw-bold text-dark mb-1">{getFileIcon(selectedDoc.title)} {selectedDoc.title}</h5>
                              <span className="badge bg-light border border-secondary text-success font-monospace small">
                                {selectedDoc.logical_path}
                              </span>
                            </div>
                            <button className="btn btn-premium-primary btn-sm py-1 px-3" onClick={() => fetchFilePreview(selectedDoc)}>
                              Open Viewer
                            </button>
                          </div>

                          {/* High-Contrast Styled File Details Box */}
                          <div className="bg-light p-3 rounded-3 border border-secondary mb-3">
                            <div className="d-flex flex-column gap-2 font-monospace small">
                              <div className="d-flex justify-content-between align-items-center">
                                <span className="text-dark fw-medium">File Format:</span>
                                <span className="text-success fw-bold">
                                  {getFileIcon(selectedDoc.title)} {(selectedDoc.title || '').split('.').pop()?.toUpperCase() || 'FILE'}
                                </span>
                              </div>
                              <div className="d-flex justify-content-between align-items-center">
                                <span className="text-dark fw-medium">Version:</span>
                                <span className="text-success fw-bold">v{selectedDoc.current_version}</span>
                              </div>
                              <div className="d-flex justify-content-between align-items-center">
                                <span className="text-dark fw-medium">Canonical Records:</span>
                                <span className="text-warning fw-bold">{selectedDoc.record_count}</span>
                              </div>
                              <div className="d-flex justify-content-between align-items-center">
                                <span className="text-dark fw-medium">File Size:</span>
                                <span className="text-dark fw-bold">{(selectedDoc.repository_size / 1024).toFixed(2)} KB</span>
                              </div>
                              <div className="d-flex justify-content-between align-items-center">
                                <span className="text-dark fw-medium">Last Sync:</span>
                                <span className="text-dark fw-semibold">{new Date(selectedDoc.last_sync).toLocaleString()}</span>
                              </div>
                            </div>
                          </div>

                          <div className="mb-3">
                            <button 
                              className="btn btn-sm btn-outline-info w-100 font-monospace"
                              onClick={() => copyLogicalPath(selectedDoc.logical_path)}
                            >
                              📋 Copy Path for Knowledge Assistant
                            </button>
                          </div>

                          {/* Technical Details Accordion */}
                          <div className="accordion mt-auto" id="techAccordion">
                            <div className="accordion-item bg-light border-secondary">
                              <h2 className="accordion-header">
                                <button className="accordion-button collapsed py-2 px-3 small text-dark bg-light border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#techCollapse">
                                  Technical Details & JSONB Records
                                </button>
                              </h2>
                              <div id="techCollapse" className="accordion-collapse collapse" data-bs-parent="#techAccordion">
                                <div className="accordion-body p-3 font-monospace small text-dark bg-light">
                                  <div className="mb-2">Document ID: {selectedDoc.id}</div>
                                  <div className="mb-2">Physical Size: {(selectedDoc.repository_size / 1024).toFixed(2)} KB</div>
                                  
                                  {/* Sub-tabs */}
                                  <ul className="nav nav-pills nav-fill border border-secondary rounded overflow-hidden mb-3 bg-light mt-3">
                                    {['records', 'versions', 'audit', 'metadata'].map((tab) => (
                                      <li className="nav-item" key={tab}>
                                        <button 
                                          className={`nav-link py-1 rounded-0 border-0 ${activeDetailsTab === tab ? 'btn-premium-primary text-white' : 'bg-transparent text-dark fw-semibold'}`}
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
                                            <div key={rec.id} className="bg-white rounded p-2 border border-secondary font-monospace position-relative">
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
                                              <div className="text-dark my-1">{aud.reason}</div>
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
                  <div className="glass-panel p-4 border border-info rounded-3 mt-4">
                    <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary">
                      <div className="d-flex align-items-center gap-2">
                        <span className="badge bg-info text-dark font-monospace text-uppercase">{previewData?.file_type || 'Loading'}</span>
                        <h5 className="fw-bold text-dark mb-0">{previewingDoc.title}</h5>
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
                      </div>
                    ) : (
                      <div className="text-center py-5 text-muted">Awaiting preview content</div>
                    )}
                  </div>
                )}

              </div>
            ) : (
              /* Global Database Records JSONB Query Workspace */
              <div className="glass-panel p-4">
                <h5 className="fw-bold text-dark mb-3">Database Records Lookup (JSONB Engine)</h5>
                
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
                                  <button className="btn btn-sm btn-success py-0 px-2 border-0" onClick={() => handleUpdateRecord(rec.id, true)}>Save</button>
                                  <button className="btn btn-sm btn-secondary py-0 px-2 border-0" onClick={() => setEditingRecordId(null)}>Cancel</button>
                                </>
                              ) : (
                                <>
                                  <button className="btn btn-sm btn-outline-info py-0 px-2 border-0" onClick={() => {
                                    setEditingRecordId(rec.id);
                                    setEditingDataJson(JSON.stringify(rec.canonical_data, null, 2));
                                  }}>Edit Keys</button>
                                  <button className="btn btn-sm btn-outline-danger py-0 px-2 border-0" onClick={() => handleDeleteRecord(rec.id, true)}>Purge Record</button>
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

        {/* OTHER EXISTING TABS */}
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
                <h3 className="text-gradient fw-bold mb-0">Phase 4 Data Quality & Explainable AI</h3>
              </div>
            </div>
            <div className="glass-panel p-4">
              <DataQualityExplainability />
            </div>
          </>
        )}

        {activeTab === 'knowledge-assistant' && (
          <>
            <div className="mb-4 d-flex align-items-center gap-3">
              <button onClick={() => setActiveTab('dashboard')} className="btn btn-premium-secondary py-1 px-3 fs-6">
                ← Back
              </button>
              <div>
                <h3 className="text-gradient fw-bold mb-0">Phase 5 Knowledge Assistant</h3>
              </div>
            </div>
            <div className="glass-panel p-2 bg-white rounded-3 border">
              <UniversalKnowledgeAssistant />
            </div>
          </>
        )}

      </div>

      {/* CREATE NEW FOLDER MODAL */}
      {showNewFolderModal && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content bg-white border border-secondary text-dark shadow-lg">
              <div className="modal-header border-secondary">
                <h5 className="modal-title font-monospace fw-bold text-dark">➕ Create New Folder / Subfolder</h5>
                <button type="button" className="btn-close" onClick={() => setShowNewFolderModal(false)}></button>
              </div>
              <form onSubmit={handleCreateFolder}>
                <div className="modal-body">
                  <div className="alert alert-success py-2 px-3 mb-3 border-0 small font-monospace d-flex align-items-center gap-2">
                    <i className="bi bi-folder2-open text-success fs-5"></i>
                    <div>
                      <div>Target Parent Path: <strong className="text-dark">{targetFolderPath || explorerData.current_logical_path}</strong></div>
                      <div className="text-secondary extra-small">{selectedRepoType.toUpperCase()} REPOSITORY ({targetFolderId ? 'Subfolder Level' : 'Root Level'})</div>
                    </div>
                  </div>
                  <div className="mb-3">
                    <label className="form-label text-secondary small font-monospace font-semibold">Folder Name</label>
                    <input 
                      type="text" 
                      className="form-control bg-white text-dark border-secondary font-monospace"
                      placeholder="e.g. Subfolder, Engineering, Reports"
                      value={newFolderName}
                      onChange={(e) => setNewFolderName(e.target.value)}
                      required
                      autoFocus
                    />
                  </div>
                </div>
                <div className="modal-footer border-secondary">
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowNewFolderModal(false)}>Cancel</button>
                  <button type="submit" className="btn btn-success btn-sm font-monospace text-white" disabled={creatingFolder}>
                    {creatingFolder ? 'Creating...' : 'Create Folder'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* UPLOAD FILE / FOLDER MODAL & INGESTION PIPELINE MONITOR */}
      {showUploadModal && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content bg-white border border-secondary text-dark shadow-lg">
              <div className="modal-header border-secondary">
                <h5 className="modal-title font-monospace fw-bold text-dark">
                  {uploadMode === 'file' ? '📤 Document Upload & Ingestion Pipeline' : '📁 Folder Tree Upload & Ingestion'}
                </h5>
                <button type="button" className="btn-close" onClick={() => { setShowUploadModal(false); setPipelineResult(null); setPipelineError(''); }}></button>
              </div>
              
              <div className="modal-body">
                <div className="alert alert-info py-2 px-3 mb-3 border-0 small font-monospace d-flex align-items-center gap-2">
                  <i className="bi bi-geo-alt-fill text-info fs-5"></i>
                  <div>
                    <div>Target Destination: <strong className="text-dark">{targetFolderPath || explorerData.current_logical_path}</strong></div>
                    <div className="text-secondary extra-small">{selectedRepoType.toUpperCase()} REPOSITORY</div>
                  </div>
                </div>

                {pipelineError && (
                  <div className="alert alert-danger py-2 small mb-3 border-0">
                    ✕ {pipelineError}
                  </div>
                )}

                {processing ? (
                  <div className="text-center py-4">
                    <div className="spinner-border text-success mb-3" role="status" style={{ width: '3rem', height: '3rem' }}></div>
                    <h6 className="fw-bold text-success font-monospace">{uploadProgress || 'Ingesting documents through 8-stage pipeline...'}</h6>
                    <p className="small text-secondary mb-0">Validating signature, running OCR parsing, mapping schema, and updating vector embeddings...</p>
                  </div>
                ) : pipelineResult ? (
                  <div className="d-flex flex-column gap-3">
                    <div className={`alert ${pipelineResult.processing_status === 'COMPLETED' ? 'alert-success' : (pipelineResult.processing_status === 'PROCESSING' ? 'alert-info' : 'alert-danger')} py-2 mb-2 d-flex justify-content-between align-items-center`}>
                      <span className="fw-bold font-monospace d-flex align-items-center gap-2">
                        {pipelineResult.processing_status === 'PROCESSING' && (
                          <span className="spinner-border spinner-border-sm text-info" role="status"></span>
                        )}
                        STATUS: {pipelineResult.processing_status}
                      </span>
                      <button className="btn btn-sm btn-outline-dark" onClick={() => { setShowUploadModal(false); setPipelineResult(null); }}>
                        Close & View in Explorer
                      </button>
                    </div>

                    <ul className="nav nav-tabs border-secondary mb-2">
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

                    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                      {resultTab === 'record' && (
                        <pre className="text-success font-monospace small bg-light p-3 rounded border">
                          {JSON.stringify(pipelineResult.pipeline_result?.standardized_record || {}, null, 2)}
                        </pre>
                      )}
                      {resultTab === 'metadata' && (
                        <pre className="text-dark font-monospace small bg-light p-3 rounded border">
                          {JSON.stringify(pipelineResult.pipeline_result?.metadata || {}, null, 2)}
                        </pre>
                      )}
                      {resultTab === 'stages' && (
                        <pre className="text-dark font-monospace small bg-light p-3 rounded border">
                          {JSON.stringify(pipelineResult.pipeline_result?.stage_execution || {}, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleUploadSubmit}>
                    {/* Drag & Drop zone for single file */}
                    {uploadMode === 'file' ? (
                      <div 
                        className={`border border-2 border-dashed rounded-3 p-4 text-center mb-3 position-relative ${dragActive ? 'border-success bg-light' : 'border-secondary bg-light'}`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                      >
                        <input 
                          type="file" 
                          className="position-absolute top-0 start-0 w-100 h-100 opacity-0 cursor-pointer"
                          onChange={(e) => { if (e.target.files?.[0]) setSelectedFile(e.target.files[0]); }}
                          style={{ cursor: 'pointer' }}
                        />
                        <svg className="mb-2 text-success" width="36" height="36" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        {selectedFile ? (
                          <div>
                            <p className="text-dark fw-medium mb-0">{selectedFile.name}</p>
                            <p className="text-secondary small font-monospace">{(selectedFile.size / 1024).toFixed(2)} KB</p>
                          </div>
                        ) : (
                          <div>
                            <p className="text-dark mb-0 fw-semibold">Drag & drop document here or click to browse</p>
                            <p className="text-secondary small mb-0">(PDF, Excel, CSV, JSON, Images, Plain Text)</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      /* Folder upload input */
                      <div className="mb-3 p-4 border border-secondary rounded-3 bg-light">
                        <label className="form-label text-success fw-bold font-monospace">Select Local Directory for Tree Ingestion</label>
                        <input 
                          type="file" 
                          className="form-control bg-white text-dark border-secondary"
                          webkitdirectory="true"
                          directory=""
                          multiple
                          onChange={(e) => {
                            if (e.target.files) setFolderFiles(Array.from(e.target.files));
                          }}
                        />
                        {folderFiles.length > 0 && (
                          <div className="mt-2 text-success font-monospace small fw-bold">
                            ✓ Ready to upload folder containing {folderFiles.length} files. Subfolder structures will be preserved automatically!
                          </div>
                        )}
                      </div>
                    )}

                    <div className="mb-3">
                      <label className="form-label text-secondary small font-monospace">Parser Strategy</label>
                      <select 
                        className="form-select bg-white border-secondary text-dark"
                        value={parserType}
                        onChange={(e) => setParserType(e.target.value)}
                      >
                        <option value="auto">Auto-Detect Signature (Recommended)</option>
                        <option value="PDF">PDF Parser</option>
                        <option value="EXCEL">Excel/Spreadsheet Parser</option>
                        <option value="CSV">CSV Table Parser</option>
                        <option value="JSON">JSON Parser</option>
                        <option value="IMAGE">Image OCR Parser</option>
                      </select>
                    </div>

                    <div className="d-flex justify-content-end gap-2 mt-4">
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowUploadModal(false)}>Cancel</button>
                      <button type="submit" className="btn btn-success btn-sm font-monospace text-white">
                        Start Upload & Ingestion
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* RECYCLE BIN SOFT-DELETION MODAL */}
      {showRecycleBin && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content bg-white border border-warning text-dark shadow-lg">
              <div className="modal-header border-secondary">
                <h5 className="modal-title font-monospace fw-bold text-dark d-flex align-items-center gap-2">
                  <i className="bi bi-trash-fill text-warning"></i> Recycle Bin (Soft-Deleted Items)
                </h5>
                <button type="button" className="btn-close" onClick={() => setShowRecycleBin(false)}></button>
              </div>
              <div className="modal-body" style={{ maxHeight: '500px', overflowY: 'auto' }}>
                {loadingRecycleBin ? (
                  <div className="text-center py-4 text-secondary">
                    <span className="spinner-border spinner-border-sm me-2 text-warning"></span>
                    Loading soft-deleted items...
                  </div>
                ) : (recycleBinData.folders?.length === 0 && recycleBinData.documents?.length === 0) ? (
                  <div className="text-center py-4 text-secondary font-monospace">
                    Recycle Bin is empty. No deleted files or folders found.
                  </div>
                ) : (
                  <div className="d-flex flex-column gap-3">
                    
                    {/* Soft-Deleted Folders */}
                    {recycleBinData.folders?.length > 0 && (
                      <div>
                        <h6 className="text-warning font-monospace fw-bold mb-2">Deleted Folders</h6>
                        <ul className="list-group list-group-flush bg-white rounded border border-secondary font-monospace small">
                          {recycleBinData.folders.map(f => (
                            <li key={f.id} className="list-group-item bg-white text-dark border-secondary d-flex justify-content-between align-items-center">
                              <div>
                                <i className="bi bi-folder-fill text-warning me-2 fs-5"></i> <strong>{f.name}</strong> <span className="text-secondary ms-2">({f.logical_path})</span>
                              </div>
                              <div className="d-flex gap-2">
                                <button className="btn btn-sm btn-outline-success py-0 px-2" onClick={() => handleRestoreItem('folder', f.id)}>
                                  Restore
                                </button>
                                <button className="btn btn-sm btn-outline-danger py-0 px-2" onClick={() => handlePermanentDelete('folder', f.id, f.name)}>
                                  Delete Permanently
                                </button>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Soft-Deleted Documents */}
                    {recycleBinData.documents?.length > 0 && (
                      <div>
                        <h6 className="text-warning font-monospace fw-bold mb-2">Deleted Documents</h6>
                        <ul className="list-group list-group-flush bg-white rounded border border-secondary font-monospace small">
                          {recycleBinData.documents.map(d => (
                            <li key={d.id} className="list-group-item bg-white text-dark border-secondary d-flex justify-content-between align-items-center">
                              <div>
                                {getFileIcon(d.title)} <strong>{d.title}</strong> <span className="text-secondary ms-2">({d.logical_path})</span>
                              </div>
                              <div className="d-flex gap-2">
                                <button className="btn btn-sm btn-outline-success py-0 px-2" onClick={() => handleRestoreItem('document', d.id)}>
                                  Restore
                                </button>
                                <button className="btn btn-sm btn-outline-danger py-0 px-2" onClick={() => handlePermanentDelete('document', d.id, d.title)}>
                                  Delete Permanently
                                </button>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                  </div>
                )}
              </div>
              <div className="modal-footer border-secondary d-flex justify-content-between">
                <div>
                  {(recycleBinData.folders?.length > 0 || recycleBinData.documents?.length > 0) && (
                    <button 
                      type="button" 
                      className="btn btn-danger btn-sm font-monospace d-flex align-items-center gap-1"
                      onClick={emptyRecycleBin}
                    >
                      <i className="bi bi-fire"></i> Empty Recycle Bin (Purge All)
                    </button>
                  )}
                </div>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowRecycleBin(false)}>Close</button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default Dashboard;
