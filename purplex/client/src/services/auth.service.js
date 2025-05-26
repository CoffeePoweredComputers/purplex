import axios from 'axios';
import { firebaseAuth } from '../firebaseConfig';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword,
  signOut,
  getIdToken
} from 'firebase/auth';

const API_URL = '/api/auth/status/';

class AuthService {
  async validateToken() {
    try {
      // Get current Firebase user
      const user = firebaseAuth.currentUser;
      if (!user) {
        return { authenticated: false };
      }
      
      // Get the ID token
      const token = await getIdToken(user);
      
      // Send the token to our backend for validation
      const response = await axios.post(API_URL, {}, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      return response.data;
    } catch (error) {
      console.error('Token validation error:', error);
      return { authenticated: false, error: error.message };
    }
  }

  async logout() {
    try {
      await signOut(firebaseAuth);
      localStorage.removeItem('user');
      return true;
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  }

  getCurrentUser() {
    return firebaseAuth.currentUser;
  }
}

export default new AuthService();

