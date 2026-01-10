import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.REACT_APP_BACKEND_URL ||
  "http://localhost:8001";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export default {
  // Projects
  async createProject(data) {
    const response = await api.post("/api/projects", data);
    return response.data;
  },

  async getProject(projectId) {
    const response = await api.get(`/api/projects/${projectId}`);
    return response.data;
  },

  async getAllProjects() {
    const response = await api.get("/api/projects");
    return response.data;
  },

  async deleteProject(projectId) {
    const response = await api.delete(`/api/projects/${projectId}`);
    return response.data;
  },

  // Files
  async saveFile(data) {
    const response = await api.post("/api/files", data);
    return response.data;
  },

  async getFiles(projectId) {
    const response = await api.get(`/api/files/${projectId}`);
    return response.data;
  },

  async deleteFile(projectId, path) {
    const response = await api.delete("/api/files", {
      data: { project_id: projectId, path },
    });
    return response.data;
  },

  // AI Chat
  async chat(message, projectId, context = []) {
    const response = await api.post("/api/chat", {
      message,
      project_id: projectId,
      context,
    });
    return response.data;
  },

  // Component Generation
  async generateComponent(description, framework = "react") {
    const response = await api.post("/api/generate/component", {
      description,
      framework,
    });
    return response.data;
  },

  // Design System Generation
  async generateDesignSystem(description, style = "modern") {
    const response = await api.post("/api/generate/design-system", {
      description,
      style,
    });
    return response.data;
  },

  // Trading APIs
  async tradingAuthToken(data) {
    const response = await api.post("/api/trading/auth/token", data);
    return response.data;
  },

  async tradingAuthPin(data) {
    const response = await api.post("/api/trading/auth/pin", data);
    return response.data;
  },

  async tradingAuthOAuth() {
    const response = await api.post("/api/trading/auth/oauth");
    return response.data;
  },

  async tradingAuthConsume(data) {
    const response = await api.post("/api/trading/auth/consume", data);
    return response.data;
  },

  async getTradingProfile(data) {
    const response = await api.post("/api/trading/profile", data);
    return response.data;
  },

  async placeOrder(data) {
    const response = await api.post("/api/trading/orders/place", data);
    return response.data;
  },

  async getOrders(accessToken) {
    const response = await api.post("/api/trading/orders", {
      token_id: accessToken,
    });
    return response.data;
  },

  async cancelOrder(orderId, accessToken) {
    const response = await api.post(`/api/trading/orders/${orderId}/cancel`, {
      token_id: accessToken,
    });
    return response.data;
  },

  async modifyOrder(orderId, data) {
    const response = await api.post(
      `/api/trading/orders/${orderId}/modify`,
      data
    );
    return response.data;
  },

  async getPositions(accessToken) {
    const response = await api.post("/api/trading/positions", {
      token_id: accessToken,
    });
    return response.data;
  },

  async getHoldings(accessToken) {
    const response = await api.post("/api/trading/holdings", {
      token_id: accessToken,
    });
    return response.data;
  },

  async getFunds(accessToken) {
    const response = await api.post("/api/trading/funds", {
      token_id: accessToken,
    });
    return response.data;
  },

  async getMarketQuote(data) {
    const response = await api.post("/api/trading/market/quote", data);
    return response.data;
  },

  async getOptionChain(data) {
    const response = await api.post("/api/trading/market/option-chain", data);
    return response.data;
  },

  async getHistoricalData(data) {
    const response = await api.post("/api/trading/market/historical", data);
    return response.data;
  },

  async getSecurities(accessToken) {
    const response = await api.post("/api/trading/securities", {
      token_id: accessToken,
    });
    return response.data;
  },

  async getExpiryList(data) {
    const response = await api.post("/api/trading/expiry-list", data);
    return response.data;
  },
};
