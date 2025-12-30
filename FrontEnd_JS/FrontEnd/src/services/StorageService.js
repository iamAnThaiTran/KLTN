const StorageService = {
  // Chat Management
  saveChat: (chat) => {
    const chats = StorageService.getAllChats();
    chats.unshift(chat);
    localStorage.setItem('chatHistories', JSON.stringify(chats));
  },
  
  getAllChats: () => {
    const data = localStorage.getItem('chatHistories');
    return data ? JSON.parse(data) : [];
  },
  
  deleteChat: (id) => {
    const chats = StorageService.getAllChats().filter(chat => chat.id !== id);
    localStorage.setItem('chatHistories', JSON.stringify(chats));
  },
  
  clearAll: () => {
    localStorage.removeItem('chatHistories');
  },

  // Auth Management
  setToken: (token) => {
    localStorage.setItem('authToken', token);
  },

  getToken: () => {
    return localStorage.getItem('authToken');
  },

  setUser: (user) => {
    localStorage.setItem('user', JSON.stringify(user));
  },

  getUser: () => {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  },

  removeToken: () => {
    localStorage.removeItem('authToken');
  },

  removeUser: () => {
    localStorage.removeItem('user');
  },

  clearAuth: () => {
    StorageService.removeToken();
    StorageService.removeUser();
  }
};

export { StorageService };
export default StorageService;