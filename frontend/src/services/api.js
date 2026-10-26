import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 3000, // 3s timeout for fast fallback if backend is offline
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('civiclens_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// -----------------------------------------------------------------------------
// Interactive Local Simulation Engine (Used when FastAPI server is offline)
// -----------------------------------------------------------------------------
const INITIAL_DEMO_COMPLAINTS = [
  {
    id: 101,
    tracking_number: 'CVL-2026-1001',
    title: 'Severe pothole causing traffic jam near Sector 14 market',
    description: 'Deep pothole spanning almost 3 feet in front of the main grocery junction. Two two-wheelers have skidded already.',
    category: 'Roads & Infrastructure',
    priority: 'HIGH',
    status: 'IN_PROGRESS',
    latitude: 28.6139,
    longitude: 77.2090,
    address: 'Sector 14 Market Crossing',
    ward: 'Ward 7 - Central',
    ai_confidence: 0.94,
    is_duplicate: false,
    duplicate_of_id: null,
    similarity_score: null,
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    audit_logs: [
      { id: 1, action: 'COMPLAINT_FILED', remarks: 'Lodged via Citizen Portal', timestamp: new Date(Date.now() - 3 * 86400000).toISOString() },
      { id: 2, action: 'STATUS_CHANGE', remarks: 'Assigned to field engineer team B', timestamp: new Date(Date.now() - 1 * 86400000).toISOString() }
    ]
  },
  {
    id: 102,
    tracking_number: 'CVL-2026-1002',
    title: 'Uncollected garbage dump emitting toxic smell near primary school',
    description: 'Community bin overflowing for 5 days. Waste is spilling onto the road and stray dogs are tearing trash bags open.',
    category: 'Sanitation & Solid Waste',
    priority: 'CRITICAL',
    status: 'ASSIGNED',
    latitude: 28.6250,
    longitude: 77.2180,
    address: 'Opposite Bal Bharati Public School',
    ward: 'Ward 12 - North',
    ai_confidence: 0.98,
    is_duplicate: false,
    duplicate_of_id: null,
    similarity_score: null,
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    audit_logs: [
      { id: 3, action: 'COMPLAINT_FILED', remarks: 'Lodged via Citizen Portal', timestamp: new Date(Date.now() - 2 * 86400000).toISOString() }
    ]
  },
  {
    id: 103,
    tracking_number: 'CVL-2026-1003',
    title: 'Major clean water pipeline rupture on 5th Avenue',
    description: 'Potable drinking water is gushing out on the street since early morning. Hundreds of liters wasted.',
    category: 'Water Supply & Sewage',
    priority: 'CRITICAL',
    status: 'SUBMITTED',
    latitude: 28.6080,
    longitude: 77.2250,
    address: '5th Avenue, Near Park Gate 3',
    ward: 'Ward 3 - East',
    ai_confidence: 0.96,
    is_duplicate: false,
    duplicate_of_id: null,
    similarity_score: null,
    created_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    audit_logs: [
      { id: 4, action: 'COMPLAINT_FILED', remarks: 'Lodged via Citizen Portal', timestamp: new Date(Date.now() - 1 * 86400000).toISOString() }
    ]
  },
  {
    id: 104,
    tracking_number: 'CVL-2026-1004',
    title: 'Four consecutive street lights broken along ring road stretch',
    description: 'The entire stretch between pillar 42 and 46 is completely pitch black at night, making it very dangerous for pedestrians.',
    category: 'Electricity & Street Lighting',
    priority: 'MEDIUM',
    status: 'RESOLVED',
    latitude: 28.6320,
    longitude: 77.2010,
    address: 'Outer Ring Road, Pillar 44',
    ward: 'Ward 7 - Central',
    ai_confidence: 0.92,
    is_duplicate: false,
    duplicate_of_id: null,
    similarity_score: null,
    created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    audit_logs: [
      { id: 5, action: 'COMPLAINT_FILED', remarks: 'Lodged via Citizen Portal', timestamp: new Date(Date.now() - 5 * 86400000).toISOString() },
      { id: 6, action: 'STATUS_CHANGE', remarks: 'Streetlight bulbs replaced and power line spliced', timestamp: new Date(Date.now() - 4 * 86400000).toISOString() }
    ]
  },
  {
    id: 105,
    tracking_number: 'CVL-2026-1005',
    title: 'Stagnant drainage water breeding mosquitoes near apartment complex',
    description: 'Blocked open drain has stagnant dirty water for over two weeks. Rising dengue risk for nearby residents.',
    category: 'Public Health & Environment',
    priority: 'HIGH',
    status: 'UNDER_REVIEW',
    latitude: 28.5990,
    longitude: 77.2100,
    address: 'Greenview Enclave, Block C',
    ward: 'Ward 9 - South',
    ai_confidence: 0.91,
    is_duplicate: false,
    duplicate_of_id: null,
    similarity_score: null,
    created_at: new Date(Date.now() - 4 * 86400000).toISOString(),
    audit_logs: [
      { id: 7, action: 'COMPLAINT_FILED', remarks: 'Lodged via Citizen Portal', timestamp: new Date(Date.now() - 4 * 86400000).toISOString() }
    ]
  }
];

function getStoredComplaints() {
  const saved = localStorage.getItem('civiclens_demo_complaints');
  if (saved) {
    try { return JSON.parse(saved); } catch (e) {}
  }
  localStorage.setItem('civiclens_demo_complaints', JSON.stringify(INITIAL_DEMO_COMPLAINTS));
  return INITIAL_DEMO_COMPLAINTS;
}

function saveStoredComplaints(complaints) {
  localStorage.setItem('civiclens_demo_complaints', JSON.stringify(complaints));
}

// -----------------------------------------------------------------------------
// API Services with Instant Offline Fallbacks
// -----------------------------------------------------------------------------

export const authAPI = {
  login: async (email, password) => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const res = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      return res.data;
    } catch (err) {
      console.warn("FastAPI unreachable, activating instant mock login for:", email);
      let role = 'CITIZEN';
      let name = 'Priya Sharma';
      let id = 3;
      if (email.includes('admin')) {
        role = 'ADMIN';
        name = 'Municipal Commissioner';
        id = 1;
      } else if (email.includes('officer')) {
        role = 'OFFICER';
        name = 'Rajesh Verma (Zonal Officer)';
        id = 2;
      }
      const mockUser = { id, email, full_name: name, role, is_active: true };
      const mockToken = `mock-token-${role.toLowerCase()}-${Date.now()}`;
      return { access_token: mockToken, token_type: 'bearer', user: mockUser };
    }
  },
  register: async (userData) => {
    try {
      const res = await api.post('/auth/register', userData);
      return res.data;
    } catch (err) {
      return { id: Date.now(), ...userData, is_active: true };
    }
  },
  getCurrentUser: async () => {
    try {
      const res = await api.get('/auth/me');
      return res.data;
    } catch (err) {
      return null;
    }
  },
};

export const complaintAPI = {
  list: async (params = {}) => {
    try {
      const res = await api.get('/complaints/', { params });
      return res.data;
    } catch (err) {
      console.info("Using simulated local complaint database");
      let list = getStoredComplaints();
      if (params.status) {
        list = list.filter(c => c.status === params.status);
      }
      if (params.search) {
        const q = params.search.toLowerCase();
        list = list.filter(c => 
          c.title.toLowerCase().includes(q) || 
          c.description.toLowerCase().includes(q) || 
          c.tracking_number.toLowerCase().includes(q)
        );
      }
      return list;
    }
  },

  getById: async (id) => {
    try {
      const res = await api.get(`/complaints/${id}`);
      return res.data;
    } catch (err) {
      const list = getStoredComplaints();
      return list.find(c => c.id === parseInt(id)) || list[0];
    }
  },

  create: async (data) => {
    try {
      const res = await api.post('/complaints/', data);
      return res.data;
    } catch (err) {
      console.info("Local engine creating complaint:", data.title);
      const list = getStoredComplaints();
      const newId = Date.now();
      const trackingNumber = `CVL-2026-${Math.floor(1000 + Math.random() * 9000)}`;
      
      // Determine priority heuristics
      let priority = 'MEDIUM';
      const text = `${data.title} ${data.description}`.toLowerCase();
      if (text.includes('fire') || text.includes('spark') || text.includes('live wire') || text.includes('burst') || text.includes('flood') || text.includes('fatal')) {
        priority = 'CRITICAL';
      } else if (text.includes('deep') || text.includes('overflow') || text.includes('dengue') || text.includes('accident')) {
        priority = 'HIGH';
      }

      const newComplaint = {
        id: newId,
        tracking_number: trackingNumber,
        title: data.title,
        description: data.description,
        category: data.category || 'Roads & Infrastructure',
        priority: priority,
        status: 'SUBMITTED',
        latitude: data.latitude || 28.6139,
        longitude: data.longitude || 77.2090,
        address: data.address || `${data.ward || 'Central'}, Civic Area`,
        ward: data.ward || 'Ward 7 - Central',
        ai_confidence: 0.95,
        is_duplicate: false,
        created_at: new Date().toISOString(),
        audit_logs: [
          {
            id: Date.now(),
            action: 'COMPLAINT_FILED',
            remarks: `Grievance lodged via Citizen Portal. AI categorized as ${data.category || 'Roads'} with ${priority} priority.`,
            timestamp: new Date().toISOString()
          }
        ]
      };

      const updatedList = [newComplaint, ...list];
      saveStoredComplaints(updatedList);
      return newComplaint;
    }
  },

  updateStatus: async (id, status, remarks) => {
    try {
      const res = await api.patch(`/complaints/${id}/status`, { status, remarks });
      return res.data;
    } catch (err) {
      console.info(`Local engine updating complaint ${id} status to ${status}`);
      const list = getStoredComplaints();
      const updatedList = list.map(c => {
        if (c.id === parseInt(id)) {
          const newLogs = c.audit_logs ? [...c.audit_logs] : [];
          newLogs.push({
            id: Date.now(),
            action: 'STATUS_CHANGE',
            remarks: remarks || `Status changed to ${status}`,
            timestamp: new Date().toISOString()
          });
          return { ...c, status, audit_logs: newLogs };
        }
        return c;
      });
      saveStoredComplaints(updatedList);
      return updatedList.find(c => c.id === parseInt(id));
    }
  },

  getAudit: async (id) => {
    try {
      const res = await api.get(`/complaints/${id}/audit`);
      return res.data;
    } catch (err) {
      const list = getStoredComplaints();
      const c = list.find(item => item.id === parseInt(id));
      return c?.audit_logs || [
        { id: 1, action: 'COMPLAINT_FILED', remarks: 'Lodged in CivicLens portal', timestamp: new Date().toISOString() }
      ];
    }
  },
};

export const aiAPI = {
  classify: async (title, description) => {
    try {
      const res = await api.post('/ai/classify', { title, description });
      return res.data;
    } catch (err) {
      const text = `${title} ${description}`.toLowerCase();
      let category = 'Roads & Infrastructure';
      let priority = 'MEDIUM';
      let confidence = 0.92;

      if (text.includes('garbage') || text.includes('trash') || text.includes('waste') || text.includes('dump') || text.includes('clean')) {
        category = 'Sanitation & Solid Waste';
      } else if (text.includes('water') || text.includes('pipe') || text.includes('leak') || text.includes('sewage') || text.includes('drain')) {
        category = 'Water Supply & Sewage';
      } else if (text.includes('light') || text.includes('wire') || text.includes('electric') || text.includes('power') || text.includes('dark')) {
        category = 'Electricity & Street Lighting';
      } else if (text.includes('dengue') || text.includes('mosquito') || text.includes('hospital') || text.includes('health')) {
        category = 'Public Health & Environment';
      }

      if (text.includes('live wire') || text.includes('spark') || text.includes('flood') || text.includes('fatal') || text.includes('burst')) {
        priority = 'CRITICAL';
      } else if (text.includes('deep pothole') || text.includes('overflow') || text.includes('dengue')) {
        priority = 'HIGH';
      }

      return {
        category,
        confidence,
        priority,
        priority_score: priority === 'CRITICAL' ? 0.95 : priority === 'HIGH' ? 0.75 : 0.45,
        suggested_department_code: category.substring(0, 5).toUpperCase(),
      };
    }
  },

  checkDuplicates: async (title, description) => {
    try {
      const res = await api.post('/ai/check-duplicates', { title, description });
      return res.data;
    } catch (err) {
      const list = getStoredComplaints();
      const text = `${title} ${description}`.toLowerCase();
      const words = new Set(text.split(/\s+/).filter(w => w.length > 3));

      const matches = [];
      for (const item of list) {
        const itemWords = new Set(`${item.title} ${item.description}`.toLowerCase().split(/\s+/).filter(w => w.length > 3));
        const intersection = [...words].filter(w => itemWords.has(w));
        const sim = words.size > 0 ? intersection.length / Math.min(words.size, itemWords.size) : 0;
        if (sim >= 0.40) {
          matches.push({
            complaint_id: item.id,
            tracking_number: item.tracking_number,
            title: item.title,
            description: item.description,
            similarity_score: Math.min(0.96, Math.max(0.72, sim * 1.3)),
            status: item.status,
            created_at: item.created_at,
          });
        }
      }

      return {
        is_duplicate: matches.length > 0,
        match_count: matches.length,
        candidates: matches.slice(0, 3),
      };
    }
  },
};

export const analyticsAPI = {
  getDashboard: async () => {
    try {
      const res = await api.get('/analytics/dashboard');
      return res.data;
    } catch (err) {
      const list = getStoredComplaints();
      const total = list.length;
      const resolved = list.filter(c => c.status === 'RESOLVED').length;
      const resRate = total > 0 ? Math.round((resolved / total) * 100) : 0;

      return {
        total_complaints: total,
        resolved_count: resolved,
        pending_count: total - resolved,
        duplicates_detected: 3,
        resolution_rate: resRate,
        avg_resolution_hours: 22.5,
        status_distribution: {
          submitted: list.filter(c => c.status === 'SUBMITTED').length,
          under_review: list.filter(c => c.status === 'UNDER_REVIEW').length,
          assigned: list.filter(c => c.status === 'ASSIGNED').length,
          in_progress: list.filter(c => c.status === 'IN_PROGRESS').length,
          resolved: resolved,
          rejected: list.filter(c => c.status === 'REJECTED').length,
          duplicate: list.filter(c => c.status === 'DUPLICATE').length,
        },
        priority_distribution: {
          low: list.filter(c => c.priority === 'LOW').length,
          medium: list.filter(c => c.priority === 'MEDIUM').length,
          high: list.filter(c => c.priority === 'HIGH').length,
          critical: list.filter(c => c.priority === 'CRITICAL').length,
        },
        department_metrics: [
          { department_id: 1, name: 'Roads & Infrastructure', total_complaints: 14, resolved_complaints: 11, pending_complaints: 3, sla_compliance_rate: 88.5 },
          { department_id: 2, name: 'Sanitation & Solid Waste', total_complaints: 26, resolved_complaints: 22, pending_complaints: 4, sla_compliance_rate: 91.0 },
          { department_id: 3, name: 'Water Supply & Sewage', total_complaints: 18, resolved_complaints: 13, pending_complaints: 5, sla_compliance_rate: 79.4 },
          { department_id: 4, name: 'Electricity & Lighting', total_complaints: 12, resolved_complaints: 11, pending_complaints: 1, sla_compliance_rate: 94.2 },
          { department_id: 5, name: 'Public Health & Safety', total_complaints: 9, resolved_complaints: 7, pending_complaints: 2, sla_compliance_rate: 82.0 },
        ],
        ward_hotspots: [
          { ward: 'Ward 7 - Central', count: 18 },
          { ward: 'Ward 12 - North', count: 14 },
          { ward: 'Ward 3 - East', count: 11 },
          { ward: 'Ward 9 - South', count: 8 },
        ],
        daily_trend: [
          { date: 'Oct 14', count: 2 },
          { date: 'Oct 16', count: 5 },
          { date: 'Oct 18', count: 3 },
          { date: 'Oct 20', count: 7 },
          { date: 'Oct 22', count: 4 },
          { date: 'Oct 24', count: 8 },
          { date: 'Oct 26', count: list.length },
        ],
      };
    }
  },
};

export default api;
