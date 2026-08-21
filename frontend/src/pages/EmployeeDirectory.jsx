import React, { useState, useEffect } from 'react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';

const EmployeeDirectory = () => {
  const { user } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  // Add Employee Form States
  const [showAddModal, setShowAddModal] = useState(false);
  const [newEmpId, setNewEmpId] = useState('');
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newDept, setNewDept] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newExp, setNewExp] = useState(0);
  const [newProject, setNewProject] = useState('Bench');
  const [newLocation, setNewLocation] = useState('Remote');
  const [newStatus, setNewStatus] = useState('Active');
  const [newSkills, setNewSkills] = useState('');
  const [newSalary, setNewSalary] = useState(0);
  const [newJoiningDate, setNewJoiningDate] = useState('');
  
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  
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

  const handleAddEmployee = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    
    if (!newEmpId || !newName || !newEmail || !newDept || !newRole) {
      setFormError('Please fill out all required fields (Employee ID, Name, Email, Department, Role).');
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await client.post('repository/employees/', {
        employee_id: newEmpId,
        name: newName,
        email: newEmail,
        department: newDept,
        role: newRole,
        experience_years: parseInt(newExp) || 0,
        current_project: newProject,
        work_location: newLocation,
        employment_status: newStatus,
        skills: newSkills,
        salary: parseFloat(newSalary) || 0.0,
        joining_date: newJoiningDate || new Date().toISOString().split('T')[0]
      });
      
      if (res.data.success) {
        setFormSuccess('Employee added successfully!');
        fetchEmployees();
        setNewEmpId('');
        setNewName('');
        setNewEmail('');
        setNewDept('');
        setNewRole('');
        setNewExp(0);
        setNewProject('Bench');
        setNewLocation('Remote');
        setNewStatus('Active');
        setNewSkills('');
        setNewSalary(0);
        setNewJoiningDate('');
        
        setTimeout(() => {
          setShowAddModal(false);
          setFormSuccess('');
        }, 1500);
      } else {
        setFormError(res.data.message || 'Failed to add employee.');
      }
    } catch (err) {
      console.error(err);
      setFormError(err.response?.data?.message || 'Error occurred while saving employee record.');
    } finally {
      setSubmitting(false);
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
              {user?.role === 'admin' && (
                <button className="btn btn-premium-primary text-white w-100" onClick={() => setShowAddModal(true)}>
                  Add
                </button>
              )}
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
      {/* Add Employee Modal Overlay */}
      {showAddModal && (
        <>
          <div className="modal-backdrop fade show" style={{ zIndex: 1040 }}></div>
          <div className="modal fade show d-block" tabIndex="-1" style={{ zIndex: 1050 }}>
            <div className="modal-dialog modal-dialog-centered modal-lg">
              <div className="modal-content shadow border-0 rounded-3 bg-white" style={{ opacity: 1 }}>
                <div className="modal-header bg-light py-3">
                  <h5 className="modal-title fw-bold text-dark">Add New Employee</h5>
                  <button type="button" className="btn-close" onClick={() => setShowAddModal(false)}></button>
                </div>
                <form onSubmit={handleAddEmployee}>
                  <div className="modal-body p-4" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                    {formError && <div className="alert alert-danger py-2">{formError}</div>}
                    {formSuccess && <div className="alert alert-success py-2">{formSuccess}</div>}
                    
                    <div className="row g-3">
                      <div className="col-md-4">
                        <label className="form-label small fw-semibold text-secondary">Employee ID *</label>
                        <input type="text" className="form-control" placeholder="EMP001" value={newEmpId} onChange={(e) => setNewEmpId(e.target.value)} required />
                      </div>
                      <div className="col-md-8">
                        <label className="form-label small fw-semibold text-secondary">Full Name *</label>
                        <input type="text" className="form-control" placeholder="John Doe" value={newName} onChange={(e) => setNewName(e.target.value)} required />
                      </div>
                      
                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-secondary">Work Email *</label>
                        <input type="email" className="form-control" placeholder="johndoe@enterprise.com" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} required />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-secondary">Department *</label>
                        <input type="text" className="form-control" placeholder="Engineering" value={newDept} onChange={(e) => setNewDept(e.target.value)} required />
                      </div>
                      
                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-secondary">Role / Designation *</label>
                        <input type="text" className="form-control" placeholder="Software Engineer" value={newRole} onChange={(e) => setNewRole(e.target.value)} required />
                      </div>
                      <div className="col-md-3">
                        <label className="form-label small fw-semibold text-secondary">Experience (Years)</label>
                        <input type="number" className="form-control" min="0" value={newExp} onChange={(e) => setNewExp(e.target.value)} />
                      </div>
                      <div className="col-md-3">
                        <label className="form-label small fw-semibold text-secondary">Salary (USD/Year)</label>
                        <input type="number" className="form-control" min="0" value={newSalary} onChange={(e) => setNewSalary(e.target.value)} />
                      </div>

                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-secondary">Current Project</label>
                        <input type="text" className="form-control" placeholder="Bench" value={newProject} onChange={(e) => setNewProject(e.target.value)} />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-secondary">Work Location</label>
                        <input type="text" className="form-control" placeholder="Remote" value={newLocation} onChange={(e) => setNewLocation(e.target.value)} />
                      </div>

                      <div className="col-md-12">
                        <label className="form-label small fw-semibold text-secondary">Skills (Comma-separated)</label>
                        <input type="text" className="form-control" placeholder="Python, Django, React, SQL" value={newSkills} onChange={(e) => setNewSkills(e.target.value)} />
                      </div>

                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-secondary">Employment Status</label>
                        <select className="form-select" value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                          <option value="Active">Active</option>
                          <option value="Inactive">Inactive</option>
                          <option value="Suspended">Suspended</option>
                        </select>
                      </div>
                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-secondary">Joining Date</label>
                        <input type="date" className="form-control" value={newJoiningDate} onChange={(e) => setNewJoiningDate(e.target.value)} />
                      </div>
                    </div>
                  </div>
                  <div className="modal-footer bg-light">
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAddModal(false)} disabled={submitting}>Cancel</button>
                    <button type="submit" className="btn btn-premium-primary btn-sm text-white" disabled={submitting}>
                      {submitting ? 'Adding...' : 'Add Employee'}
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

export default EmployeeDirectory;
