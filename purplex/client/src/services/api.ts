const API_BASE_URL = 'http://localhost:8000/api';

// Handler for login
async function fetchAPI(endpoint: string, options: RequestInit = {}) {

  try {

    const userData = localStorage.getItem('user');
    // Always set a bearer token for authentication
    let authHeaders = {
      'Authorization': 'Bearer debug'
    };

    // If we have user data, try to use their token
    if (userData) {
      try {
        const user = JSON.parse(userData);
        if (user.token) {
          authHeaders = {
            'Authorization': `Bearer ${user.token}`
          };
        }
      } catch (e) {
        console.error('Error parsing user data:', e);
      }
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options.headers
      }
    });
    if (!response.ok) {
      if (response.status === 401) {
        console.error('Unauthorized request:', response);
      } else if (response.status === 403) {
        console.error('Forbidden request:', response);
      }
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// Problems API
export const problemsAPI = {
  getAllProblems: () => fetchAPI('/problems/'),
  getProblemSets: () => fetchAPI('/problem-sets/'),
  getProblemSet: (sid: string) => fetchAPI(`/problem-set/${sid}`)
};

// Submissions API
export const submissionsAPI = {
  testCode: (payload: any) => fetchAPI('/test/', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  submitCode: (problemId: string, code: string) => fetchAPI(`/submit_code/${problemId}/`, {
    method: 'POST',
    body: JSON.stringify({ code })
  })
};

// AI Generation API
export const aiAPI = {
  generateCode: (prompt: string) => fetchAPI('/generate/', {
    method: 'POST',
    body: JSON.stringify({ prompt })
  })
};

export default {
  problems: problemsAPI,
  submissions: submissionsAPI,
  ai: aiAPI
};
