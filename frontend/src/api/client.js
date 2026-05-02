import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  timeout: 5000,
});

export const api = {
  getDashboard: () => client.get('/dashboard'),
  getWorkItem: (id) => client.get(`/workitems/${id}`),
  getSignals: (id) => client.get(`/workitems/${id}/signals`),
  transitionWorkItem: (id, targetState) => client.patch(`/workitems/${id}/transition`, { target_state: targetState }),
  submitRca: (id, rcaData) => client.post(`/rca/${id}`, rcaData),
};

export default client;
