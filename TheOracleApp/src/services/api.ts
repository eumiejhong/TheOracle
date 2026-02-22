// API configuration and endpoints
const API_BASE_URL = 'http://localhost:8000'; // Django backend URL

export class ApiService {
  private static token: string | null = null;

  static setToken(token: string) {
    this.token = token;
  }

  static clearToken() {
    this.token = null;
  }

  private static async request(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<any> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Authentication
  static async login(email: string, password: string) {
    return this.request('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  static async register(email: string, password: string) {
    return this.request('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  // User Profile
  static async getUserProfile(userId: string) {
    return this.request(`/api/profile/${userId}/`);
  }

  static async createUserProfile(profile: any) {
    return this.request('/api/profile/', {
      method: 'POST',
      body: JSON.stringify(profile),
    });
  }

  static async updateUserProfile(userId: string, profile: any) {
    return this.request(`/api/profile/${userId}/`, {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  }

  // Wardrobe
  static async getWardrobeItems(userId: string) {
    return this.request(`/api/wardrobe/${userId}/`);
  }

  static async addWardrobeItem(item: FormData) {
    return fetch(`${API_BASE_URL}/api/wardrobe/`, {
      method: 'POST',
      headers: {
        Authorization: this.token ? `Bearer ${this.token}` : '',
      },
      body: item,
    }).then(res => res.json());
  }

  static async deleteWardrobeItem(itemId: string) {
    return this.request(`/api/wardrobe/${itemId}/`, {
      method: 'DELETE',
    });
  }

  static async toggleFavorite(itemId: string) {
    return this.request(`/api/wardrobe/${itemId}/toggle-favorite/`, {
      method: 'POST',
    });
  }

  // Daily Styling
  static async submitDailyInput(input: any) {
    return this.request('/api/daily-input/', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  static async getStylingSuggestions(userId: string) {
    return this.request(`/api/suggestions/${userId}/`);
  }

  static async submitFeedback(suggestionId: string, feedback: any) {
    return this.request(`/api/suggestions/${suggestionId}/feedback/`, {
      method: 'POST',
      body: JSON.stringify(feedback),
    });
  }
}