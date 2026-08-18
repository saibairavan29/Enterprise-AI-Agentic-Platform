import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [isRegister, setIsRegister] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    passwordConfirm: '',
    firstName: '',
    lastName: '',
    phone: '',
    role: 'reader',
  });

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setSubmitting(true);

    if (isRegister) {
      // Validate confirm password
      if (formData.password !== formData.passwordConfirm) {
        setErrorMsg('Passwords do not match');
        setSubmitting(false);
        return;
      }
      
      const payload = {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        password_confirm: formData.passwordConfirm,
        first_name: formData.firstName,
        last_name: formData.lastName,
        phone_number: formData.phone,
        role: formData.role,
      };

      const res = await register(payload);
      if (res.success) {
        setSuccessMsg('Registration successful! Please sign in.');
        setIsRegister(false);
        setFormData((prev) => ({
          ...prev,
          password: '',
          passwordConfirm: '',
        }));
      } else {
        setErrorMsg(res.message);
      }
    } else {
      const res = await login(formData.username, formData.password);
      if (res.success) {
        navigate('/');
      } else {
        setErrorMsg(res.message);
      }
    }
    setSubmitting(false);
  };

  return (
    <div className="container-fluid d-flex align-items-center justify-content-center min-vh-100" style={{ backgroundColor: 'var(--bg-secondary)' }}>
      <div className="row w-100 justify-content-center">
        <div className="col-12 col-md-8 col-lg-5">
          <div className="glass-panel pulse-glow p-5">
            <div className="text-center mb-4">
              <h2 className="text-gradient-glowing fw-bold mb-2">Enterprise Decision Intelligence</h2>
              <p className="text-secondary small">{isRegister ? 'Create an enterprise identity' : 'Verify credentials'}</p>
            </div>

            {errorMsg && (
              <div className="alert alert-danger border-0 py-2">
                {errorMsg}
              </div>
            )}
            
            {successMsg && (
              <div className="alert alert-success border-0 py-2">
                {successMsg}
              </div>
            )}

            <form onSubmit={handleAuthSubmit}>
              <div className="mb-3">
                <label className="form-label text-secondary small fw-medium">Username</label>
                <input
                  type="text"
                  name="username"
                  className="form-control bg-white border-secondary text-dark"
                  placeholder="Enter username"
                  value={formData.username}
                  onChange={handleInputChange}
                  required
                />
              </div>

              {isRegister && (
                <>
                  <div className="mb-3">
                    <label className="form-label text-secondary small fw-medium">Email Address</label>
                     <input
                      type="email"
                      name="email"
                      className="form-control bg-white border-secondary text-dark"
                      placeholder="Enter email"
                      value={formData.email}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                  <div className="row">
                    <div className="col-6 mb-3">
                      <label className="form-label text-secondary small fw-medium">First Name</label>
                       <input
                        type="text"
                        name="firstName"
                        className="form-control bg-white border-secondary text-dark"
                        placeholder="First"
                        value={formData.firstName}
                        onChange={handleInputChange}
                      />
                    </div>
                    <div className="col-6 mb-3">
                      <label className="form-label text-secondary small fw-medium">Last Name</label>
                      <input
                        type="text"
                        name="lastName"
                        className="form-control bg-white border-secondary text-dark"
                        placeholder="Last"
                        value={formData.lastName}
                        onChange={handleInputChange}
                      />
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-6 mb-3">
                      <label className="form-label text-secondary small fw-medium">Phone</label>
                       <input
                        type="text"
                        name="phone"
                        className="form-control bg-white border-secondary text-dark"
                        placeholder="Phone"
                        value={formData.phone}
                        onChange={handleInputChange}
                      />
                    </div>
                    <div className="col-6 mb-3">
                      <label className="form-label text-secondary small fw-medium">System Role</label>
                      <select
                        name="role"
                        className="form-select bg-white border-secondary text-dark"
                        value={formData.role}
                        onChange={handleInputChange}
                      >
                        <option value="reader">Reader</option>
                        <option value="analyst">Analyst</option>
                        <option value="admin">Admin</option>
                      </select>
                    </div>
                  </div>
                </>
              )}

              <div className="mb-3">
                <label className="form-label text-secondary small fw-medium">Password</label>
                 <input
                  type="password"
                  name="password"
                  className="form-control bg-white border-secondary text-dark"
                  placeholder="Enter password"
                  value={formData.password}
                  onChange={handleInputChange}
                  required
                />
              </div>

              {isRegister && (
                <div className="mb-4">
                  <label className="form-label text-secondary small fw-medium">Confirm Password</label>
                   <input
                    type="password"
                    name="passwordConfirm"
                    className="form-control bg-white border-secondary text-dark"
                    placeholder="Confirm password"
                    value={formData.passwordConfirm}
                    onChange={handleInputChange}
                    required
                  />
                </div>
              )}

              <button
                type="submit"
                className="btn btn-premium-primary w-100 mb-3"
                disabled={submitting}
              >
                {submitting ? 'Processing...' : isRegister ? 'Register' : 'Sign In'}
              </button>

              <div className="text-center">
                <button
                  type="button"
                  className="btn btn-link text-decoration-none text-secondary small p-0"
                  onClick={() => {
                    setIsRegister(!isRegister);
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                >
                  {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Register"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
