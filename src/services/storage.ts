import AsyncStorage from '@react-native-async-storage/async-storage';

export class StorageService {
  // Authentication tokens
  static async setToken(token: string): Promise<void> {
    await AsyncStorage.setItem('auth_token', token);
  }

  static async getToken(): Promise<string | null> {
    return await AsyncStorage.getItem('auth_token');
  }

  static async removeToken(): Promise<void> {
    await AsyncStorage.removeItem('auth_token');
  }

  // User data
  static async setUserData(userData: any): Promise<void> {
    await AsyncStorage.setItem('user_data', JSON.stringify(userData));
  }

  static async getUserData(): Promise<any | null> {
    const userData = await AsyncStorage.getItem('user_data');
    return userData ? JSON.parse(userData) : null;
  }

  static async removeUserData(): Promise<void> {
    await AsyncStorage.removeItem('user_data');
  }

  // Generic storage methods
  static async setItem(key: string, value: string): Promise<void> {
    await AsyncStorage.setItem(key, value);
  }

  static async getItem(key: string): Promise<string | null> {
    return await AsyncStorage.getItem(key);
  }

  static async removeItem(key: string): Promise<void> {
    await AsyncStorage.removeItem(key);
  }

  static async clear(): Promise<void> {
    await AsyncStorage.clear();
  }
}