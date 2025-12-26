const StorageService = {
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
  }
};


export default StorageService;