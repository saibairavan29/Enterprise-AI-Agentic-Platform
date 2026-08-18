import React, { useState, useEffect } from 'react';
import client from '../api/client';

const EmployeeDirectory = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  // Search and Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortField, setSortField] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  
  // Selection and Profile details drawer
  const [selectedEmp, setSelectedEmp] = useState(null);
  
  // Pagination States
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const fetchEmployees = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      // Query the API endpoint we created
      const res = await client.get('repository/employees/');
      const data = res.data.results || res.data.data || [];
      setEmployees(data);
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to load employee directory records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  // Utility to extract safe detail values
  const getEmpDataVal = (emp, fieldName) => {
    return emp.employee_details?.[fieldName] || 'N/A';
  };

  // Client-side filtering & sorting
  const filteredEmployees = employees.filter(emp => {
    const details = emp.employee_details || {};
    const name = (details.name || '').toLowerCase();
    const role = (details.role || '').toLowerCase();
    const dept = (details.department || '').toLowerCase();
    const project = (details.current_project || '').toLowerCase();
    const skills = (details.skills || '').toLowerCase();
    const status = (details.employment_status || '').toLowerCase();
    const empId = (details.employee_id || '').toLowerCase();

    const searchLower = searchQuery.toLowerCase();
    const matchesSearch = 
      name.includes(searchLower) ||
      role.includes(searchLower) ||
      dept.includes(searchLower) ||
      project.includes(searchLower) ||
      skills.includes(searchLower) ||
      empId.includes(searchLower);

    const matchesDept = !deptFilter || dept === deptFilter.toLowerCase();
    const matchesRole = !roleFilter || role === roleFilter.toLowerCase();
    const matchesStatus = !statusFilter || status === statusFilter.toLowerCase();

    return matchesSearch && matchesDept && matchesRole && matchesStatus;
  });

  // Unique lists for dropdown filters
  const departments = Array.from(new Set(employees.map(e => getEmpDataVal(e, 'department')).filter(d => d !== 'N/A')));
  const roles = Array.from(new Set(employees.map(e => getEmpDataVal(e, 'role')).filter(r => r !== 'N/A')));
  const statuses = Array.from(new Set(employees.map(e => getEmpDataVal(e, 'employment_status')).filter(s => s !== 'N/A')));

  // Sorting
  const sortedEmployees = [...filteredEmployees].sort((a, b) => {
    let valA = getEmpDataVal(a, sortField);
    let valB = getEmpDataVal(b, sortField);
    
    // Sort logic
    if (typeof valA === 'string') valA = valA.toLowerCase();
    if (typeof valB === 'string') valB = valB.toLowerCase();
    
    if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  // Pagination bounds
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = sortedEmployees.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(sortedEmployees.length / itemsPerPage);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  return (
    <div className="row g-4 position-relative">
      <div className={selectedEmp ? "col-12 col-lg-8" : "col-12"}>
        <div className="bg-white rounded-3 shadow-sm border p-4">
          
          {/* Filters Area */}
          <div className="row g-3 mb-4 align-items-end">
            <div className="col-12 col-md-4">
              <label className="form-label small text-secondary fw-semibold">Search Directory</label>
              <input 
                type="text" 
                className="form-control"
                placeholder="Search name, role, skills, project..."
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
              />
            </div>
            
            <div className="col-6 col-md-2">
              <label className="form-label small text-secondary fw-semibold">Department</label>
              <select 
                className="form-select text-capitalize"
                value={deptFilter}
                onChange={(e) => { setDeptFilter(e.target.value); setCurrentPage(1); }}
              >
                <option value="">All Departments</option>
                {departments.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            
            <div className="col-6 col-md-2">
              <label className="form-label small text-secondary fw-semibold">Role</label>
              <select 
                className="form-select text-capitalize"
                value={roleFilter}
                onChange={(e) => { setRoleFilter(e.target.value); setCurrentPage(1); }}
              >
                <option value="">All Roles</option>
                {roles.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>

            <div className="col-6 col-md-2">
              <label className="form-label small text-secondary fw-semibold">Status</label>
              <select 
                className="form-select text-capitalize"
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
              >
                <option value="">All Statuses</option>
                {statuses.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div className="col-6 col-md-2 d-flex gap-2">
              <button className="btn btn-outline-secondary w-100" onClick={fetchEmployees} disabled={loading}>
                Refresh
              </button>
            </div>
          </div>

          {errorMsg && <div className="alert alert-danger py-2">{errorMsg}</div>}

          {/* Table list */}
          <div className="table-responsive rounded border mb-3">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr className="small text-secondary">
                  <th className="cursor-pointer" onClick={() => handleSort('employee_id')}>
                    Employee ID {sortField === 'employee_id' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="cursor-pointer" onClick={() => handleSort('name')}>
                    Name {sortField === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="cursor-pointer" onClick={() => handleSort('role')}>
                    Role {sortField === 'role' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="cursor-pointer" onClick={() => handleSort('experience_years')}>
                    Experience {sortField === 'experience_years' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="cursor-pointer" onClick={() => handleSort('department')}>
                    Department {sortField === 'department' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th>Current Project</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="7" className="text-center py-5">
                      <span className="spinner-border spinner-border-sm me-2 text-primary" role="status"></span>
                      Loading directory records...
                    </td>
                  </tr>
                ) : currentItems.length > 0 ? (
                  currentItems.map(emp => {
                    const active = getEmpDataVal(emp, 'employment_status').toLowerCase() === 'active';
                    return (
                      <tr 
                        key={emp.id} 
                        className={`cursor-pointer ${selectedEmp?.id === emp.id ? 'table-primary-subtle' : ''}`}
                        onClick={() => setSelectedEmp(selectedEmp?.id === emp.id ? null : emp)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="font-monospace fw-semibold">{getEmpDataVal(emp, 'employee_id')}</td>
                        <td>
                          <div className="fw-semibold text-dark">{getEmpDataVal(emp, 'name')}</div>
                          <div className="text-secondary small font-monospace" style={{ fontSize: '0.75rem' }}>{getEmpDataVal(emp, 'email')}</div>
                        </td>
                        <td className="text-capitalize">{getEmpDataVal(emp, 'role')}</td>
                        <td>{getEmpDataVal(emp, 'experience_years')} Years</td>
                        <td className="text-capitalize">{getEmpDataVal(emp, 'department')}</td>
                        <td>{getEmpDataVal(emp, 'current_project')}</td>
                        <td>
                          <span className={`badge ${active ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'} border border-${active ? 'success' : 'secondary'} rounded-pill px-2 py-1`}>
                            {getEmpDataVal(emp, 'employment_status')}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="7" className="text-center py-5 text-muted">
                      No matching employee records found.
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
                Showing {indexOfFirstItem + 1} to {Math.min(indexOfLastItem, sortedEmployees.length)} of {sortedEmployees.length} employees
              </span>
              <nav>
                <ul className="pagination pagination-sm mb-0">
                  <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                    <button className="page-link" onClick={() => setCurrentPage(currentPage - 1)}>Previous</button>
                  </li>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                    <li key={page} className={`page-item ${currentPage === page ? 'active' : ''}`}>
                      <button className="page-link" onClick={() => setCurrentPage(page)}>{page}</button>
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

      {/* Details Side Panel Drawer */}
      {selectedEmp && (
        <div className="col-12 col-lg-4">
          <div className="bg-white rounded-3 shadow-sm border p-4 sticky-top" style={{ top: '24px' }}>
            <div className="d-flex justify-content-between align-items-start mb-3 pb-2 border-bottom">
              <div>
                <span className="badge bg-primary-subtle text-primary font-monospace mb-1">{getEmpDataVal(selectedEmp, 'employee_id')}</span>
                <h4 className="fw-bold mb-0 text-dark">{getEmpDataVal(selectedEmp, 'name')}</h4>
                <p className="text-secondary small mb-0">{getEmpDataVal(selectedEmp, 'role')}</p>
              </div>
              <button className="btn-close" onClick={() => setSelectedEmp(null)}></button>
            </div>

            <div className="d-flex flex-column gap-3">
              <div>
                <span className="small text-secondary fw-semibold d-block">Department</span>
                <span className="text-dark text-capitalize">{getEmpDataVal(selectedEmp, 'department')}</span>
              </div>

              <div>
                <span className="small text-secondary fw-semibold d-block">Work Location</span>
                <span className="text-dark">{getEmpDataVal(selectedEmp, 'work_location')}</span>
              </div>

              <div>
                <span className="small text-secondary fw-semibold d-block">Current Project</span>
                <span className="text-dark">{getEmpDataVal(selectedEmp, 'current_project')}</span>
              </div>

              <div>
                <span className="small text-secondary fw-semibold d-block">Experience</span>
                <span className="text-dark">{getEmpDataVal(selectedEmp, 'experience_years')} Years</span>
              </div>

              <div>
                <span className="small text-secondary fw-semibold d-block">Employment Status</span>
                <span className="text-dark">{getEmpDataVal(selectedEmp, 'employment_status')}</span>
              </div>

              <div>
                <span className="small text-secondary fw-semibold d-block">Skills & Expertise</span>
                <div className="d-flex flex-wrap gap-1 mt-1">
                  {(getEmpDataVal(selectedEmp, 'skills') !== 'N/A' ? getEmpDataVal(selectedEmp, 'skills').split(',') : []).map(skill => (
                    <span key={skill} className="badge bg-light text-dark border small rounded-pill px-2 py-1">
                      {skill.trim()}
                    </span>
                  )) || <span className="text-muted">None specified</span>}
                </div>
              </div>

              <div>
                <span className="small text-secondary fw-semibold d-block">Joining Date</span>
                <span className="text-dark">{getEmpDataVal(selectedEmp, 'joining_date')}</span>
              </div>

              <div>
                <span className="small text-secondary fw-semibold d-block">Work Email</span>
                <span className="text-dark font-monospace small">{getEmpDataVal(selectedEmp, 'email')}</span>
              </div>

              {/* Administrative metadata, strictly collapsed under an expandable panel */}
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
                      <div>Document ID: {selectedEmp.knowledge_document}</div>
                      <div>Created: {new Date(selectedEmp.created_at).toLocaleDateString()}</div>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmployeeDirectory;
