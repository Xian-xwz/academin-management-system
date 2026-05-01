import { defineStore } from 'pinia';
import { getToken, setToken, removeToken, getUserInfo, setUserInfoData, removeUserInfo } from '@/utils/auth';

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken() || '',
    userInfo: getUserInfo(),
  }),
  actions: {
    setUserInfo(info: any) {
      this.userInfo = info;
      setUserInfoData(info);
    },
    loginSubmit(token: string) {
      this.token = token;
      setToken(token);
    },
    logout() {
      this.token = '';
      this.userInfo = null;
      removeToken();
      removeUserInfo();
    },
    restoreFromStorage() {
      this.token = getToken() || '';
      this.userInfo = getUserInfo();
    }
  }
});
