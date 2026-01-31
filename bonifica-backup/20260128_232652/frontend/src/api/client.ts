javascript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
});

export default {
  searchEvents(params) {
    return apiClient.get('/api/events', { params });
  },
  getEvent(id) {
    return apiClient.get(`/api/events/${id}`);
  },
  createEvent(payload) {
    return apiClient.post('/api/events', payload);
  }
};