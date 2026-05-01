const TokenKey = 'Student-System-Token';
const UserKey = 'Student-System-User';

export function getToken() {
  return localStorage.getItem(TokenKey);
}

export function setToken(token: string) {
  return localStorage.setItem(TokenKey, token);
}

export function removeToken() {
  return localStorage.removeItem(TokenKey);
}

export function getUserInfo() {
  const info = localStorage.getItem(UserKey);
  try {
    return info ? JSON.parse(info) : null;
  } catch (e) {
    return null;
  }
}

export function setUserInfoData(info: any) {
  return localStorage.setItem(UserKey, JSON.stringify(info));
}

export function removeUserInfo() {
  return localStorage.removeItem(UserKey);
}
