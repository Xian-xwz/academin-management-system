import request from '@/api';

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

export const getSchedule = async (params?: any) => {
  const res = await request.get('/schedule', { params });
  return unwrapResponse(res);
};

export const updateCourseNote = async (id: number | string, note: string) => {
  const res = await request.patch(`/schedule/${id}/note`, { note });
  return unwrapResponse(res);
};
