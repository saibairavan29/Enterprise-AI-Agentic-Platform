import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1/';

const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach access token
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Handle token refresh on 401 Unauthorized
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Check if error status is 401 and not already retried
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (refreshToken) {
        try {
          // Attempt token refresh
          // Note: we use direct axios here to prevent infinite loop
          const response = await axios.post(`${API_URL}auth/login/refresh/`, {
            refresh: refreshToken,
          });
          
          if (response.status === 200) {
            const { access } = response.data.data;
            localStorage.setItem('access_token', access);
            
            // Retry the original request with new token
            originalRequest.headers.Authorization = `Bearer ${access}`;
            return client(originalRequest);
          }
        } catch (refreshError) {
          // Token refresh failed, user session is invalid. Trigger logout event.
          console.error('Refresh token expired or invalid:', refreshError);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.dispatchEvent(new Event('auth-logout'));
        }
      }
    }
    
    return Promise.reject(error);
  }
);

export default client;
