import request from '@/api';

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

export const login = async (data: any) => {
  const res = await request.post('/auth/login', {
    username: data.username,
    password: data.password
  });
  return unwrapResponse(res);
};

export const register = async (data: any) => {
  const res = await request.post('/auth/register', {
    student_id: data.studentId || data.student_id || data.username,
    password: data.password,
    real_name: data.realName || data.real_name || data.username,
    email: data.email,
    major_code: data.majorCode || data.major_code,
    grade: data.grade
  });
  return unwrapResponse(res);
};

export const uploadAvatar = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await request.post('/auth/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return unwrapResponse(res);
};

export const changePassword = async (data: { oldPassword: string; newPassword: string }) => {
  const res = await request.post('/auth/change-password', {
    old_password: data.oldPassword,
    new_password: data.newPassword
  });
  return unwrapResponse(res);
};
