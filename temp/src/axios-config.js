import axios from 'axios';

// Глобальная конфигурация Axios
axios.defaults.baseURL = 'http://localhost:8000';
axios.defaults.headers.common['Content-Type'] = 'application/json; charset=utf-8';
axios.defaults.headers.common['Accept'] = 'application/json; charset=utf-8';

export default axios; 