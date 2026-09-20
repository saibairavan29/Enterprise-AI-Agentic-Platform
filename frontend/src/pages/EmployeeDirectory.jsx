import React, { useState, useEffect } from 'react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';

const formatLabel = (key) => {
  if (!key) return '';
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/\bId\b/gi, 'ID');
};

const DEFAULT_SCHEMA = [
  { key: 'employee_id', label: 'Employee ID', type: 'text' },
  { key: 'name', label: 'Name', type: 'text' },
  { key: 'email', label: 'Work Email', type: 'text' },
  { key: 'role', label: 'Role / Designation', type: 'text' },
  { key: 'department', label: 'Department', type: 'category' },
  { key: 'experience_years', label: 'Experience (Years)', type: 'number' },
  { key: 'salary', label: 'Salary', type: 'number' },
  { key: 'current_project', label: 'Current Project', type: 'text' },
  { key: 'employment_status', label: 'Status', type: 'category' }
];

const EmployeeDirectory = () => {
  const { user } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [schema, setSchema] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  // Multi-Selection State
  const [selectedIds, setSelectedIds] = useState([]);

  // Single Add Record Form States (Dynamic)
  const [showAddModal, setShowAddModal] = useState(false);
  const [addFormData, setAddFormData] = useState({});

  // Edit Record Form States (Dynamic)
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingEmp, setEditingEmp] = useState(null);
  const [editFormData, setEditFormData] = useState({});

  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  
  // Stack Add (Bulk Import) Form States
  const [showStackAddModal, setShowStackAddModal] = useState(false);
  const [importSourceTab, setImportSourceTab] = useState('local'); // 'local' | 'team' | 'personal'
  const [stackFile, setStackFile] = useState(null);
  const [selectedRepoDoc, setSelectedRepoDoc] = useState(null);
  const [repoDocs, setRepoDocs] = useState([]);
  const [loadingRepoDocs, setLoadingRepoDocs] = useState(false);

  const [stackPreviewRows, setStackPreviewRows] = useState([]);
  const [stackPreviewHeaders, setStackPreviewHeaders] = useState([]);
  const [stackUploading, setStackUploading] = useState(false);
  const [stackError, setStackError] = useState('');
  const [stackSuccessMsg, setStackSuccessMsg] = useState('');
  const [stackStats, setStackStats] = useState(null);

  // Search and Filter States (Dynamic)
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilters, setCategoryFilters] = useState({});
  const [sortField, setSortField] = useState('');
  const [sortOrder, setSortOrder] = useState('asc');
  
  // Selection and Profile details drawer
  const [selectedEmp, setSelectedEmp] = useState(null);
  
  // Pagination States
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const deriveSchemaFromRecords = (records) => {
    if (!records || records.length === 0) return;
    const keySet = [];
    const seenLower = new Set();

    records.forEach(r => {
      const data = r.canonical_data || r.employee_details || r;
      if (data && typeof data === 'object') {
        Object.keys(data).forEach(k => {
          const kClean = String(k).trim();
          const kLower = kClean.toLowerCase().replace(/_/g, '');
          if (!['id', 'knowledge_document', 'created_at', 'updated_at', 'employee_details', 'canonical_data'].includes(kClean)) {
            if (!seenLower.has(kLower)) {
              seenLower.add(kLower);
              keySet.push(kClean);
            }
          }
        });
      }
    });

    if (keySet.length === 0) return;

    const cols = keySet.map(key => {
      let type = 'text';
      const sampleRec = records.find(r => {
        const d = r.canonical_data || r.employee_details || r;
        if (!d) return false;
        return d[key] !== undefined && d[key] !== null;
      });
      const dObj = sampleRec ? (sampleRec.canonical_data || sampleRec.employee_details || sampleRec) : null;
      const sampleVal = dObj ? dObj[key] : null;

      const kLower = key.toLowerCase();
      if (typeof sampleVal === 'number' || kLower.includes('salary') || kLower.includes('exp') || kLower.includes('years') || kLower.includes('count') || kLower.includes('age') || kLower.includes('pay')) {
        type = 'number';
      } else if (kLower.includes('date')) {
        type = 'date';
      }

      return {
        key,
        label: formatLabel(key),
        type
      };
    });

    setSchema(cols);
  };

  const fetchEmployees = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await client.get('repository/employees/');
      const data = Array.isArray(res.data) ? res.data : (res.data.results || res.data.data || []);
      setEmployees(data);

      try {
        const schemaRes = await client.get('repository/employees/schema/');
        const schemaCols = schemaRes.data?.data || schemaRes.data?.columns;
        if (Array.isArray(schemaCols) && schemaCols.length > 0) {
          setSchema(schemaCols);
        } else {
          deriveSchemaFromRecords(data);
        }
      } catch (sErr) {
        deriveSchemaFromRecords(data);
      }
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to load record directory.');
    } finally {
      setLoading(false);
    }
  };

  const activeSchema = schema.length > 0 ? schema : DEFAULT_SCHEMA;

  const fetchRepoDocuments = async (sourceType) => {
    setLoadingRepoDocs(true);
    setRepoDocs([]);
    setSelectedRepoDoc(null);
    try {
      const res = await client.get('repository/documents/');
      const docs = Array.isArray(res.data) ? res.data : (res.data.results || res.data.data || []);
      
      const validDocs = docs.filter(doc => {
        const title = (doc.title || doc.source_document?.original_name || doc.metadata?.file?.original_name || '').toLowerCase();
        const isDataset = title.endsWith('.csv') || title.endsWith('.xlsx') || title.endsWith('.xls') || (doc.record_count && doc.record_count > 0);
        if (sourceType === 'personal') {
          const isOwner = doc.owner === user?.username || doc.owner?.username === user?.username || doc.repository_type === 'personal';
          return isDataset && isOwner;
        } else {
          return isDataset;
        }
      });
      setRepoDocs(validDocs);
    } catch (err) {
      console.error("Failed to load repository documents:", err);
    } finally {
      setLoadingRepoDocs(false);
    }
  };

  const handleTabChange = (tabName) => {
    setImportSourceTab(tabName);
    setStackError('');
    setStackSuccessMsg('');
    setStackFile(null);
    setSelectedRepoDoc(null);
    setStackPreviewRows([]);
    setStackPreviewHeaders([]);

    if (tabName === 'team' || tabName === 'personal') {
      fetchRepoDocuments(tabName);
    }
  };

  const handleSelectRepoDocument = (doc) => {
    setSelectedRepoDoc(doc);
    setStackError('');
    setStackSuccessMsg('');

    client.get(`repository/documents/${doc.id}/records/`)
      .then(res => {
        const records = Array.isArray(res.data) ? res.data : (res.data.results || res.data.data || []);
        if (records.length > 0) {
          const rows = records.slice(0, 8).map(r => r.canonical_data || {});
          const headers = Array.from(new Set(rows.flatMap(r => Object.keys(r))));
          setStackPreviewHeaders(headers);
          setStackPreviewRows(rows);
        } else {
          setStackPreviewHeaders([]);
          setStackPreviewRows([]);
        }
      })
      .catch(err => {
        console.error("Failed to preview repository document records", err);
      });
  };

  const handleOpenAddModal = () => {
    const initData = {};
    activeSchema.forEach(col => {
      initData[col.key] = col.type === 'number' ? 0 : '';
    });
    setAddFormData(initData);
    setFormError('');
    setFormSuccess('');
    setShowAddModal(true);
  };

  const handleAddRecord = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    
    setSubmitting(true);
    try {
      const res = await client.post('repository/employees/', addFormData);
      
      if (res.data.success) {
        setFormSuccess('Record added successfully!');
        fetchEmployees();
        
        setTimeout(() => {
          setShowAddModal(false);
          setFormSuccess('');
        }, 1500);
      } else {
        setFormError(res.data.message || 'Failed to add record.');
      }
    } catch (err) {
      console.error(err);
      setFormError(err.response?.data?.message || 'Error occurred while saving record.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStackFileChange = (e) => {
    const file = e.target.files[0];
    setStackFile(file || null);
    setStackError('');
    setStackSuccessMsg('');
    setStackStats(null);
    setStackPreviewRows([]);
    setStackPreviewHeaders([]);

    if (file) {
      const fileName = file.name.toLowerCase();
      if (fileName.endsWith('.csv')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          const text = event.target.result;
          const lines = text.split(/\r\n|\n/).filter(line => line.trim() !== '');
          if (lines.length > 0) {
            const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
            const rows = lines.slice(1, 10).map(line => {
              const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''));
              const rowObj = {};
              headers.forEach((h, idx) => {
                rowObj[h] = vals[idx] || '';
              });
              return rowObj;
            });
            setStackPreviewHeaders(headers);
            setStackPreviewRows(rows);
          }
        };
        reader.readAsText(file);
      }
    }
  };

  const downloadSampleTemplate = () => {
    const headers = activeSchema.map(s => s.key).join(',');
    const sampleRow = activeSchema.map(s => {
      if (s.key.includes('id')) return 'REC1001';
      if (s.key.includes('name')) return 'John Doe';
      if (s.key.includes('email')) return 'john.doe@enterprise.com';
      if (s.key.includes('salary')) return '85000';
      if (s.type === 'number') return '5';
      if (s.type === 'date') return '2024-01-15';
      return 'Sample Value';
    }).join(',');

    const csvContent = `${headers}\n${sampleRow}`;
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "record_import_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleStackAddSubmit = async (e) => {
    e.preventDefault();
    if (importSourceTab === 'local' && !stackFile) {
      setStackError('Please select a file to import.');
      return;
    }
    if ((importSourceTab === 'team' || importSourceTab === 'personal') && !selectedRepoDoc) {
      setStackError(`Please select a document from the ${importSourceTab === 'team' ? 'Team' : 'Personal'} Repository.`);
      return;
    }

    setStackUploading(true);
    setStackError('');
    setStackSuccessMsg('');
    setStackStats(null);

    try {
      let res;
      if (importSourceTab === 'local') {
        const formData = new FormData();
        formData.append('file', stackFile);
        res = await client.post('repository/employees/bulk_import/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } else {
        res = await client.post('repository/employees/bulk_import/', {
          document_id: selectedRepoDoc.id
        });
      }

      if (res.data.success) {
        const stats = res.data.data;
        setStackStats(stats);
        setStackSuccessMsg(res.data.message || `Stack Add completed successfully!`);
        fetchEmployees();
        setStackFile(null);
        setSelectedRepoDoc(null);
        setStackPreviewRows([]);
        setStackPreviewHeaders([]);

        setTimeout(() => {
          setShowStackAddModal(false);
          setStackSuccessMsg('');
          setStackStats(null);
        }, 2500);
      } else {
        setStackError(res.data.message || 'Failed to import record file.');
      }
    } catch (err) {
      console.error(err);
      setStackError(err.response?.data?.message || err.response?.data?.errors?.[0] || 'Error importing record dataset.');
    } finally {
      setStackUploading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  const getEmpDataVal = (emp, fieldName) => {
    if (!emp) return 'N/A';
    const details = emp.canonical_data || emp.employee_details || emp;
    let val = details[fieldName] !== undefined ? details[fieldName] : emp[fieldName];

    if (val === undefined || val === null) {
      const fnLower = String(fieldName).toLowerCase().replace(/_/g, '');
      if (details && typeof details === 'object') {
        const matchKey = Object.keys(details).find(k => k.toLowerCase().replace(/_/g, '') === fnLower);
        if (matchKey && details[matchKey] !== undefined && details[matchKey] !== null) {
          val = details[matchKey];
        }
      }
    }

    if (val === undefined || val === null || val === '') return 'N/A';
    if (typeof val === 'object') {
      return Array.isArray(val) ? val.join(', ') : JSON.stringify(val);
    }
    return val;
  };

  const safeEmployees = Array.isArray(employees) ? employees : [];

  // Auto-discover category columns for filter bar (unique values <= 25)
  const filterableCols = activeSchema.filter(col => {
    const uniqueVals = new Set(safeEmployees.map(e => getEmpDataVal(e, col.key)).filter(v => v && v !== 'N/A'));
    return uniqueVals.size > 0 && uniqueVals.size <= 25;
  });

  const filteredEmployees = safeEmployees.filter(emp => {
    if (!emp) return false;
    const details = emp.canonical_data || emp.employee_details || emp;

    if (searchQuery.trim()) {
      const searchLower = searchQuery.toLowerCase();
      const match = Object.values(details).some(val => {
        if (val === null || val === undefined) return false;
        const strVal = typeof val === 'object' ? JSON.stringify(val) : String(val);
        return strVal.toLowerCase().includes(searchLower);
      });
      if (!match) return false;
    }

    for (const [fKey, fVal] of Object.entries(categoryFilters)) {
      if (fVal) {
        const cellVal = String(getEmpDataVal(emp, fKey)).toLowerCase();
        if (cellVal !== fVal.toLowerCase()) return false;
      }
    }

    return true;
  });

  const sortedEmployees = [...filteredEmployees].sort((a, b) => {
    if (!sortField) return 0;
    let valA = getEmpDataVal(a, sortField);
    let valB = getEmpDataVal(b, sortField);

    const strA = typeof valA === 'object' ? JSON.stringify(valA) : String(valA);
    const strB = typeof valB === 'object' ? JSON.stringify(valB) : String(valB);

    const numA = parseFloat(strA.replace(/[^0-9.-]/g, ''));
    const numB = parseFloat(strB.replace(/[^0-9.-]/g, ''));

    if (!isNaN(numA) && !isNaN(numB)) {
      return sortOrder === 'asc' ? numA - numB : numB - numA;
    }
    
    valA = strA.toLowerCase();
    valB = strB.toLowerCase();
    
    if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const totalPages = Math.max(1, Math.ceil(sortedEmployees.length / itemsPerPage));

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [sortedEmployees.length, totalPages]);

  const getVisiblePageNumbers = (current, total) => {
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }
    if (current <= 4) {
      return [1, 2, 3, 4, 5, '...', total];
    }
    if (current >= total - 3) {
      return [1, '...', total - 4, total - 3, total - 2, total - 1, total];
    }
    return [1, '...', current - 1, current, current + 1, '...', total];
  };

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = sortedEmployees.slice(indexOfFirstItem, indexOfLastItem);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // --- SELECTION HANDLERS ---
  const handleToggleSelect = (id, e) => {
    if (e) e.stopPropagation();
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const isAllCurrentSelected = currentItems.length > 0 && currentItems.every(emp => selectedIds.includes(emp.id));

  const handleToggleSelectAll = () => {
    const currentItemIds = currentItems.map(e => e.id);
    if (isAllCurrentSelected) {
      setSelectedIds(prev => prev.filter(id => !currentItemIds.includes(id)));
    } else {
      setSelectedIds(prev => Array.from(new Set([...prev, ...currentItemIds])));
    }
  };

  // --- SINGLE & STACK REMOVE HANDLERS ---
  const handleSingleRemove = async (empId, e) => {
    if (e) e.stopPropagation();
    if (!window.confirm("Are you sure you want to remove this record?")) return;
    try {
      await client.delete(`repository/employees/${empId}/`);
      if (selectedEmp?.id === empId) setSelectedEmp(null);
      setSelectedIds(prev => prev.filter(id => id !== empId));
      fetchEmployees();
    } catch (err) {
      console.error(err);
      alert("Failed to remove record.");
    }
  };

  const handleStackRemove = async () => {
    if (selectedIds.length === 0) return;
    if (!window.confirm(`Are you sure you want to Stack Remove ${selectedIds.length} selected records?`)) return;
    try {
      await client.post('repository/employees/bulk_delete/', { record_ids: selectedIds });
      setSelectedIds([]);
      setSelectedEmp(null);
      fetchEmployees();
    } catch (err) {
      console.error(err);
      alert("Failed to execute Stack Remove.");
    }
  };

  const handlePurgeAll = async () => {
    if (!window.confirm("WARNING: Are you sure you want to remove ALL records from the directory? This action cannot be undone.")) return;
    try {
      await client.post('repository/employees/purge_all/');
      setSelectedIds([]);
      setSelectedEmp(null);
      fetchEmployees();
    } catch (err) {
      console.error(err);
      alert("Failed to purge directory.");
    }
  };

  // --- EDIT DETAILS HANDLERS ---
  const openEditModal = (emp, e) => {
    if (e) e.stopPropagation();
    setEditingEmp(emp);
    const details = emp.canonical_data || emp.employee_details || emp;
    const initialForm = {};
    activeSchema.forEach(col => {
      initialForm[col.key] = details[col.key] !== undefined ? details[col.key] : '';
    });
    setEditFormData(initialForm);
    setShowEditModal(true);
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingEmp) return;
    setSubmitting(true);
    try {
      const res = await client.put(`repository/employees/${editingEmp.id}/`, editFormData);
      if (res.data.success) {
        fetchEmployees();
        setShowEditModal(false);
        setEditingEmp(null);
        if (selectedEmp?.id === editingEmp.id) {
          setSelectedEmp(res.data.data);
        }
      }
    } catch (err) {
      console.error(err);
      alert("Failed to update record details.");
    } finally {
      setSubmitting(false);
    }
  };

  const renderCellContent = (emp, col) => {
    let val = getEmpDataVal(emp, col.key);
    if (val === 'N/A') return <span className="text-muted">N/A</span>;

    if (typeof val === 'object' && val !== null) {
      val = Array.isArray(val) ? val.join(', ') : JSON.stringify(val);
    }

    const valStr = String(val);
    const kLower = col.key.toLowerCase();
    if (kLower.includes('salary') || kLower.includes('pay') || kLower.includes('compensation')) {
      if (valStr.includes('₹') || valStr.toLowerCase().includes('rs') || valStr.toLowerCase().includes('inr')) {
        return <span className="fw-semibold text-success font-monospace">{valStr}</span>;
      }
      const numVal = parseFloat(valStr.replace(/[^0-9.-]/g, ''));
      const formatted = !isNaN(numVal) ? `₹${numVal.toLocaleString('en-IN')}` : valStr;
      return <span className="fw-semibold text-success font-monospace">{formatted}</span>;
    }

    if (kLower.includes('status')) {
      const isActive = valStr.toLowerCase() === 'active';
      return (
        <span className={`badge ${isActive ? 'bg-success-subtle text-success border-success' : 'bg-secondary-subtle text-secondary border-secondary'} border rounded-pill px-2 py-1`}>
          {valStr}
        </span>
      );
    }

    if (col.type === 'number' || typeof val === 'number') {
      return <span className="font-monospace">{valStr}</span>;
    }

    if (kLower.includes('email')) {
      return <span className="text-secondary small font-monospace">{valStr}</span>;
    }

    if (kLower.includes('id')) {
      return <span className="font-monospace fw-semibold">{valStr}</span>;
    }

    return <span className="text-dark">{valStr}</span>;
  };

  return (
    <div className="container-fluid py-4 px-4">
      {/* Top Banner Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold text-dark mb-1 d-flex align-items-center gap-2">
            <span>📊</span> Record Directory
          </h2>
          <p className="text-secondary mb-0">Universal Schema-Driven Record Directory with dynamic columns, forms, filters, and side panel.</p>
        </div>
      </div>

      <div className="row g-4 position-relative">
        <div className={selectedEmp ? "col-12 col-lg-8" : "col-12"}>
          <div className="bg-white rounded-3 shadow-sm border p-4">
            
            {/* Filters & Actions Bar */}
            <div className="row g-3 mb-4 align-items-end">
              <div className="col-12 col-md-3">
                <label className="form-label small text-secondary fw-semibold">Search Directory</label>
                <input 
                  type="text" 
                  className="form-control"
                  placeholder="Search any record field..."
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                />
              </div>
              
              {filterableCols.slice(0, 3).map(col => {
                const options = Array.from(new Set(
                  safeEmployees.map(e => {
                    const v = getEmpDataVal(e, col.key);
                    return typeof v === 'object' ? JSON.stringify(v) : String(v);
                  }).filter(v => v && v !== 'N/A' && v !== '[object Object]')
                ));
                return (
                  <div key={col.key} className="col-6 col-md-2">
                    <label className="form-label small text-secondary fw-semibold">{col.label}</label>
                    <select 
                      className="form-select text-capitalize"
                      value={categoryFilters[col.key] || ''}
                      onChange={(e) => {
                        setCategoryFilters({ ...categoryFilters, [col.key]: e.target.value });
                        setCurrentPage(1);
                      }}
                    >
                      <option value="">All {col.label}s</option>
                      {options.map(opt => (
                        <option key={String(opt)} value={String(opt)}>
                          {String(opt)}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}

              <div className="col-12 col-md-3 d-flex gap-2 justify-content-end flex-wrap ms-auto">
                <button className="btn btn-outline-secondary px-3" onClick={fetchEmployees} disabled={loading} title="Refresh Directory">
                  Refresh
                </button>
                {user?.role === 'admin' && (
                  <>
                    <button className="btn btn-outline-primary fw-bold px-3 text-nowrap d-flex align-items-center gap-1" onClick={() => setShowStackAddModal(true)} title="Bulk import records from Local File, Team Repo, or Personal Repo">
                      <span>📥</span> Stack Add
                    </button>
                    <button className="btn btn-premium-primary text-white fw-semibold px-3 text-nowrap" onClick={handleOpenAddModal}>
                      + Add
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Selection Toolbar Bar */}
            {selectedIds.length > 0 && (
              <div className="alert alert-primary py-2 px-3 mb-3 d-flex justify-content-between align-items-center rounded border-primary">
                <div className="fw-semibold">
                  <span>✅ {selectedIds.length} record{selectedIds.length > 1 ? 's' : ''} selected</span>
                </div>
                <div className="d-flex gap-2">
                  <button className="btn btn-sm btn-outline-secondary bg-white" onClick={() => setSelectedIds([])}>
                    Deselect All
                  </button>
                  {user?.role === 'admin' && (
                    <button className="btn btn-sm btn-danger fw-bold text-white d-flex align-items-center gap-1" onClick={handleStackRemove}>
                      <span>🗑️</span> Stack Remove ({selectedIds.length})
                    </button>
                  )}
                </div>
              </div>
            )}

            {safeEmployees.length > 0 && selectedIds.length === 0 && user?.role === 'admin' && (
              <div className="d-flex justify-content-end mb-2">
                <button className="btn btn-sm btn-outline-danger" onClick={handlePurgeAll} title="Clear all records from directory">
                  🗑️ Remove All Records ({safeEmployees.length})
                </button>
              </div>
            )}

            {errorMsg && <div className="alert alert-danger py-2">{errorMsg}</div>}

            {/* Table list */}
            <div className="table-responsive rounded border mb-3">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr className="small text-secondary">
                    <th style={{ width: '40px' }} className="text-center">
                      <input 
                        type="checkbox" 
                        className="form-check-input"
                        checked={isAllCurrentSelected}
                        onChange={handleToggleSelectAll}
                        title="Select All on Current Page"
                      />
                    </th>
                    {activeSchema.map(col => (
                      <th key={col.key} className="cursor-pointer text-nowrap" onClick={() => handleSort(col.key)}>
                        {col.label} {sortField === col.key && (sortOrder === 'asc' ? '↑' : '↓')}
                      </th>
                    ))}
                    <th className="text-end pe-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={activeSchema.length + 2} className="text-center py-5">
                        <span className="spinner-border spinner-border-sm me-2 text-primary" role="status"></span>
                        Loading directory records...
                      </td>
                    </tr>
                  ) : currentItems.length > 0 ? (
                    currentItems.map(emp => {
                      const isSelected = selectedIds.includes(emp.id);
                      return (
                        <tr 
                          key={emp.id} 
                          className={`cursor-pointer ${isSelected ? 'table-warning-subtle' : (selectedEmp?.id === emp.id ? 'table-primary-subtle' : '')}`}
                          onClick={() => setSelectedEmp(selectedEmp?.id === emp.id ? null : emp)}
                          style={{ cursor: 'pointer' }}
                        >
                          <td className="text-center" onClick={(e) => e.stopPropagation()}>
                            <input 
                              type="checkbox" 
                              className="form-check-input"
                              checked={isSelected}
                              onChange={(e) => handleToggleSelect(emp.id, e)}
                            />
                          </td>
                          {activeSchema.map(col => (
                            <td key={col.key}>
                              {renderCellContent(emp, col)}
                            </td>
                          ))}
                          <td className="text-end pe-3" onClick={(e) => e.stopPropagation()}>
                            <div className="d-flex justify-content-end gap-1">
                              <button 
                                className="btn btn-sm btn-outline-primary py-0 px-2"
                                onClick={(e) => openEditModal(emp, e)}
                                title="Edit Record Details"
                              >
                                ✏️
                              </button>
                              <button 
                                className="btn btn-sm btn-outline-danger py-0 px-2"
                                onClick={(e) => handleSingleRemove(emp.id, e)}
                                title="Remove Record"
                              >
                                🗑️
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={activeSchema.length + 2} className="text-center py-5 text-muted">
                        No matching records found. Click <strong>Stack Add</strong> or <strong>+ Add</strong> to import dataset records.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="d-flex justify-content-between align-items-center pt-2">
                <span className="small text-secondary">
                  Showing {indexOfFirstItem + 1} to {Math.min(indexOfLastItem, sortedEmployees.length)} of {sortedEmployees.length} records
                </span>
                <nav>
                  <ul className="pagination pagination-sm mb-0">
                    <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                      <button className="page-link" onClick={() => setCurrentPage(currentPage - 1)}>Previous</button>
                    </li>
                    {getVisiblePageNumbers(currentPage, totalPages).map((page, idx) => (
                      <li key={idx} className={`page-item ${page === currentPage ? 'active' : ''} ${page === '...' ? 'disabled' : ''}`}>
                        {page === '...' ? (
                          <span className="page-link">...</span>
                        ) : (
                          <button className="page-link" onClick={() => setCurrentPage(page)}>{page}</button>
                        )}
                      </li>
                    ))}
                    <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                      <button className="page-link" onClick={() => setCurrentPage(currentPage + 1)}>Next</button>
                    </li>
                  </ul>
                </nav>
              </div>
            )}

          </div>
        </div>

        {/* Details Side Panel Drawer (Dynamic) */}
        {selectedEmp && (
          <div className="col-12 col-lg-4">
            <div className="bg-white rounded-3 shadow-sm border p-4 sticky-top" style={{ top: '24px' }}>
              <div className="d-flex justify-content-between align-items-start mb-3 pb-2 border-bottom">
                <div>
                  <span className="badge bg-primary-subtle text-primary font-monospace mb-1">
                    {getEmpDataVal(selectedEmp, activeSchema[0]?.key || 'id')}
                  </span>
                  <h4 className="fw-bold mb-0 text-dark">
                    {getEmpDataVal(selectedEmp, activeSchema[1]?.key || 'name')}
                  </h4>
                  <p className="text-secondary small mb-0">
                    {getEmpDataVal(selectedEmp, activeSchema[2]?.key || 'role')}
                  </p>
                </div>
                <button className="btn-close" onClick={() => setSelectedEmp(null)}></button>
              </div>

              <div className="d-flex flex-column gap-3">
                <div className="d-flex gap-2">
                  <button className="btn btn-sm btn-outline-primary flex-fill d-flex align-items-center justify-content-center gap-1" onClick={(e) => openEditModal(selectedEmp, e)}>
                    <span>✏️</span> Edit Details
                  </button>
                  <button className="btn btn-sm btn-outline-danger flex-fill d-flex align-items-center justify-content-center gap-1" onClick={(e) => handleSingleRemove(selectedEmp.id, e)}>
                    <span>🗑️</span> Remove
                  </button>
                </div>

                {Object.entries(selectedEmp.canonical_data || selectedEmp.employee_details || selectedEmp).map(([key, val]) => {
                  if (['id', 'knowledge_document', 'created_at', 'updated_at', 'canonical_data', 'employee_details'].includes(key)) return null;
                  const label = formatLabel(key);
                  const isSalary = key.toLowerCase().includes('salary') || key.toLowerCase().includes('pay');
                  
                  let displayVal = 'N/A';
                  if (val !== null && val !== undefined && val !== '') {
                    if (typeof val === 'object') {
                      displayVal = Array.isArray(val) ? val.join(', ') : JSON.stringify(val);
                    } else {
                      displayVal = String(val);
                    }
                  }
                  if (isSalary) {
                    const numVal = parseFloat(displayVal.replace(/[^0-9.-]/g, ''));
                    if (!isNaN(numVal)) {
                      displayVal = `$${numVal.toLocaleString('en-US')}`;
                    }
                  }

                  return (
                    <div key={key}>
                      <span className="small text-secondary fw-semibold d-block">{label}</span>
                      <span className={`text-dark ${isSalary ? 'fw-bold text-success font-monospace' : ''}`}>{displayVal}</span>
                    </div>
                  );
                })}

                {/* Administrative metadata */}
                <div className="accordion mt-3" id="adminMetadata">
                  <div className="accordion-item border-secondary-subtle">
                    <h2 className="accordion-header">
                      <button className="accordion-button collapsed py-2 px-3 small text-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#adminCollapse">
                        System Details (Admin Only)
                      </button>
                    </h2>
                    <div id="adminCollapse" className="accordion-collapse collapse" data-bs-parent="#adminMetadata">
                      <div className="accordion-body p-3 font-monospace small text-secondary bg-light">
                        <div>Record ID: {selectedEmp.id}</div>
                        <div>Document ID: {selectedEmp.knowledge_document || 'N/A'}</div>
                        <div>Created: {selectedEmp.created_at ? new Date(selectedEmp.created_at).toLocaleDateString() : 'N/A'}</div>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>
        )}
      </div>

      {/* ✏️ Dynamic Edit Modal */}
      {showEditModal && editingEmp && (
        <>
          <div className="modal-backdrop fade show" style={{ zIndex: 1040 }}></div>
          <div className="modal fade show d-block" tabIndex="-1" style={{ zIndex: 1050 }}>
            <div className="modal-dialog modal-dialog-centered modal-lg">
              <div className="modal-content border-0 shadow-lg">
                <div className="modal-header bg-primary text-white">
                  <h5 className="modal-title fw-bold">✏️ Edit Record Details</h5>
                  <button type="button" className="btn-close btn-close-white" onClick={() => setShowEditModal(false)}></button>
                </div>
                <form onSubmit={handleSaveEdit}>
                  <div className="modal-body p-4">
                    <div className="row g-3">
                      {activeSchema.map(col => (
                        <div key={col.key} className="col-12 col-md-6">
                          <label className="form-label small text-secondary fw-semibold">{col.label}</label>
                          {col.type === 'number' ? (
                            <input 
                              type="number" 
                              className="form-control"
                              value={editFormData[col.key] !== undefined ? editFormData[col.key] : ''}
                              onChange={(e) => setEditFormData({ ...editFormData, [col.key]: e.target.value !== '' ? Number(e.target.value) : '' })}
                            />
                          ) : col.type === 'date' ? (
                            <input 
                              type="date" 
                              className="form-control"
                              value={editFormData[col.key] || ''}
                              onChange={(e) => setEditFormData({ ...editFormData, [col.key]: e.target.value })}
                            />
                          ) : (
                            <input 
                              type="text" 
                              className="form-control"
                              value={editFormData[col.key] || ''}
                              onChange={(e) => setEditFormData({ ...editFormData, [col.key]: e.target.value })}
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="modal-footer bg-light">
                    <button type="button" className="btn btn-outline-secondary" onClick={() => setShowEditModal(false)}>Cancel</button>
                    <button type="submit" className="btn btn-primary px-4" disabled={submitting}>
                      {submitting ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      )}

      {/* 📥 Stack Add (Bulk Import) Modal */}
      {showStackAddModal && (
        <>
          <div className="modal-backdrop fade show" style={{ zIndex: 1040 }}></div>
          <div className="modal fade show d-block" tabIndex="-1" style={{ zIndex: 1050 }}>
            <div className="modal-dialog modal-dialog-centered modal-lg">
              <div className="modal-content border-0 shadow-lg">
                <div className="modal-header bg-primary text-white">
                  <h5 className="modal-title fw-bold">📥 Stack Add — Bulk Import Dataset</h5>
                  <button type="button" className="btn-close btn-close-white" onClick={() => setShowStackAddModal(false)}></button>
                </div>
                
                <div className="modal-body p-4">
                  {/* Source Tabs */}
                  <ul className="nav nav-pills nav-fill mb-4 p-1 bg-light rounded border">
                    <li className="nav-item">
                      <button 
                        className={`nav-link fw-semibold ${importSourceTab === 'local' ? 'active bg-primary' : 'text-secondary'}`}
                        onClick={() => handleTabChange('local')}
                      >
                        📁 Local File Upload (.csv / .xlsx)
                      </button>
                    </li>
                    <li className="nav-item">
                      <button 
                        className={`nav-link fw-semibold ${importSourceTab === 'team' ? 'active bg-primary' : 'text-secondary'}`}
                        onClick={() => handleTabChange('team')}
                      >
                        👥 Team Repository
                      </button>
                    </li>
                    <li className="nav-item">
                      <button 
                        className={`nav-link fw-semibold ${importSourceTab === 'personal' ? 'active bg-primary' : 'text-secondary'}`}
                        onClick={() => handleTabChange('personal')}
                      >
                        🔒 Personal Repository
                      </button>
                    </li>
                  </ul>

                  {/* Tab 1: Local File Upload */}
                  {importSourceTab === 'local' && (
                    <div className="mb-3">
                      <label className="form-label fw-semibold text-dark">Select Dataset File (.csv, .xlsx, .xls)</label>
                      <input 
                        type="file" 
                        className="form-control form-control-lg mb-2"
                        accept=".csv, .xlsx, .xls"
                        onChange={handleStackFileChange}
                      />
                      <div className="d-flex justify-content-between align-items-center mt-2">
                        <span className="small text-secondary">Accepted formats: Standard CSV or Excel Spreadsheets.</span>
                        <button type="button" className="btn btn-link btn-sm p-0 text-decoration-none" onClick={downloadSampleTemplate}>
                          📥 Download Sample CSV Template
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Tab 2 & 3: Team / Personal Repository Selection */}
                  {(importSourceTab === 'team' || importSourceTab === 'personal') && (
                    <div className="mb-3">
                      <label className="form-label fw-semibold text-dark">
                        Select Dataset Document from {importSourceTab === 'team' ? 'Team Repository' : 'Personal Repository'}
                      </label>
                      {loadingRepoDocs ? (
                        <div className="text-center py-4">
                          <span className="spinner-border spinner-border-sm me-2 text-primary"></span>
                          Loading available repository documents...
                        </div>
                      ) : repoDocs.length > 0 ? (
                        <div className="list-group max-height-250 overflow-auto border rounded">
                          {repoDocs.map(doc => (
                            <button
                              key={doc.id}
                              type="button"
                              className={`list-group-item list-group-item-action d-flex justify-content-between align-items-center ${selectedRepoDoc?.id === doc.id ? 'active' : ''}`}
                              onClick={() => handleSelectRepoDocument(doc)}
                            >
                              <div>
                                <div className="fw-semibold">{doc.title || doc.source_document?.original_name}</div>
                                <div className="small opacity-75">{doc.record_count || 0} records • Ingested: {new Date(doc.created_at).toLocaleDateString()}</div>
                              </div>
                              <span className="badge bg-light text-dark font-monospace">{doc.document_type || 'DATASET'}</span>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <div className="alert alert-warning py-3 mb-0">
                          No valid dataset files found in {importSourceTab === 'team' ? 'Team Repository' : 'Personal Repository'}. Please upload a dataset file first.
                        </div>
                      )}
                    </div>
                  )}

                  {/* Data Preview Table */}
                  {stackPreviewRows.length > 0 && (
                    <div className="mt-4">
                      <h6 className="fw-bold text-secondary mb-2">Dataset Preview (First {stackPreviewRows.length} Rows):</h6>
                      <div className="table-responsive border rounded max-height-200 overflow-auto">
                        <table className="table table-sm table-striped mb-0 small">
                          <thead className="table-light">
                            <tr>
                              {stackPreviewHeaders.map(h => (
                                <th key={h}>{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {stackPreviewRows.map((row, rIdx) => (
                              <tr key={rIdx}>
                                {stackPreviewHeaders.map(h => (
                                  <td key={h}>{row[h] !== undefined ? String(row[h]) : ''}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Errors / Success Status */}
                  {stackError && <div className="alert alert-danger py-2 mt-3 mb-0">{stackError}</div>}
                  {stackSuccessMsg && <div className="alert alert-success py-2 mt-3 mb-0">{stackSuccessMsg}</div>}

                </div>

                <div className="modal-footer bg-light">
                  <button type="button" className="btn btn-outline-secondary" onClick={() => setShowStackAddModal(false)}>Close</button>
                  <button 
                    type="button" 
                    className="btn btn-primary px-4 fw-bold"
                    onClick={handleStackAddSubmit}
                    disabled={stackUploading || (importSourceTab === 'local' && !stackFile) || ((importSourceTab === 'team' || importSourceTab === 'personal') && !selectedRepoDoc)}
                  >
                    {stackUploading ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2"></span>
                        Importing Dataset...
                      </>
                    ) : '📥 Import Dataset'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Single Add Record Modal (Dynamic) */}
      {showAddModal && (
        <>
          <div className="modal-backdrop fade show" style={{ zIndex: 1040 }}></div>
          <div className="modal fade show d-block" tabIndex="-1" style={{ zIndex: 1050 }}>
            <div className="modal-dialog modal-dialog-centered modal-lg">
              <div className="modal-content border-0 shadow-lg">
                <div className="modal-header bg-primary text-white">
                  <h5 className="modal-title fw-bold">+ Add New Record</h5>
                  <button type="button" className="btn-close btn-close-white" onClick={() => setShowAddModal(false)}></button>
                </div>
                <form onSubmit={handleAddRecord}>
                  <div className="modal-body p-4">
                    {formError && <div className="alert alert-danger py-2 mb-3">{formError}</div>}
                    {formSuccess && <div className="alert alert-success py-2 mb-3">{formSuccess}</div>}

                    <div className="row g-3">
                      {activeSchema.map(col => (
                        <div key={col.key} className="col-12 col-md-6">
                          <label className="form-label small text-secondary fw-semibold">{col.label}</label>
                          {col.type === 'number' ? (
                            <input 
                              type="number" 
                              className="form-control"
                              placeholder={`Enter ${col.label}`}
                              value={addFormData[col.key] !== undefined ? addFormData[col.key] : ''}
                              onChange={(e) => setAddFormData({ ...addFormData, [col.key]: e.target.value !== '' ? Number(e.target.value) : '' })}
                            />
                          ) : col.type === 'date' ? (
                            <input 
                              type="date" 
                              className="form-control"
                              value={addFormData[col.key] || ''}
                              onChange={(e) => setAddFormData({ ...addFormData, [col.key]: e.target.value })}
                            />
                          ) : (
                            <input 
                              type="text" 
                              className="form-control"
                              placeholder={`Enter ${col.label}`}
                              value={addFormData[col.key] || ''}
                              onChange={(e) => setAddFormData({ ...addFormData, [col.key]: e.target.value })}
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="modal-footer bg-light">
                    <button type="button" className="btn btn-outline-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
                    <button type="submit" className="btn btn-primary px-4" disabled={submitting}>
                      {submitting ? 'Saving...' : 'Save Record'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      )}

    </div>
  );
};

class EmployeeDirectoryErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("EmployeeDirectory rendering error caught by boundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="alert alert-danger p-4 rounded-3 shadow-sm my-4">
          <h4 className="fw-bold text-danger mb-2">⚠️ Record Directory Interface Warning</h4>
          <p className="mb-3">A rendering error occurred while displaying directory records.</p>
          <pre className="bg-dark text-light p-3 rounded font-monospace small mb-3">
            {this.state.error?.toString() || 'Unknown rendering exception'}
          </pre>
          <button 
            className="btn btn-outline-danger fw-bold"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            🔄 Reload Directory Interface
          </button>
        </div>
      );
    }
    return <EmployeeDirectory {...this.props} />;
  }
}

export default EmployeeDirectoryErrorBoundary;
